# Copyright (C) 2025, François-Guillaume Fernandez.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from datetime import datetime
from enum import Enum

from pydantic import EmailStr
from sqlmodel import Field, SQLModel, String

__all__ = ["User", "UserRole"]


class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    MEMBER = "member"


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: int | None = Field(None, primary_key=True)
    # Auth-related
    email: EmailStr = Field(..., sa_type=String(), unique=True, index=True, nullable=False)  # type: ignore[call-overload]
    hashed_password: str = Field(..., nullable=False, min_length=4, max_length=60)
    role: UserRole = Field(UserRole.MEMBER, nullable=False)
    # Others
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    picture_bkey: str | None = Field(None, min_length=1, description="S3 bucket key of the user's profile picture")
