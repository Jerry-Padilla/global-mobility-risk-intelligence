import math
import re
import statistics
from collections import Counter
from datetime import date

from django.db import transaction

from .models import Anomaly, Complaint, Vehicle

KEYWORDS = {
    "BRAKING": ["brake", "braking", "abs"],
    "STEERING": ["steering", "steer"],
    "POWERTRAIN": ["transmission", "engine", "powertrain"],
    "BATTERY": ["battery", "charging"],
    "ELECTRICAL": ["electrical", "wiring", "short circuit"],
    "AIRBAG": ["airbag", "air bag"],
    "VISIBILITY": ["windshield", "wiper", "visibility"],
    "ADAS": ["autopilot", "lane assist", "adas"],
    "STRUCTURE": ["frame", "corrosion", "structure"],
}


def categorize(text):
    normalized = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    normalized = " ".join(normalized.split())
    evidence = {
        category: [word for word in words if re.search(r"\b" + re.escape(word) + r"\b", normalized)]
        for category, words in KEYWORDS.items()
    }
    evidence = {key: value for key, value in evidence.items() if value}
    return list(evidence) or ["UNCATEGORIZED"], {"version": "keywords-v1", "matches": evidence}


def month_shift(value, delta):
    ordinal = value.year * 12 + value.month - 1 + delta
    return date(ordinal // 12, ordinal % 12 + 1, 1)


def detect(observed, baseline):
    if len(baseline) != 12:
        return None
    expected = statistics.mean(baseline)
    deviation = max(statistics.pstdev(baseline), math.sqrt(max(expected, 1)))
    threshold = max(2 * expected, expected + 3 * deviation)
    if observed < 10 or observed <= threshold:
        return None
    return {
        "observed": observed,
        "expected": expected,
        "threshold": threshold,
        "increase_pct": (observed / expected - 1) * 100 if expected else None,
        "severity": "CRITICAL" if observed >= threshold * 2 else "HIGH",
    }


@transaction.atomic
def calculate_anomalies(mode, as_of):
    evaluation = month_shift(as_of, -1)
    baseline_start = month_shift(evaluation, -12)
    Anomaly.objects.filter(mode=mode, month=evaluation).delete()
    count = 0
    for vehicle in Vehicle.objects.filter(mode=mode, coverage_start__lte=baseline_start):
        rows = Complaint.objects.filter(
            vehicle=vehicle, filed_on__gte=baseline_start, filed_on__lt=month_shift(evaluation, 1)
        )
        counts = Counter((row.component, row.filed_on.replace(day=1)) for row in rows)
        for component in {key[0] for key in counts}:
            baseline = [
                counts[(component, month_shift(evaluation, -offset))] for offset in range(1, 13)
            ]
            result = detect(counts[(component, evaluation)], baseline)
            if result:
                Anomaly.objects.create(
                    mode=mode, vehicle=vehicle, component=component, month=evaluation, **result
                )
                count += 1
    return count
