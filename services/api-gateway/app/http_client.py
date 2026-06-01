import httpx
from fastapi import HTTPException

from app.config import settings


async def service_request(
    base_url: str,
    method: str,
    path: str,
    **kwargs,
) -> httpx.Response:
    headers = {"X-Internal-Api-Key": settings.internal_api_key}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method,
            f"{base_url.rstrip('/')}{path}",
            headers=headers,
            **kwargs,
        )
    if response.status_code >= 400:
        detail: str | dict = response.text
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            pass
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response
