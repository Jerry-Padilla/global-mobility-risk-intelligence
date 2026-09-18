import os

import pytest

from apps.analytics.backends import DuckDBBackend, SnowflakeBackend
from apps.analytics.datasets import DATASETS


@pytest.mark.snowflake
@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(
    not os.getenv("RUN_SNOWFLAKE_TESTS"),
    reason="Explicit warehouse credentials and matching publication required",
)
def test_warehouse_contract(data_root):
    from datetime import date

    from django.core.management import call_command

    from apps.analytics.publication import publish
    from apps.analytics.snowflake_loader import publish_snowflake

    # RUN_SNOWFLAKE_TESTS explicitly authorizes publication into the configured test account.
    call_command("generate_company_data", as_of=date(2026, 9, 18), verbosity=0)
    publish("demo")
    publish_snowflake("demo")
    for dataset in DATASETS:
        local = DuckDBBackend().query(dataset, "demo")
        remote = SnowflakeBackend().query(dataset, "demo")
        assert local.version == remote.version
        assert local.rows == remote.rows
