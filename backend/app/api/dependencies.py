# Copyright (C) 2025, François-Guillaume Fernandez.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jwt import DecodeError, ExpiredSignatureError, InvalidSignatureError
from jwt import decode as jwt_decode
from jwt import encode as jwt_encode
from pydantic import ValidationError

from app.core.config import settings
from app.schemas import JWTPayload

__all__ = ["create_jwt_token", "decode_token", "get_jwt"]

# Scope definition
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/creds",
)


def decode_token(token: str, authenticate_value: Union[str, None] = None) -> Dict[str, str]:
    try:
        payload = jwt_decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM], options={"verify_aud": False}
        )
    except (ExpiredSignatureError, InvalidSignatureError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": authenticate_value} if authenticate_value else None,
        )
    except DecodeError:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Invalid token.",
            headers={"WWW-Authenticate": authenticate_value} if authenticate_value else None,
        )
    return payload


def create_jwt_token(content: Dict[str, Any], expires_minutes: int = settings.JWT_EXPIRE_MINUTES) -> str:
    """Encode content dict using security algorithm, setting expiration."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    return jwt_encode({**content, "exp": expire}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def get_jwt(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
) -> JWTPayload:
    authenticate_value = f'Bearer scope="{security_scopes.scope_str}"' if security_scopes.scopes else "Bearer"
    payload = decode_token(token)
    try:
        jwt_payload = JWTPayload(**payload)
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": authenticate_value} if authenticate_value else None,
        )
    # Retrieve the actual role
    if jwt_payload.scope not in security_scopes.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incompatible token scope.",
            headers={"WWW-Authenticate": authenticate_value},
        )
    return jwt_payload
