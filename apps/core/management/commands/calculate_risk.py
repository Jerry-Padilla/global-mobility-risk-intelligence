from datetime import date

from django.core.management.base import BaseCommand

from apps.automotive.services import calculate_anomalies
from apps.risk.services import calculate_risks


class Command(BaseCommand):
    help = "Calculate explainable dependency risks and completed-month anomalies"

    def add_arguments(self, parser):
        parser.add_argument("--mode", choices=["demo", "live"], default="live")
        parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())

    def handle(self, *args, **options):
        run = calculate_risks(options["mode"], options["as_of"])
        count = calculate_anomalies(options["mode"], options["as_of"])
        self.stdout.write(
            f"Run {run.id}: {run.assessments.count()} dependencies; {count} anomalies"
        )
