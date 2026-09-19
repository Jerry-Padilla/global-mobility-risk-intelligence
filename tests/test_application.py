from datetime import date

import pytest
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.test.utils import CaptureQueriesContext

from apps.automotive.models import Anomaly, Complaint
from apps.risk.models import CalculationRun
from apps.risk.services import latest_assessments
from apps.supply_chain.models import Factory, InventorySnapshot, Supplier

pytestmark = pytest.mark.django_db


def test_scenarios_and_seed_idempotence(demo):
    assert (Factory.objects.count(), Supplier.objects.count()) == (8, 40)
    critical = latest_assessments("demo").get(
        source__site__supplier__code="S001", requirement__part__number="GM-10000"
    )
    assert critical.classification == "CRITICAL"
    assert critical.event.kind == "earthquake"
    assert critical.days_of_supply == pytest.approx(3.8)
    assert latest_assessments("demo").filter(event__kind="weather").exists()
    assert Anomaly.objects.get(mode="demo").observed == 104
    counts = (
        CalculationRun.objects.count(),
        Complaint.objects.count(),
        InventorySnapshot.objects.count(),
    )
    call_command("generate_company_data", as_of=date(2026, 9, 18), verbosity=0)
    assert counts == (
        CalculationRun.objects.count(),
        Complaint.objects.count(),
        InventorySnapshot.objects.count(),
    )


@pytest.mark.parametrize(
    "url",
    [
        "/",
        "/suppliers/",
        "/factories/",
        "/global-risk/",
        "/supply-chain/",
        "/vehicle-safety/",
        "/recalls/",
        "/complaints/",
        "/analytics/",
        "/data-health/",
    ],
)
def test_pages_render(client, demo, url):
    response = client.get(url)
    assert response.status_code == 200
    assert b"DEMONSTRATION DATA" in response.content


def test_api_is_read_only_and_dataset_isolation(client, demo):
    assert client.get("/api/v1/suppliers/").json()["count"] == 40
    assert client.get("/api/v1/suppliers/?mode=live").json()["count"] == 0
    supplier = Supplier.objects.first()
    assert client.get(f"/api/v1/suppliers/{supplier.pk}/?mode=live").status_code == 404
    assert client.post("/api/v1/suppliers/", {}).status_code == 405
    assert client.get("/admin/").status_code == 302
    assert (
        client.get("/api/v1/automotive/complaints/?page_size=1000").json()["results"].__len__()
        == 200
    )
    assert (
        client.get("/api/v1/automotive/complaints/?vehicle__make=Nonexistent").json()["count"] == 0
    )


def test_detail_query_budget_and_htmx(client, demo):
    supplier = Supplier.objects.get(code="S001")
    with CaptureQueriesContext(connection) as captured:
        response = client.get(f"/suppliers/{supplier.pk}/")
    assert response.status_code == 200
    assert len(captured) < 18
    response = client.get("/suppliers/?q=Taiwan", HTTP_HX_REQUEST="true")
    assert b"Taiwan Precision" in response.content
    assert b"<html" not in response.content


def test_geojson_bounds(client, demo):
    assert client.get("/api/v1/map/?bbox=bad").status_code == 400
    assert client.get("/api/v1/map/?bbox=nan,-90,180,90").status_code == 400
    assert client.get("/api/v1/map/").json()["features"]
    assert not client.get("/api/v1/map/?mode=live").json()["features"]


def test_database_constraints(demo):
    snapshot = InventorySnapshot.objects.first()
    with pytest.raises(IntegrityError), transaction.atomic():
        InventorySnapshot.objects.filter(pk=snapshot.pk).update(quantity=-1)
    factory = Factory.objects.first()
    with pytest.raises(IntegrityError), transaction.atomic():
        Factory.objects.filter(pk=factory.pk).update(latitude=100)


def test_relationship_mode_validation(demo):
    from django.core.exceptions import ValidationError

    from apps.supply_chain.models import Part, Requirement

    factory = Factory.objects.create(
        mode="live",
        code="live1",
        name="Live",
        city="Detroit",
        country="US",
        latitude=42,
        longitude=-83,
        production_capacity=10,
        product_family="EV",
    )
    relationship = Requirement(factory=factory, part=Part.objects.first(), daily_usage=10)
    with pytest.raises(ValidationError, match="same dataset"):
        relationship.full_clean()


def test_event_investigation_is_scoped(client, demo):
    from apps.environmental.models import Event

    event = Event.objects.get(mode="demo", source_id="scenario-earthquake")
    response = client.get(f"/global-risk/?event={event.pk}")
    assert response.status_code == 200
    assert all(r.event_id == event.pk for r in response.context["risks"])
    assert client.get(f"/global-risk/?mode=live&event={event.pk}").status_code == 404


def test_live_empty_state_and_filters(client, demo):
    response = client.get("/suppliers/?mode=live")
    assert b"No suppliers match" in response.content
    assert b"Taiwan Precision" not in response.content
    response = client.get("/complaints/?component=BATTERY")
    assert b"No records match" in response.content


@pytest.mark.parametrize("route", ["/recalls/", "/complaints/", "/vehicle-safety/"])
def test_vehicle_dropdowns_preserve_filters_and_mode(client, demo, route):
    response = client.get(route, {"make": "Aster", "model": "E4", "component": "STEERING"})
    assert response.status_code == 200
    assert b'<select name="make"' in response.content
    assert b'<select name="component"' in response.content
    assert b'value="Aster" selected' in response.content
    assert b"Reset filters" in response.content
    live = client.get(route, {"mode": "live"})
    assert b'value="Aster"' not in live.content
