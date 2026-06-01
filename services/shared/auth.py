"""Shared internal service authentication."""

from fastapi import Header, HTTPException, status

INTERNAL_HEADER = "X-Internal-Api-Key"


def verify_internal_api_key(
    x_internal_api_key: str | None = Header(default=None, alias=INTERNAL_HEADER),
    *,
    expected_key: str,
) -> None:
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal API key not configured",
        )
    if x_internal_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing internal API key",
        )
