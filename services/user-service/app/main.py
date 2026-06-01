from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import Base, engine
from app.routers import users


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="User Service",
    description="Internal user management service. Access only via API Gateway.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(users.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": settings.service_name}
