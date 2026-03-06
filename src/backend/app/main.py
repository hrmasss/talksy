"""Main Litestar application setup."""

from pathlib import Path

from app import __version__
from app.api.health import HealthController
from app.api.v1 import api_v1_router
from app.config import settings
from app.core.logging import logger, setup_logging
from litestar import Litestar, get
from litestar.config.compression import CompressionConfig
from litestar.config.cors import CORSConfig
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import RedocRenderPlugin, StoplightRenderPlugin, SwaggerRenderPlugin
from litestar.response import Redirect
from litestar.static_files import create_static_files_router


@get("/", include_in_schema=False)
async def root_redirect() -> Redirect:
    """Redirect root to API documentation."""
    return Redirect(path="/docs")


def create_app() -> Litestar:
    """Create and configure the Litestar application."""
    
    # Setup logging
    setup_logging()
    
    # CORS configuration
    cors_config = CORSConfig(
        allow_origins=["*"] if settings.is_development else ["https://talksy.app"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    
    # Compression config
    compression_config = CompressionConfig(backend="gzip", minimum_size=1000)
    
    # OpenAPI configuration with Stoplight Elements
    # The `path` sets the root for all OpenAPI endpoints
    # First render plugin is also served at the root path
    openapi_config = OpenAPIConfig(
        title="Talksy API",
        description="""
# Talksy API

AI-powered mock exam and English conversation practice platform.

## Features

- **Mock Exams**: Practice IELTS, PTE, and TOEFL exams with AI-powered feedback
- **Conversation Practice**: Natural English conversation practice with AI tutors
- **Progress Tracking**: Track your improvement over time
- **Personalized Feedback**: Get detailed analysis and suggestions

## Authentication

Most endpoints require authentication. Use the `/api/v1/users/login` endpoint to get an access token.

## Rate Limiting

API requests are rate-limited to ensure fair usage. Contact support for higher limits.
        """,
        version=__version__,
        contact={"name": "Talksy Support", "email": "support@talksy.app"},
        license={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        render_plugins=[
            StoplightRenderPlugin(),  # Served at /docs (root) and /docs/elements
            SwaggerRenderPlugin(path="/swagger"),
            RedocRenderPlugin(path="/redoc"),
        ],
        path="/docs",  # Root path for OpenAPI - JSON at /docs/openapi.json
        use_handler_docstrings=True,
    )
    
    # Logging middleware
    logging_config = LoggingMiddlewareConfig(
        request_log_fields=["method", "path", "query"],
        response_log_fields=["status_code"],
    )
    
    # Route handlers
    route_handlers = [
        root_redirect,
        HealthController,
        api_v1_router,
    ]
    
    # Static files for frontend (will be built by Vite)
    static_dir = Path(__file__).parent.parent.parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    
    # Create static file routers for user and admin UIs
    static_routers = []
    
    # User UI static files
    user_static_dir = static_dir / "user"
    if user_static_dir.exists():
        static_routers.append(
            create_static_files_router(
                path="/app",
                directories=[user_static_dir],
                html_mode=True,
            )
        )
    
    # Admin UI static files
    admin_static_dir = static_dir / "admin"
    if admin_static_dir.exists():
        static_routers.append(
            create_static_files_router(
                path="/admin",
                directories=[admin_static_dir],
                html_mode=True,
            )
        )
    
    # Create app
    app = Litestar(
        route_handlers=route_handlers + static_routers,
        cors_config=cors_config,
        compression_config=compression_config,
        openapi_config=openapi_config,
        middleware=[logging_config.middleware],
        debug=settings.debug,
        on_startup=[on_startup],
        on_shutdown=[on_shutdown],
    )
    
    return app


async def _ensure_postgres_db_exists() -> None:
    """Create the PostgreSQL database if it does not exist."""
    import asyncpg

    db_name = settings.db_name
    try:
        # Connect to the default 'postgres' maintenance database
        conn = await asyncpg.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database="postgres",
        )
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", db_name
            )
            if not exists:
                # Database names cannot be parameterised in CREATE DATABASE
                await conn.execute(f'CREATE DATABASE "{db_name}"')
                logger.info(f"Database '{db_name}' created successfully")
            else:
                logger.debug(f"Database '{db_name}' already exists")
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"Could not ensure database '{db_name}' exists: {e}")


async def on_startup() -> None:
    """Application startup handler."""
    logger.info(f"Starting Talksy v{__version__} in {settings.environment} mode")

    # Create the database if it doesn't exist (PostgreSQL only)
    if settings.db_engine == "postgres":
        await _ensure_postgres_db_exists()

    # Initialize database tables
    try:
        from piccolo.engine import engine_finder
        engine = engine_finder()
        if engine:
            await engine.start_connection_pool()
            logger.info("Database connection pool started")
    except Exception as e:
        logger.warning(f"Could not start database connection pool: {e}")


async def on_shutdown() -> None:
    """Application shutdown handler."""
    logger.info("Shutting down Talksy...")

    # Close LangGraph checkpointer connection pool
    try:
        from app.agents.common.checkpointer import close_pool
        await close_pool()
        logger.info("Agent checkpointer pool closed")
    except Exception as e:
        logger.warning(f"Error closing agent checkpointer pool: {e}")
    
    # Close database connections
    try:
        from piccolo.engine import engine_finder
        engine = engine_finder()
        if engine:
            await engine.close_connection_pool()
            logger.info("Database connection pool closed")
    except Exception as e:
        logger.warning(f"Error closing database connection pool: {e}")


# Application instance
app = create_app()
