from django.db import models

from apps.core.models import DatasetModel, DatasetRelation


class CalculationRun(DatasetModel):
    as_of = models.DateTimeField(db_index=True)
    model_version = models.CharField(max_length=30, default="weighted-v1")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["mode", "as_of", "model_version"], name="risk_run_version"
            )
        ]


class Assessment(DatasetRelation):
    run = models.ForeignKey(CalculationRun, on_delete=models.CASCADE, related_name="assessments")
    requirement = models.ForeignKey(
        "supply_chain.Requirement", on_delete=models.CASCADE, related_name="assessments"
    )
    source = models.ForeignKey(
        "supply_chain.Sourcing", on_delete=models.CASCADE, related_name="assessments"
    )
    event = models.ForeignKey(
        "environmental.Event", on_delete=models.SET_NULL, null=True, blank=True
    )
    score = models.FloatField(null=True, db_index=True)
    classification = models.CharField(max_length=15)
    days_of_supply = models.FloatField(null=True)
    distance_km = models.FloatField(null=True)
    factors = models.JSONField(default=dict)
    stockout_on = models.DateField(null=True)
    explanation = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["run", "requirement", "source"], name="assessment_dependency"
            )
        ]
