from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.sources import ingest_weather


class Command(BaseCommand):
    help = "Ingest weather for configured live company sites and logistics hubs"

    def handle(self, *args, **options):
        run = ingest_weather()
        if run.rejected:
            raise CommandError(f"Rejected {run.rejected} records; inspect Data health")
        self.stdout.write(f"Run {run.pk}: {run.status}; loaded={run.loaded}")
