from datetime import date

from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Count, Max, Prefetch, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from apps.automotive.models import Anomaly, Complaint, Recall, Vehicle
from apps.environmental.models import Event
from apps.ingestion.models import IngestionRun, QualityIssue, SourceState
from apps.risk.models import Assessment
from apps.risk.services import latest_assessments
from apps.supply_chain.models import Factory, Shipment, Sourcing, Supplier, SupplierSite


def dataset(request):
    return "live" if request.GET.get("mode") == "live" else "demo"


def summary(mode):
    rows = list(latest_assessments(mode))
    high = [r for r in rows if r.score is not None and r.score >= 50]
    coverage = {r.requirement_id: r.days_of_supply for r in rows if r.days_of_supply is not None}
    return {
        "critical": sum(r.classification == "CRITICAL" for r in rows),
        "suppliers": len({r.source.site.supplier_id for r in high}),
        "factories": len({r.requirement.factory_id for r in high}),
        "parts": len({r.requirement.part_id for r in high}),
        "coverage": round(sum(coverage.values()) / len(coverage), 1) if coverage else None,
        "anomalies": Anomaly.objects.filter(mode=mode).count(),
        "assessments": rows,
        "as_of": rows[0].run.as_of if rows else None,
    }


@require_GET
def dashboard(request):
    context = summary(dataset(request))
    context.update(
        {
            "active": "dashboard",
            "title": "Operations overview",
            "risks": context["assessments"][:8],
            "events": Event.objects.filter(mode=dataset(request)).order_by("-occurred_at")[:4],
            "scenario": next(
                (r for r in context["assessments"] if r.event and r.event.kind == "earthquake"),
                None,
            ),
        }
    )
    return render(request, "dashboard.html", context)


@require_GET
def investigation(request, pk):
    mode = dataset(request)
    risk = get_object_or_404(
        Assessment.objects.select_related(
            "run", "event", "source__site__supplier", "requirement__part", "requirement__factory"
        ),
        pk=pk,
        run__mode=mode,
    )
    candidates = (
        Sourcing.objects.filter(part=risk.requirement.part, site__mode=mode, active=True)
        .exclude(site__supplier=risk.source.site.supplier)
        .select_related("site__supplier")
    )
    alternatives = []
    for candidate in candidates:
        candidate.lead_delta = candidate.lead_time_days - risk.source.lead_time_days
        candidate.cost_difference = candidate.cost_delta_pct - risk.source.cost_delta_pct
        candidate.within_coverage = (
            risk.days_of_supply is not None and candidate.lead_time_days <= risk.days_of_supply
        )
        alternatives.append(candidate)
    inventory = (
        risk.requirement.inventory.filter(date__lte=risk.run.as_of.date()).order_by("-date").first()
    )
    return render(
        request,
        "investigation.html",
        {
            "title": "From disruption to decision",
            "active": "supply-chain",
            "risk": risk,
            "as_of": risk.run.as_of,
            "inventory": inventory,
            "alternatives": alternatives,
            "has_approved": any(c.qualification == "approved" for c in alternatives),
        },
    )


@require_GET
def entity_list(request, kind):
    mode = dataset(request)
    is_supplier = kind == "suppliers"
    objects = (
        Supplier.objects.filter(mode=mode).prefetch_related("sites")
        if is_supplier
        else Factory.objects.filter(mode=mode)
    )
    query = request.GET.get("q", "").strip()[:100]
    if query:
        objects = objects.filter(name__icontains=query)
    assessments = list(latest_assessments(mode))
    scores = {}
    for row in assessments:
        key = row.source.site.supplier_id if is_supplier else row.requirement.factory_id
        if key not in scores or (row.score or 0) > (scores[key].score or 0):
            scores[key] = row
    page = Paginator(objects.order_by("name"), 25).get_page(request.GET.get("page"))
    for obj in page:
        obj.risk = scores.get(obj.pk)
        obj.location = next(iter(obj.sites.all()), None) if is_supplier else obj
    context = {
        "active": kind,
        "title": kind.title(),
        "page_obj": page,
        "kind": kind,
        "q": query,
        "is_supplier": is_supplier,
    }
    return render(
        request,
        "partials/entity_table.html" if request.headers.get("HX-Request") else "entities.html",
        context,
    )


