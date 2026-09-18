from dataclasses import dataclass
from typing import Protocol

import duckdb
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .datasets import DATASETS
from .models import Publication


@dataclass(frozen=True)
class AnalyticalResult:
    dataset: str
    rows: list[dict]
    version: str | None


class AnalyticsBackend(Protocol):
    def query(self, dataset: str, mode: str, limit: int = 200) -> AnalyticalResult: ...


def validate(dataset, mode, limit):
    if dataset not in DATASETS or mode not in ("demo", "live") or not 1 <= limit <= 10000:
        raise ValueError("Unsupported analytical query")


class DuckDBBackend:
    def query(self, dataset, mode, limit=200):
        validate(dataset, mode, limit)
        publication = Publication.objects.filter(mode=mode).order_by("-created_at", "-pk").first()
        if not publication:
            return AnalyticalResult(dataset, [], None)
        path = settings.DATA_ROOT / "publications" / publication.version / "catalog.duckdb"
        with duckdb.connect(str(path), read_only=True) as warehouse:
            cursor = warehouse.execute(f"SELECT * FROM {dataset} ORDER BY ALL LIMIT ?", [limit])
            fields = [item[0] for item in cursor.description]
            rows = [dict(zip(fields, row, strict=True)) for row in cursor.fetchall()]
        return AnalyticalResult(dataset, rows, publication.version)


class SnowflakeBackend:
    def query(self, dataset, mode, limit=200):
        validate(dataset, mode, limit)
        from .snowflake_loader import connect

        with connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT "version" FROM "publications" WHERE "mode"=%s', (mode,))
                result = cursor.fetchone()
                if not result:
                    return AnalyticalResult(dataset, [], None)
                cursor.execute(
                    f'SELECT * EXCLUDE ("publication_version") FROM "{dataset}" WHERE "mode"=%s AND "publication_version"=%s ORDER BY ALL LIMIT %s',
                    (mode, result[0], limit),
                )
                fields = [column[0].lower() for column in cursor.description]
                rows = [dict(zip(fields, row, strict=True)) for row in cursor.fetchall()]
        return AnalyticalResult(dataset, rows, result[0] if result else None)


def get_backend():
    if settings.ANALYTICS_BACKEND == "duckdb":
        return DuckDBBackend()
    if settings.ANALYTICS_BACKEND == "snowflake":
        return SnowflakeBackend()
    raise ImproperlyConfigured("ANALYTICS_BACKEND must be duckdb or snowflake")
