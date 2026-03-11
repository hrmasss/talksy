"""Script to create database tables."""

import asyncio

from app.db.bootstrap import TABLES, ensure_tables_exist


async def create_tables():
    """Create all database tables."""
    await ensure_tables_exist()

    for table in TABLES:
        print(f"Created table: {table._meta.tablename}")

    print("\nAll tables created successfully!")


if __name__ == "__main__":
    asyncio.run(create_tables())
