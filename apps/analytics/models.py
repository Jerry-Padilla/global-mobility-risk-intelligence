from django.db import models

from apps.core.models import DatasetModel


class Publication(DatasetModel):
    version = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    manifest = models.JSONField()
