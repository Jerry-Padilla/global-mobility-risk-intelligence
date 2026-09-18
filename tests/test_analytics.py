from unittest.mock import patch

import pytest

from apps.analytics.backends import DuckDBBackend
from apps.analytics.datasets import DATASETS
from apps.analytics.models import Publication
from apps.analytics.publication import publish

pytestmark = pytest.mark.django_db(transaction=True)


def test_empty_publication_and_contract(data_root):
    publication = publish("live")
    backend = DuckDBBackend()
    for dataset in DATASETS:
        result = backend.query(dataset, "live")
        assert result.rows == []
        assert result.version == publication.version
    with pytest.raises(ValueError):
        backend.query("DROP TABLE", "live")


def test_failed_publication_keeps_last_good(data_root):
    first = publish("live")
    with patch("apps.analytics.publication.pq.write_table", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            publish("live")
    assert Publication.objects.count() == 1
    assert DuckDBBackend().query("supplier_risk_summary", "live").version == first.version


def test_seeded_publication_grains(data_root):
    from datetime import date

    from django.core.management import call_command

    call_command("generate_company_data", as_of=date(2026, 9, 18), verbosity=0)
    publish("demo")
    rows = DuckDBBackend().query("supplier_risk_summary", "demo", limit=10000).rows
    keys = [(row["date"], row["supplier_id"], row["model_version"]) for row in rows]
    assert len(keys) == len(set(keys)) == 40 * 14
    assert max(row["score"] for row in rows) >= 75
    assert DuckDBBackend().query("automotive_anomalies", "demo").rows[0]["observed"] == 104
