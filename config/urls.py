from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.analytics.views import analytics
from apps.core import api, views

router = DefaultRouter()
for prefix, view, name in [
    ("suppliers", api.SupplierViewSet, "supplier"),
    ("factories", api.FactoryViewSet, "factory"),
    ("risk/events", api.EventViewSet, "event"),
    ("automotive/complaints", api.ComplaintViewSet, "complaint"),
    ("automotive/recalls", api.RecallViewSet, "recall"),
    ("automotive/anomalies", api.AnomalyViewSet, "anomaly"),
]:
    router.register(prefix, view, basename=name)

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("investigations/<int:pk>/", views.investigation, name="investigation"),
    path("admin/", admin.site.urls),
    path("analytics/", analytics),
    path("health/", views.health),
    path("global-risk/", views.global_risk),
    path("supply-chain/", views.supply_chain),
    path("data-health/", views.data_health),
    path("vehicle-safety/", views.automotive),
    path("complaints/", views.automotive, {"section": "complaints"}),
    path("recalls/", views.automotive, {"section": "recalls"}),
    path("api/v1/map/", views.geojson),
    path("api/v1/dashboard/", views.dashboard_api),
    path("api/v1/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
for kind in ("suppliers", "factories"):
    urlpatterns += [
        path(f"{kind}/", views.entity_list, {"kind": kind}),
        path(f"{kind}/<int:pk>/", views.entity_detail, {"kind": kind}),
    ]
