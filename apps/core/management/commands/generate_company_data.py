import random
from datetime import date, datetime, time, timedelta, timezone

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.automotive.models import Complaint, Recall, Vehicle
from apps.automotive.services import calculate_anomalies, categorize, month_shift
from apps.environmental.models import Event
from apps.risk.services import calculate_risks
from apps.supply_chain.models import (
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

LOCATIONS = [
    ("Fremont", "United States", 37.49, -121.94),
    ("Austin", "United States", 30.27, -97.74),
    ("Phoenix", "United States", 33.45, -112.07),
    ("Detroit", "United States", 42.33, -83.05),
    ("Monterrey", "Mexico", 25.69, -100.32),
    ("Hsinchu", "Taiwan", 24.81, 120.97),
    ("Nagoya", "Japan", 35.18, 136.91),
    ("Stuttgart", "Germany", 48.78, 9.18),
]
COMMODITIES = [
    "semiconductors",
    "sensors",
    "battery cooling",
    "PCBAs",
    "harnesses",
    "motors",
    "castings",
    "fasteners",
    "machined housings",
]


class Command(BaseCommand):
    help = "Idempotently seed isolated synthetic scenarios, with a reproducible reference date"

    def add_arguments(self, parser):
        parser.add_argument("--as-of", type=date.fromisoformat, default=date(2026, 9, 18))
        parser.add_argument("--seed", type=int, default=42)

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        as_of = options["as_of"]
        factories, sites = [], []
        for i, (city, country, lat, lon) in enumerate(LOCATIONS):
            factory, _ = Factory.objects.update_or_create(
                mode="demo",
                code=f"F{i + 1:02}",
                defaults={
                    "name": f"{city} Manufacturing",
                    "city": city,
                    "country": country,
                    "latitude": lat,
                    "longitude": lon,
                    "production_capacity": 120000 + i * 20000,
                    "utilization": round(rng.uniform(0.68, 0.96), 2),
                    "criticality": 5 if i == 0 else 3,
                    "product_family": "Electric mobility",
                },
            )
            factories.append(factory)
        for i in range(40):
            city, country, lat, lon = LOCATIONS[5 if i == 0 else i % 8]
            supplier, _ = Supplier.objects.update_or_create(
                mode="demo",
                code=f"S{i + 1:03}",
                defaults={
                    "name": "Taiwan Precision Semiconductors"
                    if i == 0
                    else f"{city} {['Motion', 'Electronics', 'Materials', 'Systems', 'Components'][i // 8]} {i + 1:02}",
                    "tier": 1 if i < 24 else 2,
                    "annual_spend": rng.randint(1, 24) * 1000000,
                    "criticality": 5 if i == 0 else rng.randint(2, 5),
                    "reliability": round(rng.uniform(0.84, 0.99), 2),
                },
            )
            site, _ = SupplierSite.objects.update_or_create(
                supplier=supplier,
                name=f"{city} production site",
                defaults={
                    "mode": "demo",
                    "city": city,
                    "country": country,
                    "latitude": lat + rng.uniform(-0.3, 0.3),
                    "longitude": lon + rng.uniform(-0.3, 0.3),
                },
            )
            sites.append(site)
        hub, _ = LogisticsHub.objects.update_or_create(
            mode="demo",
            name="Gulf logistics gateway",
            defaults={
                "city": "Houston",
                "country": "United States",
                "latitude": 29.76,
                "longitude": -95.37,
            },
        )
        for i in range(120):
            part, _ = Part.objects.update_or_create(
                mode="demo",
                number=f"GM-{10000 + i}",
                defaults={
                    "description": "Steering control semiconductor"
                    if i == 0
                    else f"{COMMODITIES[i % 9].title()} assembly {i + 1:03}",
                    "commodity": COMMODITIES[i % 9],
                    "unit_cost": rng.randint(5, 800),
                    "safety_stock_days": 14,
                    "criticality": 5 if i == 0 else rng.randint(2, 5),
                },
            )
            site = sites[i % 40]
            Sourcing.objects.update_or_create(
                part=part,
                site=site,
                defaults={
                    "lead_time_days": 45 if i == 0 else rng.randint(10, 60),
                    "qualification": "approved",
                    "is_primary": True,
                },
            )
            if i % 3 and i != 0:
                Sourcing.objects.update_or_create(
                    part=part,
                    site=sites[(i + 7) % 40],
                    defaults={
                        "lead_time_days": 28,
                        "qualification": "approved",
                        "is_primary": False,
                        "cost_delta_pct": 8,
                    },
                )
            req, _ = Requirement.objects.update_or_create(
                factory=factories[i % 8], part=part, defaults={"daily_usage": 100 + (i % 6) * 40}
            )
            coverage = 3.8 if i == 0 else 4.8 if i == 5 else rng.uniform(5, 40)
            for offset in range(14):
                InventorySnapshot.objects.update_or_create(
                    requirement=req,
                    date=as_of - timedelta(days=offset),
                    defaults={
                        "quantity": req.daily_usage * (coverage + offset * 0.25),
                        "safety_stock": req.daily_usage * 14,
                    },
                )
            shipment, _ = Shipment.objects.update_or_create(
                mode="demo",
                reference=f"SHP-{i + 1:05}",
                defaults={
                    "source": site,
                    "factory": req.factory,
                    "hub": hub if i % 5 == 0 and i != 0 else None,
                    "ship_date": as_of - timedelta(days=5),
                    "estimated_arrival": as_of + timedelta(days=7 if i == 0 else 2),
                    "shipping_mode": "Ocean" if i % 2 else "Air",
                    "status": "delayed" if i % 5 == 0 and i != 0 else "in_transit",
                },
            )
            ShipmentLine.objects.update_or_create(
                shipment=shipment, part=part, defaults={"quantity": 1200}
            )
        instant = datetime.combine(as_of, time(6), tzinfo=timezone.utc)
        Event.objects.update_or_create(
            mode="demo",
            source="simulation",
            source_id="scenario-earthquake",
            defaults={
                "kind": "earthquake",
                "title": "M6.2 earthquake near Hsinchu · simulated",
                "occurred_at": instant - timedelta(days=1),
                "expires_at": instant + timedelta(days=7),
                "latitude": sites[0].latitude + 0.1,
                "longitude": sites[0].longitude + 0.1,
                "magnitude": 6.2,
                "depth_km": 12,
                "severity": 0.88,
            },
        )
        Event.objects.update_or_create(
            mode="demo",
            source="simulation",
            source_id="scenario-weather",
            defaults={
                "kind": "weather",
                "title": "Extreme wind at Gulf logistics gateway · simulated",
                "occurred_at": instant - timedelta(hours=12),
                "expires_at": instant + timedelta(days=2),
                "latitude": hub.latitude,
                "longitude": hub.longitude,
                "severity": 0.95,
            },
        )
        vehicle, _ = Vehicle.objects.update_or_create(
            mode="demo",
            make="Aster",
            model="E4",
            year=2024,
            defaults={"coverage_start": month_shift(as_of, -14)},
        )
        # Replace only this synthetic vehicle's complaints to support changing reference dates.
        Complaint.objects.filter(vehicle=vehicle).delete()
        categories, evidence = categorize(
            "Intermittent steering assist loss and electrical warning."
        )
        rows = []
        for offset in range(1, 15):
            month = month_shift(as_of, -offset)
            for j in range(104 if offset == 1 else 35):
                rows.append(
                    Complaint(
                        mode="demo",
                        source_id=f"DEMO-{offset}-{j}",
                        vehicle=vehicle,
                        filed_on=month + timedelta(days=j % 27),
                        component="STEERING",
                        narrative="Intermittent steering assist loss and electrical warning. Synthetic investigation scenario.",
                        crash=j % 29 == 0,
                        injuries=int(j % 53 == 0),
                        categories=categories,
                        evidence=evidence,
                    )
                )
        Complaint.objects.bulk_create(rows)
        recall, _ = Recall.objects.update_or_create(
            mode="demo",
            campaign="DEMO-26-001",
            defaults={
                "reported_on": as_of - timedelta(days=40),
                "component": "STEERING",
                "summary": "Synthetic steering controller inspection campaign",
                "consequence": "Intermittent loss of steering assistance",
                "remedy": "Inspect and update controller software",
            },
        )
        recall.vehicles.add(vehicle)
        for offset in range(13, -1, -1):
            calculate_risks("demo", as_of - timedelta(days=offset))
        calculate_anomalies("demo", as_of)
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo ready as of {as_of}: 8 factories, 40 suppliers, 120 parts; all scenarios explicitly synthetic."
            )
        )
