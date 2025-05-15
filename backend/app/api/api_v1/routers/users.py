# Copyright (C) 2025, François-Guillaume Fernandez.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, Security, UploadFile, status
from pydantic import EmailStr, SecretStr
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.dependencies import create_jwt_token, get_jwt
from app.core.config import settings
from app.core.security import hash_password
from app.crud import UserCRUD, get_user_crud
from app.db import get_next_id, get_session
from app.models import User, UserRole
from app.schemas import HashedPassword, JWTPayload, UserPayload, UserPicture, col_metadata_
from app.services.analytics import analytics_client
from app.services.email import email_client
from app.services.storage import storage_client

router = APIRouter()


@router.post("/invite", status_code=status.HTTP_201_CREATED, summary="Invite a new user")
async def create_user(
    email: EmailStr = Form(**col_metadata_("email")),
    role: UserRole = Form(**col_metadata_("role")),
    password: SecretStr | None = Form(None, min_length=4, max_length=60),
    send_magic_link: bool = Form(False, description="If true, the user will receive a magic link to login."),
    users: UserCRUD = Depends(get_user_crud),
    session: AsyncSession = Depends(get_session),
    _: JWTPayload = Security(get_jwt, scopes=[UserRole.SUPERADMIN]),
) -> User:
    if send_magic_link:
        # Find next ID
        user_id = await get_next_id(session, "users")
        # Create short-lived token that cannot be used for other routes (removing scope)
        code = create_jwt_token({"sub": str(user_id)}, 5)
        # Send email for invite
        magic_link = f"{settings.BACKEND_HOST}{settings.API_V1_STR}/login/code?code={code}"
        if email_client.send_link(email, magic_link).status_code != 200:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to send email")

    # Create user
    user = await users.create(
        User(
            email=email,
            role=role,
            hashed_password=hash_password(password.get_secret_value()) if password else secrets.token_urlsafe(16),
        )
    )
    # Enrich user data
    analytics_client.alias(user.id, email)
    analytics_client.capture(user.id, event="user-creation")

    return user


@router.get("/", status_code=status.HTTP_200_OK, summary="Read all users")
async def fetch_all_users(
    users: UserCRUD = Depends(get_user_crud),
    token_payload: JWTPayload = Security(get_jwt, scopes=[UserRole.SUPERADMIN]),
) -> list[UserPayload]:
    analytics_client.capture(token_payload.sub, event="user-fetch-all")
    return [
        UserPayload(
            **user.model_dump(),
            picture_url=storage_client.bucket.get_public_url(user.picture_bkey) if user.picture_bkey else None,
        )
        for user in await users.fetch_all()
    ]


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Delete the authenticated user")
async def delete_my_user(
    users: UserCRUD = Depends(get_user_crud),
    token_payload: JWTPayload = Security(get_jwt, scopes=[UserRole.SUPERADMIN, UserRole.MEMBER]),
) -> None:
    await users.delete(token_payload.sub)
    analytics_client.capture(token_payload.sub, event="user-deletion")


@router.patch("/me/password", status_code=status.HTTP_200_OK, summary="Update the authenticated user's password")
async def update_my_password(
    password: SecretStr = Form(..., description="New password for the user", min_length=4, max_length=60),
    users: UserCRUD = Depends(get_user_crud),
    token_payload: JWTPayload = Security(get_jwt, scopes=[UserRole.SUPERADMIN, UserRole.MEMBER]),
) -> None:
    await users.update(token_payload.sub, HashedPassword(hashed_password=hash_password(password.get_secret_value())))
    analytics_client.capture(token_payload.sub, event="user-password-update")


@router.patch("/me/picture", status_code=status.HTTP_200_OK, summary="Update the authenticated user's profile picture")
async def update_my_picture(
    file: UploadFile = File(..., description="Profile picture for the user"),
    users: UserCRUD = Depends(get_user_crud),
    token_payload: JWTPayload = Security(get_jwt, scopes=[UserRole.SUPERADMIN, UserRole.MEMBER]),
) -> None:
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type")
    bkey = await storage_client.upload_file(file)
    await users.update(token_payload.sub, UserPicture(picture_bkey=bkey))
    analytics_client.capture(token_payload.sub, event="user-picture-update")
