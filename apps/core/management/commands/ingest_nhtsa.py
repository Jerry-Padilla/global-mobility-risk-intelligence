from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.sources import ingest_nhtsa


class Command(BaseCommand):
    help = "Reconcile complaints and/or recalls for the versioned vehicle watchlist"

    def add_arguments(self, parser):
        parser.add_argument("--dataset", choices=["complaints", "recalls", "all"], default="all")

    def handle(self, *args, **options):
        for dataset in (
            ["complaints", "recalls"] if options["dataset"] == "all" else [options["dataset"]]
        ):
            run = ingest_nhtsa(dataset)
            if run.rejected:
                raise CommandError(
                    f"Run {run.pk} rejected {run.rejected} records; inspect Data health"
                )
            self.stdout.write(
                f"{dataset}: {run.status}; loaded={run.loaded}, skipped={run.skipped}"
            )
