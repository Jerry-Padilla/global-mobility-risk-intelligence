from django.core.management.base import BaseCommand

from apps.analytics.snowflake_loader import publish_snowflake, upload_raw
from apps.ingestion.pipeline import job_lock


class Command(BaseCommand):
    help = "Explicitly upload the current publication to optional Snowflake (may consume trial credits)"

    def add_arguments(self, parser):
        parser.add_argument("--mode", choices=["demo", "live"], default="demo")
        parser.add_argument("--include-raw", action="store_true")

    def handle(self, *args, **options):
        with job_lock(f"snowflake:{options['mode']}"):
            if options["include_raw"]:
                self.stdout.write(f"Raw envelopes uploaded: {upload_raw(options['mode'])}")
            self.stdout.write(f"Warehouse publication: {publish_snowflake(options['mode'])}")
