from datetime import date, timedelta

import pytest

from apps.automotive.services import categorize, detect
from apps.risk.scoring import calculate, classify, exposure, haversine, projected_stockout


@pytest.mark.parametrize(
    "score,label",
    [
        (0, "LOW"),
        (24.99, "LOW"),
        (25, "MODERATE"),
        (50, "HIGH"),
        (75, "CRITICAL"),
        (100, "CRITICAL"),
        (None, "INCOMPLETE"),
    ],
)
def test_thresholds(score, label):
    assert classify(score) == label


def test_earthquake_scenario_is_critical_and_explainable():
    result = calculate(exposure("earthquake", 0.88, 15), 3.8, 14, 45, 5, 0)
    assert result.classification == "CRITICAL"
    assert result.value == round(sum(f["contribution"] for f in result.factors.values()), 2)


def test_inventory_and_alternatives_reduce_risk():
    low_stock = calculate(0.8, 3, 14, 45, 5, 0).value
    assert calculate(0.8, 15, 14, 45, 5, 0).value < low_stock
    assert calculate(0.8, 3, 14, 45, 5, 1).value < low_stock
    assert calculate(0.2, 3, 14, 45, 5, 0).value < low_stock


def test_missing_and_zero_consumption():
    assert calculate(0.8, None, 14, 45, 5, 0).classification == "INCOMPLETE"
    assert calculate(0.8, None, 14, 45, 5, 0, consuming=False).value is not None


def test_distance_edges():
    assert haversine(0, 0, 0, 0) == 0
    assert haversine(0, 179, 0, -179) == pytest.approx(222.39, rel=0.001)
    assert haversine(0, 0, 0, 180) == pytest.approx(20015.1, rel=0.001)
    with pytest.raises(ValueError):
        haversine(91, 0, 0, 0)
    with pytest.raises(ValueError):
        haversine(float("nan"), 0, 0, 0)


def test_late_inbound_does_not_prevent_stockout():
    today = date(2026, 9, 18)
    assert projected_stockout(
        380, 100, today, [(today + timedelta(days=7), 1000)]
    ) == today + timedelta(days=3)
    assert projected_stockout(
        380, 100, today, [(today + timedelta(days=2), 1000)]
    ) == today + timedelta(days=13)
    assert projected_stockout(380, 0, today, []) is None


def test_explainable_categories_and_word_boundaries():
    categories, evidence = categorize(
        "BRAKE warning; steering assist lost. Battery charging failed."
    )
    assert {"BRAKING", "STEERING", "BATTERY"}.issubset(categories)
    assert "steering" in evidence["matches"]["STEERING"]
    assert categorize("abstract discussion")[0] == ["UNCATEGORIZED"]


def test_anomaly_baseline_zero_variance_and_minimum_count():
    assert detect(104, [35] * 12)["expected"] == 35
    assert detect(35, [35] * 12) is None
    assert detect(104, [35] * 11) is None
    assert detect(9, [0] * 12) is None
    assert detect(10, [0] * 12)["increase_pct"] is None
