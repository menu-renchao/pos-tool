from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.deps import get_db, get_current_user, get_current_active_user
from app.models import User
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
)
from app.schemas.auth import LoginRequest, RegisterRequest, PasswordChange
from app.schemas.user import UserResponse

router = APIRouter()


class TokenResponse(BaseModel):
    success: bool = True
    access_token: str
    refresh_token: str
    user: UserResponse


@router.post("/register")
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """User registration."""
    username = data.username.strip()
    password = data.password
    email = data.email.strip()

    # Validate input
    if not username or not password or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "All fields are required"},
        )

    if len(username) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Username must be at least 3 characters"},
        )

    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Password must be at least 6 characters"},
        )

    # Check if username exists
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Username already exists"},
        )

    # Check if email exists
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Email already registered"},
        )

    # Create user
    user = User(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
    )
    db.add(user)
    await db.commit()

    return {"success": True, "message": "Registration successful, please wait for admin approval"}


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """User login."""
    username = data.username.strip()
    password = data.password

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Username and password are required"},
        )

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error": "Invalid username or password"},
        )

    if user.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "error": "Account not yet approved"},
        )

    # Create tokens
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return {
        "success": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": UserResponse.model_validate(user),
    }


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """User logout."""
    return {"success": True, "message": "Logout successful"}


@router.get("/profile")
async def profile(current_user: User = Depends(get_current_active_user)):
    """Get current user profile."""
    return {"success": True, "user": UserResponse.model_validate(current_user)}


@router.put("/password")
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password."""
    old_password = data.old_password
    new_password = data.new_password

    if not old_password or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Old and new passwords are required"},
        )

    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Incorrect old password"},
        )

    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "New password must be at least 6 characters"},
        )

    current_user.password_hash = get_password_hash(new_password)
    await db.commit()

    return {"success": True, "message": "Password changed successfully"}
