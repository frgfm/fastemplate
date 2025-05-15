import asyncio
import os
from io import BytesIO
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.db import engine
from app.main import app

# Load environment variables FIRST to get DB connection details
load_dotenv(".env")


# --- Async PostgreSQL Connection Setup ---
# Get the URL from environment
DATABASE_URL = os.environ.get("POSTGRES_URL")
if not DATABASE_URL:
    raise ValueError("POSTGRES_URL environment variable not set")

# Ensure it uses the asyncpg driver
if "+asyncpg" not in DATABASE_URL:
    raise ValueError("POSTGRES_URL must use the asyncpg driver")


@pytest.fixture(scope="session")
def event_loop(request) -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        app=app, base_url=f"http://localhost:5050{settings.API_V1_STR}", follow_redirects=True, timeout=5
    ) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def async_session() -> AsyncSession:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        yield session
        await session.rollback()


# --- Test Function (needs to be async) ---
@pytest.mark.asyncio
async def test_full_api_workflow(async_client: AsyncClient, async_session: AsyncSession):
    """Test the full API workflow using httpx.AsyncClient."""
    # 1. (Superadmin login/validation is implicitly tested by the fixtures)
    login_data = {"username": os.environ["SUPERADMIN_EMAIL"], "password": os.environ["SUPERADMIN_PWD"]}
    response = await async_client.post("/login/creds", data=login_data)
    response.raise_for_status()

    token = response.json()["access_token"]

    superadmin_auth_headers = {"Authorization": f"Bearer {token}"}

    # 2. Create a member user
    member_email = "pytest-member@email.com"
    member_pwd = "pytest-dummy-pwd"  # noqa: S105
    response = await async_client.post(
        "/users/invite",
        headers=superadmin_auth_headers,
        data={"email": member_email, "password": member_pwd, "role": "member", "send_magic_link": False},
    )
    assert response.status_code == 201, f"Failed to create member: {response.text}"

    # 3. Get member token
    login_data = {"username": member_email, "password": member_pwd}
    response = await async_client.post("/login/creds", data=login_data)
    assert response.status_code == 200, f"Failed to get member token: {response.text}"
    member_token = response.json()["access_token"]
    member_auth_headers = {"Authorization": f"Bearer {member_token}"}

    # 4. Validate member token (Optional check)
    response = await async_client.get("/login/validate", headers=member_auth_headers)
    assert response.status_code == 200, f"Member validation failed: {response.text}"

    # 5. Update member password
    new_member_pwd = "pytest-dummy-pwd-updated"  # noqa: S105
    response = await async_client.patch(
        "/users/me/password", headers=member_auth_headers, data={"password": new_member_pwd}
    )
    assert response.status_code == 200, f"Failed to update member password: {response.text}"

    # 6. Update member profile picture
    img = Image.new("RGB", (96, 96), color="white")
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_bytes = img_byte_arr.getvalue()

    response = await async_client.patch(
        "/users/me/picture",
        headers=member_auth_headers,
        files={"file": ("dummy.png", img_bytes, "image/png")},
    )
    assert response.status_code == 200, f"Failed to update member profile picture: {response.text}"

    # 7. Read all users
    response = await async_client.get("/users", headers=superadmin_auth_headers)
    assert response.status_code == 200, f"Failed to read all users: {response.text}"

    # 8. Delete member user
    response = await async_client.delete("/users/me", headers=member_auth_headers)
    assert response.status_code == 204, f"Failed to delete member: {response.text}"
