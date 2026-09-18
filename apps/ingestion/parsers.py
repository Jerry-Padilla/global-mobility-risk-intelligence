import math
from datetime import date, datetime, timedelta, timezone

from .pipeline import digest


def finite(value, minimum, maximum):
    result = float(value)
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f"Value outside [{minimum}, {maximum}]: {value}")
    return result


def parse_date(value, day_first=False):
    if not value:
        raise ValueError("Missing date")
    formats = (
        ("%d/%m/%Y", "%Y-%m-%d", "%Y%m%d") if day_first else ("%m/%d/%Y", "%Y-%m-%d", "%Y%m%d")
    )
    for fmt in formats:
        try:
            result = datetime.strptime(str(value).split("T")[0], fmt).date()
            if result < date(1900, 1, 1) or result > date.today():
                raise ValueError("Date outside supported historical range")
            return result
        except ValueError:
            continue
    raise ValueError(f"Invalid date: {value}")


def boolean(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("y", "yes", "true", "1")


def earthquake(record):
    properties = record["properties"]
    lon, lat, depth = record["geometry"]["coordinates"]
    occurred = datetime.fromtimestamp(properties["time"] / 1000, tz=timezone.utc)
    if occurred > datetime.now(timezone.utc) + timedelta(minutes=10):
        raise ValueError("Earthquake timestamp is in the future")
    magnitude = finite(properties["mag"], 0, 10)
    identifier = str(record["id"]).strip()
    if not identifier:
        raise ValueError("Missing earthquake ID")
    return {
        "source_id": identifier,
        "kind": "earthquake",
        "title": properties.get("place") or identifier,
        "occurred_at": occurred,
        "expires_at": occurred + timedelta(days=7),
        "latitude": finite(lat, -90, 90),
        "longitude": finite(lon, -180, 180),
        "depth_km": finite(depth, -100, 1000),
        "magnitude": magnitude,
        "severity": max(0, min(1, (magnitude - 4) / 2.5)),
        "source_updated_at": datetime.fromtimestamp(
            properties.get("updated", properties["time"]) / 1000, tz=timezone.utc
        ),
        "payload_hash": digest(record),
        "url": properties.get("url", ""),
    }


def complaint(record):
    from apps.automotive.services import categorize

    narrative = record.get("summary", "") or ""
    categories, evidence = categorize(narrative)
    identifier = str(record["odiNumber"]).strip()
    if not identifier:
        raise ValueError("Missing complaint ID")
    injuries = int(record.get("numberOfInjuries") or 0)
    if injuries < 0:
        raise ValueError("Negative injury count")
    return {
        "source_id": identifier,
        "filed_on": parse_date(record["dateComplaintFiled"]),
        "incident_on": parse_date(record["dateOfIncident"])
        if record.get("dateOfIncident")
        else None,
        "component": record.get("components") or "UNKNOWN",
        "narrative": narrative,
        "crash": boolean(record.get("crash")),
        "fire": boolean(record.get("fire")),
        "injuries": injuries,
        "categories": categories,
        "evidence": evidence,
        "payload_hash": digest(record),
    }


def recall(record):
    campaign = str(record["NHTSACampaignNumber"]).strip()
    if not campaign:
        raise ValueError("Missing campaign ID")
    return {
        "campaign": campaign,
        "reported_on": parse_date(record["ReportReceivedDate"], day_first=True),
        "component": record.get("Component") or "UNKNOWN",
        "summary": record.get("Summary") or "",
        "consequence": record.get("Consequence") or "",
        "remedy": record.get("Remedy") or "",
        "payload_hash": digest(record),
    }
