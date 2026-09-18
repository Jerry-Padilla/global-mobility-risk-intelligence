from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class DatasetRelation(models.Model):
    """Enforce dataset boundaries during model/form validation, including admin edits."""

    class Meta:
        abstract = True

    @property
    def dataset_mode(self):
        if hasattr(self, "mode"):
            return self.mode
        for field in self._meta.fields:
            if isinstance(field, models.ForeignKey) and getattr(self, field.attname):
                related = getattr(self, field.name)
                if hasattr(related, "dataset_mode"):
                    return related.dataset_mode
        return None

    def clean(self):
        super().clean()
        modes = {self.mode} if hasattr(self, "mode") else set()
        for field in self._meta.fields:
            if isinstance(field, models.ForeignKey) and getattr(self, field.attname):
                related = getattr(self, field.name)
                value = getattr(related, "dataset_mode", None)
                if value:
                    modes.add(value)
        if len(modes) > 1:
            raise ValidationError("Related records must belong to the same dataset (demo or live).")


class DatasetModel(DatasetRelation):
    mode = models.CharField(
        max_length=4, choices=[("demo", "Demo"), ("live", "Live")], default="demo", db_index=True
    )

    class Meta:
        abstract = True


class LocatedModel(DatasetModel):
    name = models.CharField(max_length=160)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=60)
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=Q(latitude__gte=-90, latitude__lte=90), name="%(app_label)s_%(class)s_lat"
            ),
            models.CheckConstraint(
                condition=Q(longitude__gte=-180, longitude__lte=180),
                name="%(app_label)s_%(class)s_lon",
            ),
        ]

    def __str__(self):
        return self.name
