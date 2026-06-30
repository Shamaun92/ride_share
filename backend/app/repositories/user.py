"""User data access."""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_identifier(self, identifier: str) -> User | None:
        """Look up by email OR phone (used for flexible login)."""
        result = await self.session.execute(
            select(User).where(
                or_(User.email == identifier, User.phone == identifier)
            )
        )
        return result.scalar_one_or_none()

    async def exists(self, email: str, phone: str) -> bool:
        result = await self.session.execute(
            select(User.id).where(
                or_(User.email == email, User.phone == phone)
            )
        )
        return result.first() is not None
