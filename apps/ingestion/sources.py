import json
from datetime import datetime, timedelta, timezone

from django.conf import settings

from apps.automotive.models import Complaint, Recall, Vehicle
from apps.environmental.models import Event, WeatherReading
from apps.supply_chain.models import Factory, LogisticsHub, SupplierSite

from . import parsers
from .pipeline import PublicClient, digest, execute


def upsert(model, lookup, values):
    obj = model.objects.filter(**lookup).first()
    if obj and values.get("payload_hash") and obj.payload_hash == values["payload_hash"]:
        # Parser fixes can change normalized values without changing source payloads.
        if all(getattr(obj, key) == value for key, value in values.items()):
            return obj, False
    if obj is None:
        obj = model(**lookup)
    for key, value in values.items():
        setattr(obj, key, value)
    obj.full_clean()
    obj.save()
    return obj, True


def ingest_usgs(mode="live", client=None, reconcile=False):
    client = client or PublicClient()
    endpoint = "https://earthquake.usgs.gov/fdsnws/event/1/query"

    def pages(watermark):
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=30)
        params = {"format": "geojson", "minmagnitude": 4, "orderby": "time-asc", "limit": 20000}
        if watermark and not reconcile:
            params["updatedafter"] = (watermark - timedelta(hours=2)).isoformat()

        def window(left, right):
            query = {**params, "starttime": left.isoformat(), "endtime": right.isoformat()}
            try:
                payload = client.get(endpoint, query)
            except Exception as exc:
                import httpx

                if (
                    not isinstance(exc, httpx.HTTPStatusError)
                    or exc.response.status_code != 400
                    or "20000" not in exc.response.text
                ):
                    raise
                payload = {"features": [None] * 20000}
            if len(payload["features"]) >= 20000:
                if right - left < timedelta(seconds=1):
                    raise ValueError("USGS interval exceeds safe result limit")
                middle = left + (right - left) / 2
                yield from window(left, middle)
                yield from window(middle, right)
            else:
                yield {"url": endpoint, "params": query}, payload, payload["features"]

        yield from window(start, end)

    def consume(record, dataset):
        values = parsers.earthquake(record)
        identifier = values.pop("source_id")
        return upsert(Event, {"mode": dataset, "source": "usgs", "source_id": identifier}, values)[
            1
        ]

    try:
        return execute("usgs", mode, pages, consume)
    finally:
        client.close()


def ingest_weather(mode="live", client=None):
    client = client or PublicClient()
    endpoint = "https://api.open-meteo.com/v1/forecast"

    def pages(watermark):
        locations = []
        for model, prefix in (
            (Factory, "factory"),
            (SupplierSite, "supplier"),
            (LogisticsHub, "hub"),
        ):
            locations.extend(
                (f"{prefix}:{obj.pk}", obj.latitude, obj.longitude)
                for obj in model.objects.filter(mode=mode)
            )
        if not locations:
            raise ValueError(
                "No locations configured for this dataset; add live sites before weather ingestion"
            )
        for offset in range(0, len(locations), 20):
            batch = locations[offset : offset + 20]
            params = {
                "latitude": ",".join(str(row[1]) for row in batch),
                "longitude": ",".join(str(row[2]) for row in batch),
                "current": "temperature_2m,precipitation,wind_speed_10m",
                "timezone": "UTC",
            }
            payload = client.get(endpoint, params)
            responses = payload if isinstance(payload, list) else [payload]
            if len(responses) != len(batch):
                raise ValueError("Weather response location count mismatch")
            records = [
                {
                    "location_key": loc[0],
                    "latitude": loc[1],
                    "longitude": loc[2],
                    "response": response,
                }
                for loc, response in zip(batch, responses, strict=True)
            ]
            yield {"url": endpoint, "params": params}, payload, records

    def consume(record, dataset):
        current = record["response"]["current"]
        valid = datetime.fromisoformat(current["time"]).replace(tzinfo=timezone.utc)
        temperature = parsers.finite(current["temperature_2m"], -100, 70)
        rain = parsers.finite(current["precipitation"], 0, 1000)
        wind = parsers.finite(current["wind_speed_10m"], 0, 500)
        # The current endpoint does not supply model issue time; retrieval time is recorded as issued_at.
        if WeatherReading.objects.filter(
            mode=dataset,
            location_key=record["location_key"],
            valid_at=valid,
            temperature_c=temperature,
            precipitation_mm=rain,
            wind_kmh=wind,
        ).exists():
            return False
        WeatherReading.objects.create(
            mode=dataset,
            location_key=record["location_key"],
            latitude=record["latitude"],
            longitude=record["longitude"],
            valid_at=valid,
            issued_at=datetime.now(timezone.utc),
            temperature_c=temperature,
            precipitation_mm=rain,
            wind_kmh=wind,
        )
        severity = max(
            max(0, min(1, (wind - 60) / 60)),
            max(0, min(1, (rain - 10) / 30)),
            max(0, min(1, (temperature - 38) / 12)),
        )
        if severity > 0:
            upsert(
                Event,
                {
                    "mode": dataset,
                    "source": "open-meteo",
                    "source_id": f"{record['location_key']}:{valid.isoformat()}",
                },
                {
                    "kind": "weather",
                    "title": f"Weather threshold exceeded · {record['location_key']}",
                    "occurred_at": valid,
                    "expires_at": valid + timedelta(hours=24),
                    "latitude": record["latitude"],
                    "longitude": record["longitude"],
                    "severity": severity,
                    "payload_hash": digest(record),
                },
            )
        return True

    try:
        return execute("weather", mode, pages, consume)
    finally:
        client.close()


