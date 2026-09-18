"""Pure, versioned prioritization rules; scores are not damage probabilities."""

import math
from dataclasses import dataclass

WEIGHTS = {"environmental": 30, "inventory": 25, "sourcing": 20, "lead_time": 15, "criticality": 10}


def clamp(value):
    return max(0.0, min(1.0, value))


def haversine(lat1, lon1, lat2, lon2):
    if not all(math.isfinite(v) for v in (lat1, lon1, lat2, lon2)):
        raise ValueError("Coordinates must be finite")
    if not (
        -90 <= lat1 <= 90 and -90 <= lat2 <= 90 and -180 <= lon1 <= 180 and -180 <= lon2 <= 180
    ):
        raise ValueError("Coordinates out of bounds")
    a, b = math.radians(lat1), math.radians(lat2)
    dlat, dlon = b - a, math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(clamp(h)))


def exposure(kind, severity, distance):
    radius = 300 if kind == "earthquake" else 100
    return clamp(severity) * clamp(1 - distance / radius)


def classify(score):
    if score is None:
        return "INCOMPLETE"
    return (
        "CRITICAL"
        if score >= 75
        else "HIGH"
        if score >= 50
        else "MODERATE"
        if score >= 25
        else "LOW"
    )


@dataclass(frozen=True)
class Score:
    value: float | None
    classification: str
    factors: dict


def calculate(
    environmental, coverage, safety_days, lead_days, criticality, alternatives, consuming=True
):
    if consuming and coverage is None:
        return Score(None, "INCOMPLETE", {})
    factors = {
        "environmental": clamp(environmental),
        "inventory": clamp(1 - coverage / max(safety_days, 1)) if consuming else 0,
        "lead_time": clamp(1 - coverage / max(lead_days, 1)) if consuming else 0,
        "sourcing": 1.0 if alternatives == 0 else 0.0,
        "criticality": clamp(criticality / 5),
    }
    contributions = {
        key: {
            "normalized": round(value, 4),
            "weight": WEIGHTS[key],
            "contribution": round(value * WEIGHTS[key], 2),
        }
        for key, value in factors.items()
    }
    value = round(sum(item["contribution"] for item in contributions.values()), 2)
    return Score(value, classify(value), contributions)


def projected_stockout(quantity, daily_usage, as_of, inbound):
    """Only inventory arriving before exhaustion can postpone exhaustion."""
    from datetime import timedelta

    if daily_usage <= 0:
        return None
    coverage = quantity / daily_usage
    for arrival, amount in sorted(inbound):
        days = (arrival - as_of).days
        if days < 0 or days > coverage:
            continue
        coverage += amount / daily_usage
    return as_of + timedelta(days=math.floor(coverage))
