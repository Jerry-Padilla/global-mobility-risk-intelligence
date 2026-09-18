from datetime import datetime, timezone
from unittest.mock import Mock

import httpx
import pytest

from apps.automotive.models import Complaint, Recall
from apps.environmental.models import Event, WeatherReading
from apps.ingestion.models import IngestionRun, RawRecord, SourceState
from apps.ingestion.parsers import boolean, earthquake, parse_date, recall
from apps.ingestion.pipeline import PublicClient, execute
from apps.ingestion.sources import ingest_nhtsa, ingest_usgs, ingest_weather
from apps.supply_chain.models import Factory


def quake(magnitude=6.2):
    timestamp = int(datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp() * 1000)
    return {
        "id": "us-test",
        "properties": {
            "time": timestamp,
            "updated": timestamp,
            "mag": magnitude,
            "place": "Test event",
        },
        "geometry": {"coordinates": [120.9, 24.8, 10]},
    }


def test_parser_validation():
    assert earthquake(quake())["magnitude"] == 6.2
    with pytest.raises(ValueError):
        earthquake(quake(15))
    assert boolean("N") is False
    assert boolean("Y") is True
    assert parse_date("09/01/2026").isoformat() == "2026-09-01"
    with pytest.raises(ValueError):
        parse_date("tomorrow")


def test_recall_dates_are_day_first():
    parsed = recall({"NHTSACampaignNumber": "22V324000", "ReportReceivedDate": "11/05/2022"})
    assert parsed["reported_on"].isoformat() == "2022-05-11"


@pytest.mark.django_db
def test_usgs_idempotent_updates_and_raw_evidence(data_root):
    client = Mock()
    client.get.return_value = {"features": [quake()]}
    first = ingest_usgs(client=client)
    second = ingest_usgs(client=client)
    assert (first.loaded, second.skipped) == (1, 1)
    assert Event.objects.filter(mode="live").count() == 1
    client.get.return_value = {"features": [quake(6.5)]}
    assert ingest_usgs(client=client).loaded == 1
    assert Event.objects.get(mode="live").magnitude == 6.5
    assert RawRecord.objects.count() == 3
    assert all((data_root / r.path).exists() for r in RawRecord.objects.all())
    assert SourceState.objects.get(source="usgs").watermark is not None


@pytest.mark.django_db
def test_rejections_preserve_watermark(data_root):
    client = Mock()
    client.get.return_value = {"features": [quake(99)]}
    run = ingest_usgs(client=client)
    assert run.status == "partial"
    assert run.rejected == 1
    assert SourceState.objects.get(source="usgs").watermark is None
    assert run.issues.count() == 1


@pytest.mark.django_db
def test_api_failure_is_visible_and_does_not_advance(data_root):
    def pages(watermark):
        raise httpx.ConnectError("offline")
        yield

    with pytest.raises(httpx.ConnectError):
        execute("test", "live", pages, lambda record, mode: True)
    assert IngestionRun.objects.get(source="test").status == "failed"
    assert SourceState.objects.get(source="test").watermark is None


@pytest.mark.django_db
def test_complaint_and_recall_reconciliation(data_root):
    client = Mock()
    watchlist = [{"make": "ASTER", "model": "E4", "year": 2024}]
    client.get.return_value = {
        "results": [
            {
                "odiNumber": 123,
                "dateComplaintFiled": "09/01/2026",
                "components": "STEERING",
                "summary": "Steering assist failed",
                "crash": "N",
                "fire": "N",
                "numberOfInjuries": 0,
            }
        ]
    }
    assert ingest_nhtsa(client=client, watchlist=watchlist).loaded == 1
    assert ingest_nhtsa(client=client, watchlist=watchlist).skipped == 1
    assert Complaint.objects.get(mode="live").crash is False
    client.get.return_value = {
        "results": [
            {
                "NHTSACampaignNumber": "26V001",
                "ReportReceivedDate": "09/01/2026",
                "Component": "STEERING",
                "Summary": "Inspect controller",
            }
        ]
    }
    ingest_nhtsa("recalls", client=client, watchlist=watchlist)
    ingest_nhtsa(
        "recalls", client=client, watchlist=[{"make": "ASTER", "model": "E5", "year": 2024}]
    )
    assert Recall.objects.get(mode="live").vehicles.count() == 2


@pytest.mark.django_db
def test_weather_repeat_and_threshold(data_root):
    Factory.objects.create(
        mode="live",
        code="L1",
        name="Live facility",
        city="Houston",
        country="US",
        latitude=29,
        longitude=-95,
        production_capacity=100,
        product_family="EV",
    )
    client = Mock()
    client.get.return_value = {
        "current": {
            "time": "2026-09-01T12:00",
            "temperature_2m": 25,
            "precipitation": 1,
            "wind_speed_10m": 100,
        }
    }
    assert ingest_weather(client=client).loaded == 1
    assert ingest_weather(client=client).skipped == 1
    assert WeatherReading.objects.count() == 1
    assert Event.objects.filter(source="open-meteo").count() == 1


def test_http_client_with_mock_transport():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"features": []})

    client = PublicClient(httpx.Client(transport=httpx.MockTransport(handler)), minimum_interval=0)
    assert client.get("https://example.test", {"format": "geojson"}) == {"features": []}
    assert calls[0].url.params["format"] == "geojson"
    client.close()


def test_transient_http_retry_is_bounded(monkeypatch):
    monkeypatch.setattr("apps.ingestion.pipeline.time.sleep", lambda delay: None)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    client = PublicClient(httpx.Client(transport=httpx.MockTransport(handler)), minimum_interval=0)
    with pytest.raises(httpx.HTTPStatusError):
        client.get("https://example.test", {})
    assert len(calls) == 4


@pytest.mark.django_db(transaction=True)
def test_advisory_lock_excludes_another_connection():
    import hashlib

    import psycopg
    from django.db import connection

    from apps.ingestion.pipeline import job_lock

    key = "test-lock"
    lock_id = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], signed=True)
    config = connection.settings_dict
    with job_lock(key):
        with psycopg.connect(
            dbname=config["NAME"],
            user=config["USER"],
            password=config["PASSWORD"],
            host=config["HOST"],
            port=config["PORT"],
        ) as other:
            assert (
                other.execute("SELECT pg_try_advisory_lock(%s)", [lock_id]).fetchone()[0] is False
            )
