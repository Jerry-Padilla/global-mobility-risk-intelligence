from datetime import datetime, time, timezone

from django.db import transaction
from django.db.models import F

from apps.environmental.models import Event
from apps.supply_chain.models import Requirement, ShipmentLine

from .models import Assessment, CalculationRun
from .scoring import calculate, exposure, haversine, projected_stockout


@transaction.atomic
def calculate_risks(mode, as_of):
    instant = datetime.combine(as_of, time(12), tzinfo=timezone.utc)
    run, _ = CalculationRun.objects.get_or_create(
        mode=mode, as_of=instant, model_version="weighted-v1"
    )
    run.assessments.all().delete()
    events = list(
        Event.objects.filter(mode=mode, occurred_at__lte=instant, expires_at__gte=instant)
    )
    requirements = (
        Requirement.objects.filter(factory__mode=mode, part__mode=mode)
        .select_related("factory", "part")
        .prefetch_related("part__sources__site__supplier", "inventory")
    )
    inbound = {}
    route_hubs = {}
    for line in ShipmentLine.objects.filter(
        shipment__mode=mode,
        shipment__status__in=["in_transit", "delayed"],
        shipment__ship_date__lte=as_of,
        shipment__hub__isnull=False,
    ).select_related("shipment__hub"):
        route_hubs.setdefault(
            (line.shipment.source_id, line.shipment.factory_id, line.part_id), []
        ).append(line.shipment.hub)
    for line in ShipmentLine.objects.filter(
        shipment__mode=mode, shipment__status="in_transit", shipment__estimated_arrival__gte=as_of
    ).select_related("shipment"):
        inbound.setdefault((line.shipment.factory_id, line.part_id), []).append(
            (line.shipment.estimated_arrival, line.quantity)
        )
    assessments = []
    for req in requirements:
        snapshot = max(
            (row for row in req.inventory.all() if row.date <= as_of),
            key=lambda row: row.date,
            default=None,
        )
        coverage = snapshot.days_of_supply if snapshot else None
        sources = [
            s
            for s in req.part.sources.all()
            if s.active and s.qualification == "approved" and s.site.mode == mode
        ]
        for source in sources:
            candidates = []
            # Both an origin-site disruption and a direct factory threat affect the dependency.
            for event in events:
                distance = min(
                    haversine(site.latitude, site.longitude, event.latitude, event.longitude)
                    for site in [
                        source.site,
                        req.factory,
                        *route_hubs.get((source.site_id, req.factory_id, req.part_id), []),
                    ]
                )
                value = exposure(event.kind, event.severity, distance)
                if value > 0:
                    candidates.append((value, distance, event))
            env, distance, event = max(candidates, key=lambda row: row[0], default=(0, None, None))
            alternatives = len(
                {
                    s.site.supplier_id
                    for s in sources
                    if s.site.supplier_id != source.site.supplier_id
                }
            )
            result = calculate(
                env,
                coverage,
                req.part.safety_stock_days,
                source.lead_time_days,
                source.site.supplier.criticality,
                alternatives,
                req.daily_usage > 0,
            )
            stockout = (
                projected_stockout(
                    snapshot.quantity,
                    req.daily_usage,
                    as_of,
                    inbound.get((req.factory_id, req.part_id), []),
                )
                if snapshot
                else None
            )
            assessments.append(
                Assessment(
                    run=run,
                    requirement=req,
                    source=source,
                    event=event,
                    score=result.value,
                    classification=result.classification,
                    days_of_supply=coverage,
                    distance_km=distance,
                    factors=result.factors,
                    stockout_on=stockout,
                    explanation="Inventory snapshot missing"
                    if snapshot is None
                    else "No current consumption"
                    if not req.daily_usage
                    else f"{alternatives} approved alternative supplier(s); inventory as of {snapshot.date}",
                )
            )
    Assessment.objects.bulk_create(assessments)
    return run


def latest_assessments(mode):
    run = CalculationRun.objects.filter(mode=mode).order_by("-as_of", "-id").first()
    return (
        Assessment.objects.filter(run=run)
        .select_related(
            "source__site__supplier", "requirement__factory", "requirement__part", "event", "run"
        )
        .order_by(F("score").desc(nulls_last=True), "id")
        if run
        else Assessment.objects.none()
    )
