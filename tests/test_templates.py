from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import RequestFactory

from apps.core.templatetags.ui import factor_label


def test_map_carries_detail_location():
    html = render_to_string(
        "partials/map.html", {"location": {"latitude": 24.8, "longitude": 120.9}}
    )
    assert 'data-latitude="24.8"' in html
    assert 'data-longitude="120.9"' in html


def test_map_without_selected_location_is_global():
    html = render_to_string("partials/map.html", {})
    assert 'data-latitude=""' in html


def test_factor_names_are_readable():
    assert factor_label("lead_time") == "Lead Time"


def test_factory_profile_template_without_database():
    request = RequestFactory().get("/factories/1/?mode=demo")
    factory = SimpleNamespace(
        name="Test factory",
        city="Fremont",
        country="US",
        latitude=37.49,
        longitude=-121.94,
        production_capacity=120000,
        utilization=0.85,
        criticality=5,
        product_family="EV",
    )
    html = render_to_string(
        "detail.html",
        {
            "title": factory.name,
            "entity": factory,
            "location": factory,
            "is_supplier": False,
            "risks": [],
            "history": {"x": [], "y": []},
            "shipments": [],
            "alternatives": [],
            "below_safety_stock": 2,
        },
        request=request,
    )
    assert "Current utilization" in html
    assert "85%" in html
    assert "Parts below safety stock" in html


def test_event_context_is_escaped():
    request = RequestFactory().get("/global-risk/?event=1")
    html = render_to_string(
        "global_risk.html",
        {"selected_event": {"title": "<script>alert(1)</script>"}, "risks": [], "events": []},
        request=request,
    )
    assert "&lt;script&gt;" in html
    assert "<script>alert(1)</script>" not in html
