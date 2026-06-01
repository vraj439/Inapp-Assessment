from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.dependencies import DbSession, InternalAuth
from app.models import User
from app.schemas import UserCreate, UserListResponse, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, _auth: InternalAuth, db: DbSession) -> User:
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=payload.email, full_name=payload.full_name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("", response_model=UserListResponse)
async def list_users(
    _auth: InternalAuth,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> UserListResponse:
    total = await db.scalar(select(func.count()).select_from(User)) or 0
    result = await db.execute(select(User).order_by(User.created_at.desc()).offset(skip).limit(limit))
    users = result.scalars().all()
    return UserListResponse(items=users, total=total)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID, _auth: InternalAuth, db: DbSession) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(user_id: UUID, payload: UserUpdate, _auth: InternalAuth, db: DbSession) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.email is not None:
        existing = await db.scalar(
            select(User).where(User.email == payload.email, User.id != user_id)
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        user.email = payload.email
    if payload.full_name is not None:
        user.full_name = payload.full_name

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID, _auth: InternalAuth, db: DbSession) -> None:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await db.delete(user)
    await db.commit()
