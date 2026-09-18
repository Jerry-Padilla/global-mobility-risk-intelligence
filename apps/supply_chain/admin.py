from django.contrib import admin

from .models import (
    Factory,
    InventorySnapshot,
    LogisticsHub,
    Part,
    Requirement,
    Shipment,
    ShipmentLine,
    Sourcing,
    Supplier,
    SupplierSite,
)

for model in (
    Factory,
    Supplier,
    SupplierSite,
    Part,
    Sourcing,
    Requirement,
    InventorySnapshot,
    Shipment,
    ShipmentLine,
    LogisticsHub,
):
    admin.site.register(model)
