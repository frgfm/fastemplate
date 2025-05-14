# Copyright (C) 2025, François-Guillaume Fernandez.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from typing import Any

from pydantic import BaseModel, EmailStr, Field
from pydantic_core import PydanticUndefined

from app.models import User, UserRole

__all__ = ["CallbackJWT", "HashedPassword", "JWTPayload", "UserPicture"]


def col_metadata_(col_name: str) -> dict[str, Any]:
    """Extract column metadata (description, validators, type, default) from a DB table."""
    schema = User.model_json_schema()

    return {
        "description": schema["properties"][col_name].get("description", ""),
        "default": schema["properties"][col_name].get("default", ...),
        "gt": schema["properties"][col_name].get("exclusiveMinimum", PydanticUndefined),
        "ge": schema["properties"][col_name].get("minimum", PydanticUndefined),
        "lt": schema["properties"][col_name].get("exclusiveMaximum", PydanticUndefined),
        "le": schema["properties"][col_name].get("maximum", PydanticUndefined),
        "min_length": schema["properties"][col_name].get("minLength", PydanticUndefined),
        "max_length": schema["properties"][col_name].get("maxLength", PydanticUndefined),
        "examples": schema["properties"][col_name].get("examples", PydanticUndefined),
    }


class CallbackJWT(BaseModel):
    # https://datatracker.ietf.org/doc/html/rfc7519#section-4.1
    sub: int = Field(..., gt=0)
    exp: int = Field(..., gt=0)


class JWTPayload(CallbackJWT):
    scope: UserRole


class HashedPassword(BaseModel):
    hashed_password: str = Field(**col_metadata_("hashed_password"))


class UserPicture(BaseModel):
    picture_bkey: str = Field(**col_metadata_("picture_bkey"))


class UserPayload(BaseModel):
    id: int = Field(**col_metadata_("id"))
    email: EmailStr = Field(**col_metadata_("email"))
    role: UserRole = Field(**col_metadata_("role"))
    picture_url: str | None = Field(..., description="URL of the user's profile picture")
