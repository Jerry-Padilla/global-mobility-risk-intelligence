from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, viewsets
from rest_framework.pagination import PageNumberPagination

from apps.automotive.models import Anomaly, Complaint, Recall
from apps.environmental.models import Event
from apps.supply_chain.models import Factory, Supplier


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class FactorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Factory
        fields = "__all__"


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"


class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = "__all__"


class RecallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recall
        fields = "__all__"


class AnomalySerializer(serializers.ModelSerializer):
    class Meta:
        model = Anomaly
        fields = "__all__"


@extend_schema(parameters=[OpenApiParameter("mode", str, enum=["demo", "live"], default="demo")])
class ReadOnlyDatasetViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        mode = "live" if self.request.query_params.get("mode") == "live" else "demo"
        return super().get_queryset().filter(mode=mode).order_by("pk")


class SupplierViewSet(ReadOnlyDatasetViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    filterset_fields = ["tier", "criticality"]
    search_fields = ["name", "code"]
    ordering_fields = ["name", "annual_spend", "criticality"]


class FactoryViewSet(ReadOnlyDatasetViewSet):
    queryset = Factory.objects.all()
    serializer_class = FactorySerializer
    filterset_fields = ["country", "product_family"]
    search_fields = ["name", "city"]
    ordering_fields = ["name", "production_capacity", "utilization"]


class EventViewSet(ReadOnlyDatasetViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    filterset_fields = ["kind", "source"]
    ordering_fields = ["occurred_at", "severity", "magnitude"]


class ComplaintViewSet(ReadOnlyDatasetViewSet):
    queryset = Complaint.objects.all()
    serializer_class = ComplaintSerializer
    filterset_fields = {
        "vehicle__make": ["exact"],
        "vehicle__model": ["exact"],
        "vehicle__year": ["exact"],
        "component": ["exact"],
        "filed_on": ["gte", "lte"],
    }
    search_fields = ["narrative", "component"]
    ordering_fields = ["filed_on", "injuries"]


class RecallViewSet(ReadOnlyDatasetViewSet):
    queryset = Recall.objects.prefetch_related("vehicles")
    serializer_class = RecallSerializer
    filterset_fields = ["component", "vehicles__make", "vehicles__model", "vehicles__year"]
    ordering_fields = ["reported_on", "campaign"]


class AnomalyViewSet(ReadOnlyDatasetViewSet):
    queryset = Anomaly.objects.all()
    serializer_class = AnomalySerializer
    filterset_fields = ["component", "severity", "vehicle__make", "vehicle__model", "vehicle__year"]
    ordering_fields = ["month", "observed", "increase_pct"]
