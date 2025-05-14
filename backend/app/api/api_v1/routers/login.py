# Copyright (C) 2025, François-Guillaume Fernandez.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from typing import cast

from fastapi import APIRouter, Depends, Form, HTTPException, Security, status
from pydantic import BaseModel, EmailStr, Field, SecretStr

from app.api.dependencies import create_jwt_token, decode_token, get_jwt
from app.core.config import settings
from app.core.security import verify_password
from app.crud import UserCRUD, get_user_crud
from app.models import User, UserRole
from app.schemas import CallbackJWT, JWTPayload

router = APIRouter()


class Token(BaseModel):
    access_token: str = Field(
        ..., examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.423fgFGTfttrvU6D1k7vF92hH5vaJHCGFYd8E"]
    )
    token_type: str = Field(..., examples=["bearer"])


def _create_token(user: User) -> Token:
    token_data = {"sub": str(user.id), "scope": user.role}
    token = create_jwt_token(token_data, settings.JWT_UNLIMITED)
    return Token(access_token=token, token_type="bearer")  # noqa: S106


@router.post("/creds", status_code=status.HTTP_200_OK, summary="Request an access token using credentials")
async def login_with_creds(
    username: EmailStr = Form(..., description="Email address of the user."),
    password: SecretStr = Form(..., description="Password of the user."),
    users: UserCRUD = Depends(get_user_crud),
) -> Token:
    # Verify credentials
    user = cast(User, await users.get_by("email", username, strict=True))
    if user.hashed_password is None or not verify_password(password.get_secret_value(), user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    # create access token using user user_id/user_scopes
    return _create_token(user)


@router.get("/code", status_code=status.HTTP_200_OK, summary="Request an access token using a code")
async def request_token_from_code(
    code: str,
    users: UserCRUD = Depends(get_user_crud),
) -> Token:
    # Verify credentials
    token_payload = CallbackJWT(**decode_token(code))
    user = cast(User, await users.get(token_payload.sub, strict=True))
    return _create_token(user)


@router.get("/validate", status_code=status.HTTP_200_OK, summary="Check token validity")
def check_token_validity(
    _: JWTPayload = Security(get_jwt, scopes=[UserRole.SUPERADMIN, UserRole.MEMBER]),
) -> None:
    return None
