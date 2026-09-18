"""Parse hosted PostgreSQL URLs without logging credentials."""

from urllib.parse import parse_qs, unquote, urlsplit


def database_config(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or not parsed.hostname
        or not parsed.path.strip("/")
    ):
        raise ValueError("DATABASE_URL must identify a PostgreSQL host and database")
    options = {"connect_timeout": 10, "sslmode": "require"}
    for name, values in parse_qs(parsed.query).items():
        if name in {"sslmode", "channel_binding"}:
            options[name] = values[-1]
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname,
        "PORT": parsed.port or 5432,
        "CONN_MAX_AGE": 0,
        "OPTIONS": options,
    }
