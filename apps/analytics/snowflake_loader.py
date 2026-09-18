"""Optional, explicitly invoked warehouse publication; no connection at import time."""

import json
import os

from django.conf import settings

from .datasets import DATASETS
from .models import Publication


def connect():
    try:
        import snowflake.connector
    except ImportError as exc:
        from django.core.exceptions import ImproperlyConfigured

        raise ImproperlyConfigured("Install the snowflake optional dependency") from exc

    config = {
        key: os.environ[f"SNOWFLAKE_{key.upper()}"]
        for key in ("account", "user", "password", "database", "schema", "warehouse")
    }
    if os.getenv("SNOWFLAKE_ROLE"):
        config["role"] = os.environ["SNOWFLAKE_ROLE"]
    return snowflake.connector.connect(**config)


def publish_snowflake(mode):
    publication = Publication.objects.filter(mode=mode).latest("created_at")
    with connect() as connection:
        with connection.cursor() as cursor:
            # Stage and validate every table before switching the public version pointer.
            for dataset in DATASETS:
                path = (
                    (settings.DATA_ROOT / publication.manifest["datasets"][dataset]["path"])
                    .resolve()
                    .as_posix()
                    .replace("'", "''")
                )
                stage = f"@RAW.INGEST_STAGE/{publication.version}/{dataset}"
                cursor.execute(f"PUT 'file://{path}' {stage} AUTO_COMPRESS=FALSE OVERWRITE=TRUE")
                cursor.execute(f'CREATE TEMP TABLE "load_{dataset}" LIKE "{dataset}"')
                cursor.execute(f'ALTER TABLE "load_{dataset}" DROP COLUMN "publication_version"')
                cursor.execute(
                    f'COPY INTO "load_{dataset}" FROM {stage} FILE_FORMAT=(FORMAT_NAME=RAW.PARQUET_FORMAT) MATCH_BY_COLUMN_NAME=CASE_SENSITIVE'
                )
                cursor.execute(f'SELECT COUNT(*) FROM "load_{dataset}"')
                if cursor.fetchone()[0] != publication.manifest["datasets"][dataset]["rows"]:
                    raise ValueError(f"Warehouse row-count mismatch for {dataset}")
            cursor.execute("BEGIN")
            try:
                for dataset in DATASETS:
                    cursor.execute(
                        f'DELETE FROM "{dataset}" WHERE "mode"=%s AND "publication_version"=%s',
                        (mode, publication.version),
                    )
                    cursor.execute(
                        f'INSERT INTO "{dataset}" SELECT *, %s FROM "load_{dataset}"',
                        (publication.version,),
                    )
                cursor.execute('DELETE FROM "publications" WHERE "mode"=%s', (mode,))
                cursor.execute(
                    'INSERT INTO "publications" VALUES (%s,%s)', (mode, publication.version)
                )
                cursor.execute("COMMIT")
            except Exception:
                cursor.execute("ROLLBACK")
                raise
    return publication.version


def upload_raw(mode):
    from apps.ingestion.models import RawRecord

    count = 0
    with connect() as connection:
        with connection.cursor() as cursor:
            for raw in RawRecord.objects.filter(run__mode=mode).select_related("run"):
                payload = (settings.DATA_ROOT / raw.path).read_text(encoding="utf-8")
                cursor.execute(
                    """INSERT INTO RAW.SOURCE_RECORDS
                    SELECT %s,%s,%s,%s,%s,PARSE_JSON(%s),PARSE_JSON(%s)
                    WHERE NOT EXISTS (SELECT 1 FROM RAW.SOURCE_RECORDS WHERE MODE=%s AND SOURCE=%s AND PAYLOAD_HASH=%s)""",
                    (
                        mode,
                        raw.run.source,
                        raw.source_id,
                        raw.retrieved_at,
                        raw.payload_hash,
                        json.dumps(raw.request),
                        payload,
                        mode,
                        raw.run.source,
                        raw.payload_hash,
                    ),
                )
                count += cursor.rowcount
    return count
