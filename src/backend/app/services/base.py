"""Base service class."""

from typing import Any, Generic, TypeVar
from uuid import UUID

from piccolo.table import Table

from app.core.logging import logger

T = TypeVar("T", bound=Table)


class BaseService(Generic[T]):
    """Base service class with common CRUD operations."""

    model: type[T]

    async def get_by_id(self, id: UUID) -> T | None:
        """Get a record by ID."""
        try:
            result = await self.model.select().where(self.model.id == id).first()
            return result
        except Exception as e:
            logger.error(f"Error fetching {self.model.__name__} by ID {id}: {e}")
            return None

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[T]:
        """Get all records with pagination and optional filters."""
        try:
            query = self.model.select()
            
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key) and value is not None:
                        query = query.where(getattr(self.model, key) == value)
            
            results = await query.offset(offset).limit(limit)
            return results
        except Exception as e:
            logger.error(f"Error fetching all {self.model.__name__}: {e}")
            return []

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count records with optional filters."""
        try:
            query = self.model.count()
            
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key) and value is not None:
                        query = query.where(getattr(self.model, key) == value)
            
            return await query
        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            return 0

    async def create(self, data: dict[str, Any]) -> T:
        """Create a new record."""
        try:
            instance = self.model(**data)
            await instance.save()
            logger.info(f"Created {self.model.__name__} with ID {instance.id}")
            return instance
        except Exception as e:
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise

    async def update(self, id: UUID, data: dict[str, Any]) -> T | None:
        """Update a record by ID."""
        try:
            # Remove None values
            update_data = {k: v for k, v in data.items() if v is not None}
            
            if not update_data:
                return await self.get_by_id(id)
            
            await self.model.update(update_data).where(self.model.id == id)
            logger.info(f"Updated {self.model.__name__} with ID {id}")
            return await self.get_by_id(id)
        except Exception as e:
            logger.error(f"Error updating {self.model.__name__} {id}: {e}")
            raise

    async def delete(self, id: UUID) -> bool:
        """Delete a record by ID."""
        try:
            await self.model.delete().where(self.model.id == id)
            logger.info(f"Deleted {self.model.__name__} with ID {id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting {self.model.__name__} {id}: {e}")
            return False

    async def exists(self, id: UUID) -> bool:
        """Check if a record exists."""
        result = await self.model.exists().where(self.model.id == id)
        return result
