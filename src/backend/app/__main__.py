"""Entry point for running the application."""

import sys
from pathlib import Path

# Add src/backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_server() -> None:
    """Run the server using Granian."""
    from app.config import settings
    
    try:
        from granian import Granian
        from granian.constants import Interfaces
        
        server = Granian(
            target="app.main:app",
            address=settings.host,
            port=settings.port,
            interface=Interfaces.ASGI,
            workers=1 if settings.is_development else 4,
            reload=settings.reload and settings.is_development,
        )
        server.serve()
    except ImportError:
        # Fallback to uvicorn if granian not available
        import uvicorn
        
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.reload and settings.is_development,
        )


def run_cli() -> None:
    """Run the CLI interface."""
    import click
    
    @click.group()
    def cli():
        """Talksy CLI"""
        pass
    
    @cli.command()
    def serve():
        """Run the development server."""
        run_server()
    
    @cli.command()
    def migrate():
        """Run database migrations."""
        import asyncio
        from piccolo.apps.migrations.commands.forwards import run_forwards
        
        async def _migrate():
            await run_forwards(app_name="talksy")
        
        asyncio.run(_migrate())
        click.echo("Migrations completed!")
    
    @cli.command()
    def makemigrations():
        """Create new migrations."""
        import asyncio
        from piccolo.apps.migrations.commands.new import new
        
        async def _makemigrations():
            await new(app_name="talksy", auto=True)
        
        asyncio.run(_makemigrations())
        click.echo("Migration created!")
    
    @cli.command()
    def shell():
        """Open interactive Python shell."""
        import code
        from app.db import User, Exam, ExamAttempt, ConversationSession
        
        banner = "Talksy Interactive Shell\nAvailable: User, Exam, ExamAttempt, ConversationSession"
        code.interact(banner=banner, local=locals())
    
    cli()


if __name__ == "__main__":
    run_server()
