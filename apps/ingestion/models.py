from django.db import models

from apps.core.models import DatasetModel


class SourceState(DatasetModel):
    source = models.CharField(max_length=100)
    watermark = models.DateTimeField(null=True)
    last_success = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["mode", "source"], name="source_state")]


class IngestionRun(DatasetModel):
    source = models.CharField(max_length=100)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
    status = models.CharField(max_length=20, default="running")
    loaded = models.PositiveIntegerField(default=0)
    rejected = models.PositiveIntegerField(default=0)
    skipped = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)


class RawRecord(models.Model):
    run = models.ForeignKey(IngestionRun, on_delete=models.CASCADE, related_name="raw_records")
    source_id = models.CharField(max_length=180)
    retrieved_at = models.DateTimeField(auto_now_add=True)
    request = models.JSONField(default=dict)
    payload_hash = models.CharField(max_length=64)
    path = models.TextField()


class QualityIssue(models.Model):
    run = models.ForeignKey(IngestionRun, on_delete=models.CASCADE, related_name="issues")
    source_id = models.CharField(max_length=180)
    reason = models.TextField()
