.PHONY: setup seed ingest test lint run publish
setup:
	python -m pip install -r requirements.lock
	npm ci
	npm run build
	python manage.py migrate
seed:
	python manage.py generate_company_data
	python manage.py publish_analytics --mode demo
ingest:
	python manage.py ingest_usgs
	python manage.py ingest_nhtsa
publish:
	python manage.py calculate_risk --mode live
	python manage.py publish_analytics --mode live
test:
	python -m pytest
lint:
	python -m ruff check .
	python -m ruff format --check .
run:
	python manage.py runserver
