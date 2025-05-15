# Copyright (C) 2025, François-Guillaume Fernandez.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from fastapi import APIRouter

from app.api.api_v1.routers import login, users

api_router = APIRouter(redirect_slashes=True)
api_router.include_router(login.router, prefix="/login", tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
