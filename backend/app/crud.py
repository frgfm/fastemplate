# Copyright (C) 2025, François-Guillaume Fernandez.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import logging
from typing import Any, Generic, List, Tuple, Type, TypeVar, Union, cast

from asyncpg.exceptions import ForeignKeyViolationError, UniqueViolationError
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, delete, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar

from app.db import get_session
from app.models import User
from app.schemas import HashedPassword, UserPicture

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

logger = logging.getLogger("uvicorn.error")

__all__ = [
    "UserCRUD",
]


class BaseCRUD(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, session: AsyncSession, model: Type[ModelType]) -> None:
        self.session = session
        self.model = model

    async def create(self, payload: CreateSchemaType) -> ModelType:
        entry = self.model(**payload.model_dump())
        try:
            self.session.add(entry)
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(e)
            if str(e.orig).startswith(str(ForeignKeyViolationError)):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Unable to find foreign key reference.",
                )
            if str(e.orig).startswith(str(UniqueViolationError)):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This entry violates the unique constraint on at least one column.",
                )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create entry.",
            )
        await self.session.refresh(entry)

        return entry

    async def get(self, entry_id: int, strict: bool = False) -> Union[ModelType, None]:
        entry: Union[ModelType, None] = await self.session.get(self.model, entry_id)
        if strict and entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table {self.model.__name__} has no corresponding entry.",
            )
        return entry

    async def get_by(self, field_name: str, val: Union[str, int], strict: bool = False) -> Union[ModelType, None]:
        statement: SelectOfScalar[ModelType] = select(self.model).where(getattr(self.model, field_name) == val)
        results = await self.session.exec(statement=statement)
        entry = results.one_or_none()
        if strict and entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table {self.model.__name__} has no corresponding entry.",
            )
        return entry

    async def fetch_all(self, filter_pair: Union[Tuple[str, Any], None] = None) -> List[ModelType]:
        statement: SelectOfScalar[ModelType] = select(self.model)
        if isinstance(filter_pair, tuple):
            statement = statement.where(getattr(self.model, filter_pair[0]) == filter_pair[1])
        return await self.session.exec(statement=statement)

    async def update(self, entry_id: int, payload: UpdateSchemaType) -> ModelType:
        access = cast(ModelType, await self.get(entry_id, strict=True))
        values = payload.model_dump(exclude_unset=True)

        for k, v in values.items():
            setattr(access, k, v)

        self.session.add(access)
        await self.session.commit()
        await self.session.refresh(access)

        return access

    async def delete(self, entry_id: int) -> None:
        await self.get(entry_id, strict=True)
        statement = delete(self.model).where(self.model.id == entry_id)

        await self.session.exec(statement=statement)  # type: ignore[call-overload]
        await self.session.commit()


class UserCRUD(BaseCRUD[User, User, HashedPassword | UserPicture]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)


def get_user_crud(session: AsyncSession = Depends(get_session)) -> UserCRUD:
    return UserCRUD(session=session)
