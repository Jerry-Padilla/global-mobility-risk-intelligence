"""Stable schemas shared by Parquet, DuckDB and the optional warehouse."""

import pyarrow as pa

SCHEMAS = {
    "dependencies": pa.schema(
        [
            ("date", pa.string()),
            ("supplier_id", pa.int64()),
            ("supplier", pa.string()),
            ("factory_id", pa.int64()),
            ("factory", pa.string()),
            ("part_id", pa.int64()),
            ("part", pa.string()),
            ("event_id", pa.int64()),
            ("score", pa.float64()),
            ("coverage", pa.float64()),
            ("distance_km", pa.float64()),
            ("mode", pa.string()),
            ("model_version", pa.string()),
        ]
    ),
    "complaints": pa.schema(
        [
            ("source_id", pa.string()),
            ("vehicle_id", pa.int64()),
            ("make", pa.string()),
            ("model", pa.string()),
            ("year", pa.int64()),
            ("filed_on", pa.string()),
            ("component", pa.string()),
            ("crash", pa.bool_()),
            ("fire", pa.bool_()),
            ("injuries", pa.int64()),
            ("mode", pa.string()),
        ]
    ),
    "recalls": pa.schema(
        [
            ("campaign", pa.string()),
            ("reported_on", pa.string()),
            ("component", pa.string()),
            ("summary", pa.string()),
            ("mode", pa.string()),
        ]
    ),
    "anomalies": pa.schema(
        [
            ("vehicle_id", pa.int64()),
            ("component", pa.string()),
            ("month", pa.string()),
            ("observed", pa.int64()),
            ("expected", pa.float64()),
            ("threshold", pa.float64()),
            ("increase_pct", pa.float64()),
            ("severity", pa.string()),
            ("mode", pa.string()),
            ("model_version", pa.string()),
        ]
    ),
}

GOLD_SQL = {
    "supplier_risk_summary": "SELECT mode, date, supplier_id, supplier, MAX(score) AS score, COUNT(DISTINCT CASE WHEN score>=50 THEN factory_id END) AS affected_factories, model_version FROM dependencies GROUP BY ALL",
    "factory_risk_summary": "SELECT mode, date, factory_id, factory, MAX(score) AS score, COUNT(DISTINCT CASE WHEN score>=50 THEN part_id END) AS exposed_parts, model_version FROM dependencies GROUP BY ALL",
    "inventory_exposure": "SELECT mode, date, factory_id, factory, part_id, part, MAX(score) AS score, MAX(coverage) AS coverage FROM dependencies GROUP BY ALL",
    "event_supplier_exposure": "SELECT DISTINCT mode, date, event_id, supplier_id, supplier, MIN(distance_km) AS distance_km, MAX(score) AS score FROM dependencies WHERE event_id IS NOT NULL GROUP BY ALL",
    "automotive_complaint_trends": "SELECT mode, vehicle_id, make, model, year, component, substr(filed_on,1,7)||'-01' AS month, COUNT(*) AS count, SUM(CAST(crash AS INTEGER)) AS crashes, SUM(CAST(fire AS INTEGER)) AS fires, SUM(injuries) AS injuries FROM complaints GROUP BY ALL",
    "vehicle_failure_summary": "SELECT mode, vehicle_id, make, model, year, component, COUNT(*) AS count FROM complaints GROUP BY ALL",
    "recall_summary": "SELECT * FROM recalls",
    "automotive_anomalies": "SELECT * FROM anomalies",
}
DATASETS = tuple(GOLD_SQL)
