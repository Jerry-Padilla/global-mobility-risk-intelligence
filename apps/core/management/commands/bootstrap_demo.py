from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.analytics.publication import publish
from apps.ingestion.pipeline import job_lock
from apps.supply_chain.models import Factory


class Command(BaseCommand):
    help = "Prepare a single-instance hosted demo; regenerate disposable analytics from PostgreSQL"

    def handle(self, *args, **options):
        if settings.ANALYTICS_BACKEND != "duckdb":
            raise CommandError("Hosted demo bootstrap requires ANALYTICS_BACKEND=duckdb")
        with job_lock("hosted-demo-bootstrap"):
            if not Factory.objects.filter(mode="demo").exists():
                call_command("generate_company_data")
            publication = publish("demo")
        self.stdout.write(self.style.SUCCESS(f"Demo publication ready: {publication.version}"))
