import httpx
from fastapi import HTTPException

from app.config import settings

INTERNAL_HEADER = "X-Internal-Api-Key"


def internal_headers() -> dict[str, str]:
    return {INTERNAL_HEADER: settings.internal_api_key}


async def service_request(
    base_url: str,
    method: str,
    path: str,
    **kwargs,
) -> httpx.Response:
    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        response = await client.request(
            method,
            f"{base_url.rstrip('/')}{path}",
            headers=internal_headers(),
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
