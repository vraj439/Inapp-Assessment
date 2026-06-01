from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Query, status

from app.config import settings
from app.schemas import UserCreate, UserListResponse, UserResponse, UserUpdate

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

HEADERS = {"X-Internal-Api-Key": settings.internal_api_key}
BASE = settings.user_service_url.rstrip("/")


async def _request(method: str, path: str, **kwargs) -> httpx.Response:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, f"{BASE}{path}", headers=HEADERS, **kwargs)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.json().get("detail", response.text))
    return response


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create user")
async def create_user(payload: UserCreate) -> UserResponse:
    response = await _request("POST", "/users", json=payload.model_dump(mode="json"))
    return UserResponse.model_validate(response.json())


@router.get("", response_model=UserListResponse, summary="List users")
async def list_users(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)) -> UserListResponse:
    response = await _request("GET", "/users", params={"skip": skip, "limit": limit})
    return UserListResponse.model_validate(response.json())


@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID")
async def get_user(user_id: UUID) -> UserResponse:
    response = await _request("GET", f"/users/{user_id}")
    return UserResponse.model_validate(response.json())


@router.patch("/{user_id}", response_model=UserResponse, summary="Update user")
async def update_user(user_id: UUID, payload: UserUpdate) -> UserResponse:
    response = await _request(
        "PATCH", f"/users/{user_id}", json=payload.model_dump(mode="json", exclude_unset=True)
    )
    return UserResponse.model_validate(response.json())


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete user")
async def delete_user(user_id: UUID) -> None:
    await _request("DELETE", f"/users/{user_id}")
