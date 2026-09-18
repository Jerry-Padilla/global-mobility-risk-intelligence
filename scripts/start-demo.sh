#!/bin/sh
set -eu
python manage.py migrate --noinput
python manage.py bootstrap_demo
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 1 --threads 2 --timeout 90 --access-logfile -
