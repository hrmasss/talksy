"""Piccolo ORM configuration."""

from app.config import settings
from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine
from piccolo.engine.sqlite import SQLiteEngine

# Database engine configuration
if settings.db_engine == "sqlite":
    DB = SQLiteEngine(path=settings.db_sqlite_path)
else:
    DB = PostgresEngine(
        config={
            "host": settings.db_host,
            "port": settings.db_port,
            "database": settings.db_name,
            "user": settings.db_user,
            "password": settings.db_password,
        }
    )

# App registry for migrations
APP_REGISTRY = AppRegistry(
    apps=[
        "app.db.piccolo_app",
        "piccolo.apps.user.piccolo_app",
        "piccolo.apps.migrations.piccolo_app",
    ]
)
