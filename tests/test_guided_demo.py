from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.analytics.backends import DuckDBBackend
from apps.risk.services import latest_assessments
from config.database import database_config


@pytest.mark.django_db
def test_guided_investigation_and_isolation(client, demo):
    risk = latest_assessments("demo").get(
        source__site__supplier__code="S001", requirement__part__number="GM-10000"
    )
    response = client.get(f"/investigations/{risk.pk}/")
    assert response.status_code == 200
    assert b"Complete qualification before use" in response.content
    assert b"Available supplier inventory is unknown" in response.content
    assert risk.requirement.factory.name.encode() in response.content
    assert client.get(f"/investigations/{risk.pk}/?mode=live").status_code == 404
    assert client.post(f"/investigations/{risk.pk}/").status_code == 405
    assert f"/investigations/{risk.pk}/".encode() in client.get("/").content


def test_hosted_database_configuration():
    config = database_config("postgresql://demo:p%40ss@db.example/test?sslmode=require")
    assert config["PASSWORD"] == "p@ss"
    assert config["OPTIONS"]["sslmode"] == "require"
    assert config["CONN_MAX_AGE"] == 0
    with pytest.raises(ValueError):
        database_config("sqlite:///test.db")


@pytest.mark.django_db(transaction=True)
def test_bootstrap_recovers_missing_files(demo, data_root):
    import shutil

    call_command("bootstrap_demo")
    shutil.rmtree(data_root / "publications")
    with patch("apps.core.management.commands.bootstrap_demo.call_command") as seed:
        call_command("bootstrap_demo")
        seed.assert_not_called()
    assert (data_root / "publications").exists()
    assert DuckDBBackend().query("supplier_risk_summary", "demo").rows