@require_GET
def entity_detail(request, kind, pk):
    mode = dataset(request)
    supplier = kind == "suppliers"
    entity = get_object_or_404(Supplier if supplier else Factory, pk=pk, mode=mode)
    filters = {"source__site__supplier": entity} if supplier else {"requirement__factory": entity}
    risks = list(
        latest_assessments(mode)
        .filter(**filters)
        .prefetch_related(
            Prefetch(
                "requirement__part__sources",
                queryset=Sourcing.objects.filter(
                    qualification="approved", active=True
                ).select_related("site__supplier", "part"),
                to_attr="approved_sources",
            )
        )
    )
    history = list(
        Assessment.objects.filter(run__mode=mode, **filters)
        .values("run__as_of")
        .annotate(score=Max("score"))
        .order_by("run__as_of")
    )
    chart = {
        "x": [r["run__as_of"].isoformat() for r in history],
        "y": [r["score"] for r in history],
    }
    shipments = Shipment.objects.filter(
        mode=mode, **({"source__supplier": entity} if supplier else {"factory": entity})
    ).select_related("factory", "source")[:30]
    alternatives = []
    seen = set()
    for risk in risks:
        for source in risk.requirement.part.approved_sources:
            if source.site.supplier_id != risk.source.site.supplier_id and source.pk not in seen:
                seen.add(source.pk)
                alternatives.append(source)
    return render(
        request,
        "detail.html",
        {
            "active": kind,
            "title": entity.name,
            "entity": entity,
            "is_supplier": supplier,
            "risks": risks,
            "history": chart,
            "shipments": shipments,
            "alternatives": alternatives,
            "top_risk": risks[0] if risks else None,
            "average_lead_time": sum({r.source_id: r.source.lead_time_days for r in risks}.values())
            / len({r.source_id for r in risks})
            if risks
            else None,
            "single_source_parts": len(
                {
                    r.requirement.part_id
                    for r in risks
                    if r.factors.get("sourcing", {}).get("normalized") == 1
                }
            ),
            "below_safety_stock": len(
                {
                    r.requirement_id
                    for r in risks
                    if r.days_of_supply is not None
                    and r.days_of_supply < r.requirement.part.safety_stock_days
                }
            ),
            "location": entity.sites.first() if supplier else entity,
        },
    )


@require_GET
def global_risk(request):
    mode = dataset(request)
    events = Event.objects.filter(mode=mode).order_by("-occurred_at")
    risks = latest_assessments(mode).filter(event__isnull=False)
    selected = None
    if request.GET.get("event", "").isdigit():
        selected = get_object_or_404(Event, pk=request.GET["event"], mode=mode)
        events = events.filter(pk=selected.pk)
        risks = risks.filter(event=selected)
    return render(
        request,
        "global_risk.html",
        {
            "active": "global-risk",
            "title": "Global risk",
            "events": events[:100],
            "risks": risks[:100],
            "selected_event": selected,
        },
    )


@require_GET
def supply_chain(request):
    risks = latest_assessments(dataset(request))
    if request.GET.get("supplier", "").isdigit():
        risks = risks.filter(source__site__supplier_id=request.GET["supplier"])
    graph = [
        {
            "supplier": r.source.site.supplier.name,
            "part": r.requirement.part.number,
            "factory": r.requirement.factory.name,
            "score": r.score,
        }
        for r in risks[:30]
    ]
    return render(
        request,
        "supply_chain.html",
        {
            "active": "supply-chain",
            "title": "Supply chain dependencies",
            "risks": risks[:100],
            "graph": graph,
            "suppliers": Supplier.objects.filter(mode=dataset(request)).order_by("name"),
        },
    )


def automotive_filters(request, rows, vehicle_prefix="vehicle__"):
    for field in ("make", "model", "year"):
        value = request.GET.get(field, "")
        if value and (field != "year" or value.isdigit()):
            rows = rows.filter(
                **{
                    f"{vehicle_prefix}{field}__iexact"
                    if field != "year"
                    else f"{vehicle_prefix}{field}": value
                }
            )
    if request.GET.get("component"):
        rows = rows.filter(component__icontains=request.GET["component"][:100])
    date_field = "reported_on" if rows.model == Recall else "filed_on"
    for query, lookup in (("start", "gte"), ("end", "lte")):
        try:
            value = date.fromisoformat(request.GET.get(query, ""))
            rows = rows.filter(**{f"{date_field}__{lookup}": value})
        except ValueError:
            continue
    return rows.distinct()