def ingest_nhtsa(dataset="complaints", mode="live", client=None, watchlist=None):
    client = client or PublicClient(minimum_interval=1.5)
    vehicles = (
        watchlist
        if watchlist is not None
        else json.loads((settings.BASE_DIR / "data/watchlist.json").read_text())["vehicles"]
    )
    endpoint = f"https://api.nhtsa.gov/{'complaints/complaintsByVehicle' if dataset == 'complaints' else 'recalls/recallsByVehicle'}"

    def pages(watermark):
        for spec in vehicles:
            params = {
                "make": spec["make"],
                "model": spec.get(f"{dataset}_model", spec["model"]),
                "modelYear": spec["year"],
            }
            payload = client.get(endpoint, params)
            records = payload.get("results", payload.get("Results"))
            if not isinstance(records, list):
                raise ValueError("NHTSA response missing results list")
            yield (
                {
                    "url": endpoint,
                    "params": params,
                    "scope": f"{spec['make']}/{spec['model']}/{spec['year']}",
                },
                payload,
                [{**record, "_vehicle": spec} for record in records],
            )

    def consume(record, selected_mode):
        spec = record.pop("_vehicle")
        if (
            not spec["make"].strip()
            or not spec["model"].strip()
            or not 1900 <= int(spec["year"]) <= datetime.now().year + 2
        ):
            raise ValueError("Invalid vehicle identity")
        vehicle, _ = Vehicle.objects.get_or_create(
            mode=selected_mode,
            make=spec["make"].upper(),
            model=spec["model"].upper(),
            year=spec["year"],
        )
        if dataset == "complaints":
            values = parsers.complaint(record)
            identifier = values.pop("source_id")
            obj, changed = upsert(
                Complaint,
                {"mode": selected_mode, "source_id": identifier},
                {**values, "vehicle": vehicle},
            )
            earliest = (
                vehicle.complaints.order_by("filed_on").values_list("filed_on", flat=True).first()
            )
            if earliest and (vehicle.coverage_start is None or earliest < vehicle.coverage_start):
                vehicle.coverage_start = earliest
                vehicle.save(update_fields=["coverage_start"])
        else:
            values = parsers.recall(record)
            identifier = values.pop("campaign")
            obj, changed = upsert(Recall, {"mode": selected_mode, "campaign": identifier}, values)
            if not obj.vehicles.filter(pk=vehicle.pk).exists():
                obj.vehicles.add(vehicle)
                changed = True
        return changed

    try:
        return execute(f"nhtsa-{dataset}", mode, pages, consume)
    finally:
        client.close()
