"""Source-neutral ingestion lifecycle with durable evidence and PostgreSQL locks."""

import hashlib
import json
import logging
import time
from contextlib import contextmanager

import httpx
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from .models import IngestionRun, QualityIssue, RawRecord, SourceState

logger = logging.getLogger(__name__)


def digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


@contextmanager
def job_lock(key):
    lock_id = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], signed=True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [lock_id])
        acquired = cursor.fetchone()[0]
    if not acquired:
        raise RuntimeError(f"Another {key} job is already running")
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [lock_id])


class PublicClient:
    def __init__(self, client=None, minimum_interval=1.0):
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(30, connect=10),
            headers={"User-Agent": "Meridian-Portfolio/0.1 (public data research)"},
            follow_redirects=True,
        )
        self.minimum_interval = minimum_interval
        self.last_request = 0

    def get(self, url, params):
        for attempt in range(4):
            time.sleep(max(0, self.minimum_interval - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                response = self.client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code not in (
                    429,
                    500,
                    502,
                    503,
                    504,
                ):
                    raise
                if attempt == 3:
                    raise
                time.sleep(2**attempt)

    def close(self):
        self.client.close()


def preserve(run, payload, request, source_id):
    checksum = digest(payload)
    folder = settings.DATA_ROOT / "raw" / run.mode / run.source / str(run.id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{checksum}.json"
    if not path.exists():
        with path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, default=str)
    RawRecord.objects.create(
        run=run,
        source_id=str(source_id)[:180],
        request=request,
        payload_hash=checksum,
        path=str(path.relative_to(settings.DATA_ROOT)),
    )
    return checksum


def execute(source, mode, fetch_pages, consume):
    """fetch_pages yields (request metadata, payload, iterable of records)."""
    with job_lock(f"ingest:{mode}:{source}"):
        run = IngestionRun.objects.create(source=source, mode=mode)
        state, _ = SourceState.objects.get_or_create(source=source, mode=mode)
        checkpoint = timezone.now()
        try:
            for request, payload, records in fetch_pages(state.watermark):
                preserve(run, payload, request, request.get("scope", "response"))
                for index, record in enumerate(records):
                    try:
                        with transaction.atomic():
                            changed = consume(record, mode)
                        run.loaded += int(changed)
                        run.skipped += int(not changed)
                    except (
                        ValueError,
                        KeyError,
                        TypeError,
                        ValidationError,
                        IntegrityError,
                    ) as exc:
                        run.rejected += 1
                        QualityIssue.objects.create(
                            run=run,
                            source_id=str(record.get("id", record.get("odiNumber", index)))[:180],
                            reason=str(exc)[:2000],
                        )
            run.status = "partial" if run.rejected else "success"
            if not run.rejected:
                state.watermark = checkpoint
                state.last_success = timezone.now()
                state.save()
        except Exception as exc:
            run.status = "failed"
            run.error = f"{type(exc).__name__}: {exc}"[:4000]
            logger.exception("Ingestion failed source=%s run=%s", source, run.pk)
            raise
        finally:
            run.finished_at = timezone.now()
            run.save()
            logger.info(
                "Ingestion completed",
                extra={
                    "pipeline": {
                        "run": run.pk,
                        "source": source,
                        "status": run.status,
                        "loaded": run.loaded,
                        "skipped": run.skipped,
                        "rejected": run.rejected,
                        "duration_seconds": (run.finished_at - run.started_at).total_seconds(),
                    }
                },
            )
        return run
