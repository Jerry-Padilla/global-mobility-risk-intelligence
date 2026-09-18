from django.db import models
from django.db.models import Q

from apps.core.models import DatasetModel, DatasetRelation, LocatedModel


class Factory(LocatedModel):
    code = models.CharField(max_length=30)
    production_capacity = models.PositiveIntegerField()
    utilization = models.FloatField(default=0)
    criticality = models.PositiveSmallIntegerField(default=3)
    product_family = models.CharField(max_length=100)

    class Meta(LocatedModel.Meta):
        constraints = LocatedModel.Meta.constraints + [
            models.UniqueConstraint(fields=["mode", "code"], name="factory_code"),
            models.CheckConstraint(
                condition=Q(utilization__gte=0, utilization__lte=1), name="factory_utilization"
            ),
            models.CheckConstraint(
                condition=Q(criticality__gte=1, criticality__lte=5), name="factory_criticality"
            ),
        ]


class Supplier(DatasetModel):
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=160)
    tier = models.PositiveSmallIntegerField(default=1)
    annual_spend = models.DecimalField(max_digits=16, decimal_places=2)
    criticality = models.PositiveSmallIntegerField(default=3)
    reliability = models.FloatField(default=0.95)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["mode", "code"], name="supplier_code"),
            models.CheckConstraint(condition=Q(annual_spend__gte=0), name="supplier_spend"),
            models.CheckConstraint(
                condition=Q(criticality__gte=1, criticality__lte=5), name="supplier_criticality"
            ),
            models.CheckConstraint(
                condition=Q(reliability__gte=0, reliability__lte=1), name="supplier_reliability"
            ),
        ]

    def __str__(self):
        return self.name


class SupplierSite(LocatedModel):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="sites")

    class Meta(LocatedModel.Meta):
        constraints = LocatedModel.Meta.constraints + [
            models.UniqueConstraint(fields=["supplier", "name"], name="supplier_site_name")
        ]


class Part(DatasetModel):
    number = models.CharField(max_length=40)
    description = models.CharField(max_length=180)
    commodity = models.CharField(max_length=60, db_index=True)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    safety_stock_days = models.PositiveSmallIntegerField(default=14)
    criticality = models.PositiveSmallIntegerField(default=3)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["mode", "number"], name="part_number"),
            models.CheckConstraint(condition=Q(unit_cost__gte=0), name="part_cost"),
            models.CheckConstraint(
                condition=Q(criticality__gte=1, criticality__lte=5), name="part_criticality"
            ),
        ]

    def __str__(self):
        return self.number


class Sourcing(DatasetRelation):
    part = models.ForeignKey(Part, on_delete=models.CASCADE, related_name="sources")
    site = models.ForeignKey(SupplierSite, on_delete=models.CASCADE, related_name="sources")
    qualification = models.CharField(
        max_length=20,
        choices=[("approved", "Approved"), ("pending", "Pending")],
        default="approved",
    )
    is_primary = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    lead_time_days = models.PositiveSmallIntegerField()
    cost_delta_pct = models.FloatField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["part", "site"], name="part_site_source")]


class Requirement(DatasetRelation):
    factory = models.ForeignKey(Factory, on_delete=models.CASCADE, related_name="requirements")
    part = models.ForeignKey(Part, on_delete=models.CASCADE, related_name="requirements")
    daily_usage = models.FloatField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["factory", "part"], name="factory_part_requirement"),
            models.CheckConstraint(condition=Q(daily_usage__gte=0), name="requirement_usage"),
        ]


class InventorySnapshot(DatasetRelation):
    requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE, related_name="inventory")
    date = models.DateField(db_index=True)
    quantity = models.FloatField()
    safety_stock = models.FloatField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["requirement", "date"], name="inventory_snapshot"),
            models.CheckConstraint(
                condition=Q(quantity__gte=0, safety_stock__gte=0), name="inventory_nonnegative"
            ),
        ]

    @property
    def days_of_supply(self):
        usage = self.requirement.daily_usage
        return self.quantity / usage if usage else None


class LogisticsHub(LocatedModel):
    """A geographic routing waypoint whose exposure can affect its shipments."""


class Shipment(DatasetModel):
    reference = models.CharField(max_length=50)
    source = models.ForeignKey(SupplierSite, on_delete=models.PROTECT, related_name="shipments")
    factory = models.ForeignKey(Factory, on_delete=models.PROTECT, related_name="shipments")
    hub = models.ForeignKey(LogisticsHub, null=True, blank=True, on_delete=models.SET_NULL)
    ship_date = models.DateField()
    estimated_arrival = models.DateField(db_index=True)
    actual_arrival = models.DateField(null=True, blank=True)
    shipping_mode = models.CharField(max_length=20)
    status = models.CharField(
        max_length=20,
        choices=[("in_transit", "In transit"), ("delayed", "Delayed"), ("delivered", "Delivered")],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["mode", "reference"], name="shipment_reference"),
            models.CheckConstraint(
                condition=Q(estimated_arrival__gte=models.F("ship_date")), name="shipment_dates"
            ),
        ]


class ShipmentLine(DatasetRelation):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="lines")
    part = models.ForeignKey(Part, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["shipment", "part"], name="shipment_part")]
