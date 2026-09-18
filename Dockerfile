FROM node:22-bookworm-slim AS assets
WORKDIR /build
COPY package*.json ./
RUN npm ci
COPY scripts/build-assets.mjs scripts/build-assets.mjs
COPY static static
COPY assets assets
COPY templates templates
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-runtime.lock ./
RUN pip install --no-cache-dir -r requirements-runtime.lock
COPY . .
COPY --from=assets /build/static/vendor static/vendor
COPY --from=assets /build/static/build static/build
RUN DJANGO_DEBUG=true python manage.py collectstatic --noinput \
    && useradd --create-home app && mkdir -p /app/data/runtime && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--access-logfile", "-"]
