from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]


def require_internal_key(
    x_internal_api_key: str | None = Header(default=None, alias="X-Internal-Api-Key"),
) -> None:
    if x_internal_api_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing internal API key",
        )


InternalAuth = Annotated[None, Depends(require_internal_key)]
