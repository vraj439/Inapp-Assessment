from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.config import settings


class ServiceClients:
    def __init__(self) -> None:
        self.headers = {"X-Internal-Api-Key": settings.internal_api_key}

    async def validate_user(self, user_id: UUID) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.user_service_url.rstrip('/')}/users/{user_id}",
                headers=self.headers,
            )
            if response.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User {user_id} not found")
            if response.status_code >= 400:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="User service unavailable")

    async def validate_event(self, event_series_id: UUID) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.event_service_url.rstrip('/')}/events/{event_series_id}",
                headers=self.headers,
            )
            if response.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event not found")
            if response.status_code >= 400:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Event service unavailable")
