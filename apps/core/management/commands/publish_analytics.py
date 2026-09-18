from django.core.management.base import BaseCommand

from apps.analytics.publication import publish


class Command(BaseCommand):
    help = "Atomically publish Silver/Gold Parquet and the read-only DuckDB catalog"

    def add_arguments(self, parser):
        parser.add_argument("--mode", choices=["demo", "live"], default="demo")

    def handle(self, *args, **options):
        publication = publish(options["mode"])
        self.stdout.write(
            f"Published {publication.version}: {len(publication.manifest['datasets'])} Gold datasets"
        )
