import json
import uuid
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from django.conf import settings
from django.db import transaction

from apps.automotive.models import Anomaly, Complaint, Recall
from apps.ingestion.pipeline import job_lock
from apps.risk.models import Assessment

from .datasets import GOLD_SQL, SCHEMAS
from .models import Publication


def sql_path(path):
    return "'" + Path(path).as_posix().replace("'", "''") + "'"


def source_rows(mode):
    # Latest calculation for each dependency/day. Re-running a calculation cannot inflate Gold counts.
    dependencies = {}
    for row in (
        Assessment.objects.filter(run__mode=mode)
        .select_related(
            "run", "source__site__supplier", "requirement__factory", "requirement__part"
        )
        .order_by("run_id")
    ):
        day = row.run.as_of.date().isoformat()
        key = (day, row.source.site.supplier_id, row.requirement_id)
        dependencies[key] = {
            "date": day,
            "supplier_id": row.source.site.supplier_id,
            "supplier": row.source.site.supplier.name,
            "factory_id": row.requirement.factory_id,
            "factory": row.requirement.factory.name,
            "part_id": row.requirement.part_id,
            "part": row.requirement.part.number,
            "event_id": row.event_id,
            "score": row.score,
            "coverage": row.days_of_supply,
            "distance_km": row.distance_km,
            "mode": mode,
            "model_version": row.run.model_version,
        }
    complaints = [
        {
            "source_id": row.source_id,
            "vehicle_id": row.vehicle_id,
            "make": row.vehicle.make,
            "model": row.vehicle.model,
            "year": row.vehicle.year,
            "filed_on": row.filed_on.isoformat(),
            "component": row.component,
            "crash": row.crash,
            "fire": row.fire,
            "injuries": row.injuries,
            "mode": mode,
        }
        for row in Complaint.objects.filter(mode=mode).select_related("vehicle")
    ]
    recalls = [
        {
            "campaign": r.campaign,
            "reported_on": r.reported_on.isoformat(),
            "component": r.component,
            "summary": r.summary,
            "mode": mode,
        }
        for r in Recall.objects.filter(mode=mode)
    ]
    anomalies = [
        {
            "vehicle_id": a.vehicle_id,
            "component": a.component,
            "month": a.month.isoformat(),
            "observed": a.observed,
            "expected": a.expected,
            "threshold": a.threshold,
            "increase_pct": a.increase_pct,
            "severity": a.severity,
            "mode": mode,
            "model_version": a.model_version,
        }
        for a in Anomaly.objects.filter(mode=mode)
    ]
    return {
        "dependencies": list(dependencies.values()),
        "complaints": complaints,
        "recalls": recalls,
        "anomalies": anomalies,
    }


def publish(mode):
    with job_lock(f"analytics:{mode}"):
        version = uuid.uuid4().hex
        root = settings.DATA_ROOT / "publications" / version
        root.mkdir(parents=True)
        # Take one PostgreSQL snapshot across the source tables.
        with transaction.atomic():
            from django.db import connection

            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            rows = source_rows(mode)
        manifest = {"version": version, "mode": mode, "schema_version": 1, "datasets": {}}
        with duckdb.connect(str(root / "catalog.duckdb")) as warehouse:
            for name, records in rows.items():
                path = root / f"silver_{name}.parquet"
                pq.write_table(pa.Table.from_pylist(records, schema=SCHEMAS[name]), path)
                warehouse.execute(
                    f"CREATE VIEW {name} AS SELECT * FROM read_parquet({sql_path(path)})"
                )
            for name, sql in GOLD_SQL.items():
                table = warehouse.execute(sql).to_arrow_table()
                path = root / f"{name}.parquet"
                pq.write_table(table, path)
                # Materialize the local read-only catalog; Parquet remains the durable interchange.
                warehouse.execute(
                    f"CREATE TABLE {name} AS SELECT * FROM read_parquet({sql_path(path)})"
                )
                manifest["datasets"][name] = {
                    "path": str(path.relative_to(settings.DATA_ROOT)),
                    "rows": table.num_rows,
                }
        (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        # This database insert is the publication commit point. Failed builds remain invisible.
        return Publication.objects.create(mode=mode, version=version, manifest=manifest)
