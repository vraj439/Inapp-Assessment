from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.config import settings


class UserServiceClient:
    def __init__(self) -> None:
        self.base_url = settings.user_service_url.rstrip("/")
        self.headers = {"X-Internal-Api-Key": settings.internal_api_key}

    async def validate_users_exist(self, user_ids: list[UUID]) -> None:
        if not user_ids:
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            for user_id in user_ids:
                response = await client.get(
                    f"{self.base_url}/users/{user_id}",
                    headers=self.headers,
                )
                if response.status_code == status.HTTP_404_NOT_FOUND:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"User {user_id} not found",
                    )
                if response.status_code >= 400:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="User service unavailable",
                    )
