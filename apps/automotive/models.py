from django.db import models

from apps.core.models import DatasetModel


class Vehicle(DatasetModel):
    make = models.CharField(max_length=80)
    model = models.CharField(max_length=100)
    year = models.PositiveSmallIntegerField()
    coverage_start = models.DateField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["mode", "make", "model", "year"], name="vehicle_identity"
            )
        ]

    def __str__(self):
        return f"{self.year} {self.make} {self.model}"


class Complaint(DatasetModel):
    source_id = models.CharField(max_length=80)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="complaints")
    filed_on = models.DateField(db_index=True)
    incident_on = models.DateField(null=True, blank=True)
    component = models.CharField(max_length=160, db_index=True)
    narrative = models.TextField(blank=True)
    crash = models.BooleanField(default=False)
    fire = models.BooleanField(default=False)
    injuries = models.PositiveIntegerField(default=0)
    categories = models.JSONField(default=list)
    evidence = models.JSONField(default=dict)
    payload_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["mode", "source_id"], name="complaint_source")
        ]


class Recall(DatasetModel):
    campaign = models.CharField(max_length=80)
    vehicles = models.ManyToManyField(Vehicle, related_name="recalls")
    reported_on = models.DateField(db_index=True)
    component = models.CharField(max_length=160)
    summary = models.TextField()
    consequence = models.TextField(blank=True)
    remedy = models.TextField(blank=True)
    payload_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["mode", "campaign"], name="recall_campaign")]


class Anomaly(DatasetModel):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="anomalies")
    component = models.CharField(max_length=160)
    month = models.DateField()
    observed = models.PositiveIntegerField()
    expected = models.FloatField()
    threshold = models.FloatField()
    increase_pct = models.FloatField(null=True)
    severity = models.CharField(max_length=15)
    model_version = models.CharField(max_length=20, default="rolling-v1")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["vehicle", "component", "month"], name="anomaly_period")
        ]
