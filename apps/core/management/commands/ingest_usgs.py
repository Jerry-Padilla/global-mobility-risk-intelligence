from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.sources import ingest_usgs


class Command(BaseCommand):
    help = "Incrementally ingest USGS earthquakes; --reconcile reloads the recent catalog"

    def add_arguments(self, parser):
        parser.add_argument("--reconcile", action="store_true")

    def handle(self, *args, **options):
        run = ingest_usgs(reconcile=options["reconcile"])
        if run.rejected:
            raise CommandError(f"Run {run.pk} rejected {run.rejected} records; inspect Data health")
        self.stdout.write(f"Run {run.pk}: {run.status}; loaded={run.loaded}, skipped={run.skipped}")
