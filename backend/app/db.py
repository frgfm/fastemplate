# Copyright (C) 2025, François-Guillaume Fernandez.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import asyncio
import logging
import sys

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, select, text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models import User, UserRole

__all__ = ["get_session", "init_db"]


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.Formatter("%(levelname)s:     %(message)s")
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)

engine = create_async_engine(settings.POSTGRES_URL, echo=False)


async def get_next_id(session: AsyncSession, table_name: str) -> int:
    result = await session.exec(text(f"SELECT nextval('{table_name}_id_seq')"))  # type: ignore[call-overload]
    return result.scalar()


async def get_session() -> AsyncSession:  # type: ignore[misc]
    async with AsyncSession(engine) as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine) as session:
        logger.info("Checking PostgreSQL database state...")
        # Check if the table needs initialization
        statement = select(User).limit(1)  # type: ignore[var-annotated]
        results = await session.exec(statement=statement)
        user = results.first()
        if not user:
            logger.info("Initializing PostgreSQL database...")
            logger.info("Creating superadmin user...")
            session.add(
                User(
                    email=settings.SUPERADMIN_EMAIL,
                    hashed_password=hash_password(settings.SUPERADMIN_PWD),
                    role=UserRole.SUPERADMIN,
                )
            )
        elif user.email != settings.SUPERADMIN_EMAIL:
            logger.error("Incorrect initialization of user table")
            raise RuntimeError("DB was initialized with wrong superadmin email")
        else:
            logger.info("Recovering existing PostgreSQL database...")
        await session.commit()


async def main() -> None:
    await init_db()


if __name__ == "__main__":
    asyncio.run(main())
