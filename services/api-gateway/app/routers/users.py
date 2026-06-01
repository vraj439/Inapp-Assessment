from uuid import UUID

from fastapi import APIRouter, Query, status

from app.config import settings
from app.http_client import service_request
from app.schemas import UserCreate, UserListResponse, UserResponse, UserUpdate

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create user")
async def create_user(payload: UserCreate) -> UserResponse:
    response = await service_request(settings.user_service_url, "POST", "/users", json=payload.model_dump(mode="json"))
    return UserResponse.model_validate(response.json())


@router.get("", response_model=UserListResponse, summary="List users")
async def list_users(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)) -> UserListResponse:
    response = await service_request(
        settings.user_service_url, "GET", "/users", params={"skip": skip, "limit": limit}
    )
    return UserListResponse.model_validate(response.json())


@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID")
async def get_user(user_id: UUID) -> UserResponse:
    response = await service_request(settings.user_service_url, "GET", f"/users/{user_id}")
    return UserResponse.model_validate(response.json())


@router.patch("/{user_id}", response_model=UserResponse, summary="Update user")
async def update_user(user_id: UUID, payload: UserUpdate) -> UserResponse:
    response = await service_request(
        settings.user_service_url,
        "PATCH",
        f"/users/{user_id}",
        json=payload.model_dump(mode="json", exclude_unset=True),
    )
    return UserResponse.model_validate(response.json())


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete user")
async def delete_user(user_id: UUID) -> None:
    await service_request(settings.user_service_url, "DELETE", f"/users/{user_id}")
