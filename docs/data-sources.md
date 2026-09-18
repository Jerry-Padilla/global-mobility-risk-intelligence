# Public sources and attribution

## USGS

[Earthquake catalog API](https://earthquake.usgs.gov/fdsnws/event/1/) provides GeoJSON event identity, location, magnitude, depth, event time and update time. The command queries magnitude 4+ events within the last 30 days. Subsequent runs use an overlapping `updatedafter` watermark; `--reconcile` reloads the rolling window. Intervals split when they reach the API's 20,000-result cap. Revised source IDs update existing records.

Known boundary: records revised outside the rolling 30-day window and deleted USGS events are not automatically reconciled. Active exposure still expires after seven days. Raw payloads retain evidence for source-parser changes.

## Open-Meteo

[Forecast/current API documentation](https://open-meteo.com/en/docs) and [free-service terms](https://open-meteo.com/en/pricing). The free endpoint requires no API key for noncommercial use; commercial use has different terms. No availability guarantee is assumed.

The implementation batches at most 20 configured live locations per request, requests UTC and explicit units, and preserves current temperature, precipitation and wind. Valid time and retrieval time are distinct. The current endpoint does not expose model issue time; `issued_at` records retrieval time and is not represented as a source forecast issue timestamp. Historical weather and forecast horizons are extensions, not silently simulated features.

## NHTSA

[Official datasets and APIs](https://www.nhtsa.gov/nhtsa-datasets-and-apis) and [API policy](https://api.nhtsa.gov/).

Endpoints:

- `https://api.nhtsa.gov/complaints/complaintsByVehicle`
- `https://api.nhtsa.gov/recalls/recallsByVehicle`

Both are queried with make, model and modelYear from `data/watchlist.json`. The initial watchlist is three 2022 EV models. Entire per-vehicle results are reconciled by stable IDs and hashes; a date cursor is not assumed. Adding a watchlist vehicle does not require a new adapter. The application does not scrape arbitrary vehicle narratives or join public complaints to synthetic suppliers.

The watchlist can specify dataset-specific query aliases while retaining a canonical vehicle identity. Live verification found Ford recalls use `MUSTANG MACH E`, while complaints use `MUSTANG MACH-E`. Complaint dates are parsed month/day/year; recall report dates are parsed day/month/year. Parser corrections update normalized records even when raw payload hashes are unchanged.

Complaints are consumer reports. Crash, fire and injury fields describe reported information. Source dates and identifiers are preserved. A campaign applying to several queried vehicles remains one campaign with multiple applicability links.

## Geographic background

The bundled `static/world.geojson` is Natural Earth's 1:110m country dataset from [natural-earth-vector](https://github.com/nvkelso/natural-earth-vector), released to the [public domain](https://www.naturalearthdata.com/about/terms-of-use/). Country boundaries are visualization context, not a statement about territorial claims. The UI loads no paid map service and needs no tile key.

## Operational behavior

HTTP clients use explicit timeouts, bounded exponential backoff for transient/429 failures and request pacing. Unexpected responses fail visibly. Validation exceptions quarantine records; infrastructure failures abort the run. No paid API, credentials or Snowflake connection is required for deterministic local demonstration.
