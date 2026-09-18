# Optional Snowflake integration

The default application never imports the Snowflake connector or contacts a warehouse. All investigations, scenarios, APIs and analytics work with PostgreSQL + DuckDB after a trial expires.

## Two deliberately separate paths

1. **Application publication:** `publish_snowflake` uploads the exact tested Gold Parquet datasets to staging, validates row counts, inserts a versioned batch and switches the mode's publication pointer in one transaction. The adapter reads only that version. Old versions remain available for operator-managed retention. Use a single loader scheduler; PostgreSQL locks coordinate loaders sharing this application's database.
2. **Native ELT demonstration:** raw envelopes load into `RAW.SOURCE_RECORDS` as VARIANT. `SILVER.EARTHQUAKES` uses JSON flattening, typing, filtering and latest-record deduplication. A suspended Dynamic Table aggregates earthquakes; a separate stream/task captures ingestion audit entries. Neither feature duplicates the application's risk-score engine or runs automatically.

## Setup

Install the optional connector in the same environment:

```sh
python -m pip install '.[snowflake]'
```

Execute SQL files `00` through `03` with a provisioning role. Set up RBAC (`07`) and the resource monitor (`08`) with the necessary account privileges. Assign `MOBILITY_LOADER` to a loader user and `MOBILITY_READER` to the application's warehouse user. The reader cannot load or alter tables. The example scripts `04`–`06` are optional and create suspended processing.

Configure `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_DATABASE=MOBILITY`, `SNOWFLAKE_SCHEMA=GOLD`, `SNOWFLAKE_WAREHOUSE=MOBILITY_WH`, and optionally `SNOWFLAKE_ROLE`. Credentials stay in environment variables. Deployments with key-pair/OAuth authentication should extend the connector configuration rather than commit secrets.

```sh
python manage.py publish_analytics --mode demo
python manage.py publish_snowflake --mode demo --include-raw
# Only after successful upload:
# ANALYTICS_BACKEND=snowflake
```

Return to `ANALYTICS_BACKEND=duckdb` at any time. There is no silent warehouse fallback: an unavailable configured warehouse produces a visible analytical error while operational investigations continue.

## Verification status

The DuckDB implementation and local publication contract are tested. Snowflake SQL and connector code have **not** been executed against an account in this workspace. No credentials were provided. Setting `RUN_SNOWFLAKE_TESTS=1` explicitly enables `tests/test_snowflake_contract.py`: it seeds a test database, publishes to the configured Snowflake account, and compares local/remote results. Use an isolated warehouse test account and loader role; this test writes the demo publication and can consume credits.

Before using a warehouse deployment, run SQL under actual roles, verify upload/row counts and compare each Gold dataset. Confirm that tasks and Dynamic Tables remain suspended unless intentionally activated.

## Compute controls and references

The warehouse starts suspended, uses X-SMALL, auto-resumes on an explicit query, and auto-suspends after 60 seconds. The monitor is a credit guardrail, not a guarantee of zero cost; storage and services outside warehouse monitoring may still incur charges.

- [Dynamic Table creation and initialization](https://docs.snowflake.com/en/sql-reference/sql/create-dynamic-table)
- [Resource monitor coverage and limits](https://docs.snowflake.com/en/user-guide/resource-monitors)
- [Suspending and managing Dynamic Tables](https://docs.snowflake.com/en/user-guide/dynamic-tables/manage)

Snowpark is not included because this implementation has no transformation that benefits from an additional execution framework.
