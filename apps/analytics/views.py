import logging

from django.shortcuts import render
from django.views.decorators.http import require_GET

from .backends import get_backend
from .datasets import DATASETS
from .models import Publication

logger = logging.getLogger(__name__)


@require_GET
def analytics(request):
    mode = "live" if request.GET.get("mode") == "live" else "demo"
    dataset = request.GET.get("dataset", "supplier_risk_summary")
    if dataset not in DATASETS:
        dataset = "supplier_risk_summary"
    error = None
    rows = []
    try:
        result = get_backend().query(dataset, mode)
        rows = result.rows
    except Exception:
        logger.exception("Analytical query failed")
        error = "Analytical data is temporarily unavailable. Operational investigations remain available."
    publication = Publication.objects.filter(mode=mode).order_by("-created_at").first()
    return render(
        request,
        "analytics.html",
        {
            "active": "analytics",
            "title": "Analytics",
            "datasets": DATASETS,
            "selected": dataset,
            "columns": list(rows[0]) if rows else [],
            "records": [list(row.values()) for row in rows],
            "publication": publication,
            "error": error,
        },
    )
