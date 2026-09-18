import os
from datetime import date

os.environ["DJANGO_DEBUG"] = "true"
os.environ["SECURE_SSL_REDIRECT"] = "false"

import pytest
from django.core.management import call_command


@pytest.fixture(autouse=True)
def test_static_storage(settings):
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


@pytest.fixture(scope="session")
def demo(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("generate_company_data", as_of=date(2026, 9, 18), verbosity=0)


@pytest.fixture
def data_root(settings, tmp_path):
    settings.DATA_ROOT = tmp_path
    return tmp_path