@require_GET
def automotive(request, section="vehicle-safety"):
    mode = dataset(request)
    complaints = automotive_filters(
        request, Complaint.objects.filter(mode=mode).select_related("vehicle")
    )
    recalls = automotive_filters(
        request, Recall.objects.filter(mode=mode).prefetch_related("vehicles"), "vehicles__"
    )
    timeline = list(
        complaints.annotate(month=TruncMonth("filed_on"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )
    components = list(
        complaints.values("component").annotate(count=Count("id")).order_by("-count")[:10]
    )
    years = list(
        complaints.values("vehicle__year").annotate(count=Count("id")).order_by("vehicle__year")
    )
    recall_timeline = list(
        recalls.annotate(month=TruncMonth("reported_on"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )
    totals = complaints.aggregate(
        count=Count("id"),
        crashes=Count("id", filter=Q(crash=True)),
        fires=Count("id", filter=Q(fire=True)),
        injuries=Sum("injuries"),
    )
    chart = {
        "timeline": [{"month": r["month"].isoformat(), "count": r["count"]} for r in timeline],
        "total_complaints": totals["count"],
        "components": components,
        "years": years,
        "recalls": [
            {"month": r["month"].isoformat(), "count": r["count"]} for r in recall_timeline
        ],
    }
    rows = (
        recalls.order_by("-reported_on")
        if section == "recalls"
        else complaints.order_by("-filed_on")
    )
    anomalies = Anomaly.objects.filter(
        mode=mode, vehicle_id__in=complaints.values("vehicle_id")
    ).select_related("vehicle")
    if request.GET.get("component"):
        anomalies = anomalies.filter(component__icontains=request.GET["component"])
    return render(
        request,
        "automotive.html",
        {
            "active": section,
            "title": section.replace("-", " ").title(),
            "totals": totals,
            "recall_count": recalls.count(),
            "chart": chart,
            "anomalies": anomalies,
            "page_obj": Paginator(rows, 25).get_page(request.GET.get("page")),
            "vehicles": Vehicle.objects.filter(mode=mode),
        },
    )


@require_GET
def data_health(request):
    mode = dataset(request)
    return render(
        request,
        "data_health.html",
        {
            "active": "data-health",
            "title": "Data health",
            "runs": IngestionRun.objects.filter(mode=mode).order_by("-started_at")[:50],
            "states": SourceState.objects.filter(mode=mode),
            "issues": QualityIssue.objects.filter(run__mode=mode)
            .select_related("run")
            .order_by("-id")[:30],
        },
    )


@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok", "database": "postgresql"})
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)


@require_GET
def dashboard_api(request):
    data = summary(dataset(request))
    data.pop("assessments")
    return JsonResponse(data)


@require_GET
def geojson(request):
    mode = dataset(request)
    try:
        west, south, east, north = map(float, request.GET.get("bbox", "-180,-90,180,90").split(","))
        if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
            raise ValueError
    except ValueError:
        return JsonResponse(
            {"error": "bbox must be west,south,east,north in valid coordinate bounds"}, status=400
        )
    features = []
    for model, kind in ((Factory, "factory"), (SupplierSite, "supplier"), (Event, "event")):
        rows = model.objects.filter(
            mode=mode, latitude__range=(south, north), longitude__range=(west, east)
        ).order_by("pk")[:500]
        for row in rows:
            url = (
                f"/suppliers/{row.supplier_id}/"
                if kind == "supplier"
                else f"/factories/{row.pk}/"
                if kind == "factory"
                else "/global-risk/"
            )
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [row.longitude, row.latitude]},
                    "properties": {
                        "id": row.pk,
                        "name": row.title if kind == "event" else row.name,
                        "kind": row.kind if kind == "event" else kind,
                        "url": f"{url}?mode={mode}"
                        + (f"&event={row.pk}" if kind == "event" else ""),
                    },
                }
            )
    return JsonResponse({"type": "FeatureCollection", "features": features, "limit_per_layer": 500})
