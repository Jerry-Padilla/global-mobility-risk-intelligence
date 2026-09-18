from django.db import models
from django.db.models import Q

from apps.core.models import DatasetModel


class Event(DatasetModel):
    source = models.CharField(max_length=30)
    source_id = models.CharField(max_length=150)
    kind = models.CharField(
        max_length=20, choices=[("earthquake", "Earthquake"), ("weather", "Severe weather")]
    )
    title = models.CharField(max_length=250)
    occurred_at = models.DateTimeField(db_index=True)
    expires_at = models.DateTimeField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    magnitude = models.FloatField(null=True, blank=True)
    depth_km = models.FloatField(null=True, blank=True)
    severity = models.FloatField()
    source_updated_at = models.DateTimeField(null=True, blank=True)
    payload_hash = models.CharField(max_length=64, blank=True)
    url = models.URLField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["mode", "source", "source_id"], name="event_source_id"),
            models.CheckConstraint(
                condition=Q(
                    latitude__gte=-90, latitude__lte=90, longitude__gte=-180, longitude__lte=180
                ),
                name="event_coordinates",
            ),
            models.CheckConstraint(
                condition=Q(severity__gte=0, severity__lte=1), name="event_severity"
            ),
            models.CheckConstraint(
                condition=Q(magnitude__isnull=True) | Q(magnitude__gte=0, magnitude__lte=10),
                name="event_magnitude",
            ),
        ]


class WeatherReading(DatasetModel):
    location_key = models.CharField(max_length=80)
    latitude = models.FloatField()
    longitude = models.FloatField()
    valid_at = models.DateTimeField()
    issued_at = models.DateTimeField()
    temperature_c = models.FloatField(null=True)
    precipitation_mm = models.FloatField(null=True)
    wind_kmh = models.FloatField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["mode", "location_key", "valid_at", "issued_at"], name="weather_reading"
            )
        ]
