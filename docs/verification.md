# Verification record

Verified on Windows with Python 3.13.2 and an isolated PostgreSQL 17 cluster on loopback port 55432. PostgreSQL was not replaced with SQLite.

## Completed checks

- Full automated suite: **54 passed, 1 skipped**. The skipped test requires opt-in Snowflake credentials.
- Guided investigation tests verify public read-only access, demo/live isolation and pending qualification. Hosted-demo recovery deletes local publications, restarts bootstrap without reseeding and verifies a readable replacement analytical dataset.
- Django system checks passed; migration-drift check reported no changes.
- Ruff lint and formatting checks passed.
- OpenAPI schema generation and validation completed without warnings.
- Tailwind/asset build and production static-file collection passed.
- Expanded browser checks passed on all ten navigation routes, supplier-to-factory investigation, HTMX supplier search, automotive component filtering, event-marker investigation, maps/charts and a 390-pixel mobile layout. Screenshots were refreshed after the latest changes.
- Browser checks also complete the dashboard-to-guided-scenario journey, inspect qualification guidance and verify the investigation page at mobile width.
- Demo seeding and analytical publication succeeded. Repeat seeding preserved row counts. Gold datasets were tested for consistent grains and failed-publication recovery.
- Live USGS ingestion loaded 935 events with no rejections in the first run.
- Live NHTSA ingestion loaded 1,303 complaints. Recall ingestion succeeded after adding a Ford recall-model alias; the successful run processed 30 campaign records (17 new/updated, 13 unchanged) with no rejections.
- Open-Meteo current-weather HTTP response and units were verified for Hsinchu. Full weather adapter integration tests use a controlled HTTP response; live-company weather ingestion requires operator-configured live sites.
- Docker Desktop started successfully (Engine 29.6.2), and Compose configuration validates. Two build attempts failed downloading base-image metadata from Docker's registry/CDN with EOF errors. No container acceptance is claimed.

## External verification still required

- Retry Docker image downloads, then complete the build, Compose startup and container smoke checks.
- Run optional Snowflake setup/upload/parity tests in an actual account. The integration code exists but has not been warehouse-verified.
- Configure hosting, DNS and TLS before claiming a public deployment.
- The Render blueprint and Neon configuration are prepared, but provider accounts are not connected. Verify startup memory, restart recovery and public HTTPS in the actual free-tier environment before accepting hosting.

## Reproduce local checks

```powershell
npm run build
./.venv/Scripts/python manage.py collectstatic --noinput
./.venv/Scripts/python -m pytest -q
./.venv/Scripts/python manage.py check
./.venv/Scripts/python manage.py makemigrations --check --dry-run
# Start or restart the local Django server before browser checks:
./.venv/Scripts/python scripts/browser_check.py
```
