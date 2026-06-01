from typing import Any

import httpx
from fastapi import HTTPException, Request, Response, status


class ServiceProxy:
    def __init__(self, base_url: str, internal_api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.internal_headers = {"X-Internal-Api-Key": internal_api_key}

    async def forward(self, request: Request, path: str) -> Response:
        url = f"{self.base_url}{path}"
        headers = dict(request.headers)
        headers.pop("host", None)
        headers.update(self.internal_headers)

        body = await request.body()
        params = list(request.query_params.multi_items())

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                upstream = await client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body if body else None,
                    params=params,
                )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Upstream service unavailable: {exc}",
            ) from exc

        response_headers = {
            key: value
            for key, value in upstream.headers.items()
            if key.lower() not in {"content-encoding", "transfer-encoding", "connection"}
        }
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=response_headers,
            media_type=upstream.headers.get("content-type"),
        )
