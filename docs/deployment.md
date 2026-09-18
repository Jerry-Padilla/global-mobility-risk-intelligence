# Deployment and operations

## Local Docker

```sh
cp .env.example .env
docker compose up --build -d
docker compose exec web python manage.py generate_company_data
docker compose exec web python manage.py publish_analytics --mode demo
```

Open `http://localhost:8000`. Compose migrates before starting Gunicorn, waits for PostgreSQL health, binds the web port to loopback, and persists both database and analytical files in named volumes. Seeding is explicit so restarts do not rewrite company data. Creating a staff account is optional: `docker compose exec web python manage.py createsuperuser`.

## Native Windows

Install Python 3.13+, Node 22+ and PostgreSQL 17. Create a database and database user matching `.env`; the test user also needs CREATEDB on the development server. Do not use the production role for tests.

```powershell
Copy-Item .env.example .env
# Set PostgreSQL host/port/password in .env for your local server.
./scripts/dev.ps1 setup
./scripts/dev.ps1 seed
./scripts/dev.ps1 run
```

The implementation session uses a workspace-local portable PostgreSQL instance on port 55432 because Docker's engine was unavailable. Its binaries, password file, cluster, logs and `.env` are ignored by Git. This is a local verification convenience, not a second application database architecture. Restart it with:

```powershell
./.runtime/pgsql/bin/pg_ctl.exe -D .runtime/pgdata -l .runtime/postgres.log -o '-p 55432 -h 127.0.0.1' start
```

Stop it with `pg_ctl.exe -D .runtime/pgdata stop -m fast` after stopping Django. Reproduction on another machine should use Compose or a normal PostgreSQL installation; the ignored runtime is not shipped.

## Refresh commands

```sh
python manage.py ingest_usgs
python manage.py ingest_usgs --reconcile
python manage.py ingest_nhtsa --dataset all
python manage.py ingest_weather
python manage.py calculate_risk --mode live
python manage.py publish_analytics --mode live
```

Weather requires configured live sites. Add them through authenticated Django administration. Recommended starting schedules: USGS hourly, weather every three hours, NHTSA daily, catalog reconciliation weekly. Chain calculation/publication after successful ingestion. Cron or a host scheduler can run these commands; never trigger them from a public HTTP endpoint. Source errors produce nonzero exit status and structured logs. `Data health` displays timestamps, counts, errors and rejected records.

## Production

Use `DJANGO_DEBUG=false`, a unique secret from the host's secret store, explicit `ALLOWED_HOSTS` and HTTPS `CSRF_TRUSTED_ORIGINS`. Terminate TLS at the host/proxy. When using a trusted proxy, configure forwarded-protocol handling in deployment-specific settings and ensure the proxy strips spoofed client headers. Do not disable HTTPS protections merely to pass a deployment check.

Run `python manage.py check --deploy`, apply migrations as a release step, collect static files, then start Gunicorn. Use a dedicated least-privilege application database user. Keep PostgreSQL off the public internet. Staff credentials are never bundled. Public viewers cannot change records or launch jobs.

Provide persistent PostgreSQL and `DATA_ROOT` storage. Ephemeral-only free hosts cannot preserve ingestion history. Docker is the intended reproducible local target; container acceptance remains pending successful image downloads and execution. No hosted deployment or free-tier availability is claimed. Provider/account selection and DNS/TLS configuration remain external deployment steps.

## Recovery and retention

- Back up PostgreSQL and raw/Parquet publication files together. Restore to an isolated instance and run health and dataset-count checks.
- A failed ingestion keeps its last successful watermark; rerun after correcting the source or parser.
- A failed analytical build leaves the last publication active. Unreferenced output directories can be removed after verifying no `Publication.version` references them.
- Interrupted processes can leave `IngestionRun.status=running`; inspect process/job logs and the advisory-lock state before marking the run interrupted. Locks release when the database session closes.
- Monitor `/health/`, source freshness, run status/duration, rejection counts, filesystem capacity and database growth. `/health/` checks PostgreSQL availability and does not expose connection details.

## Cost boundary

The deterministic demo has no recurring service dependency. Public API use and public-source licensing remain provider-specific. Snowflake commands are explicit opt-in and can consume credits. No cloud resources, public deployment or paid account were created by this implementation.
