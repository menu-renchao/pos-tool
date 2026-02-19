from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.api.deps import get_db, get_current_admin_user
from app.models import User, DeviceProperty
from app.core.security import get_password_hash
from app.schemas.user import UserResponse

router = APIRouter()


class UserCreateAdmin(BaseModel):
    username: str
    password: str
    email: EmailStr
    role: str = "user"
    status: str = "approved"


class UserUpdateAdmin(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    status: Optional[str] = None


class PasswordReset(BaseModel):
    new_password: str


class DevicePropertySet(BaseModel):
    merchant_id: str
    property: str


# ============ User Management ============


@router.get("/users")
async def get_users(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user list (admin only)."""
    query = select(User)

    if status_filter and status_filter != "all":
        query = query.where(User.status == status_filter)

    query = query.order_by(User.created_at.desc())
    result = await db.execute(query)
    users = result.scalars().all()

    return {"success": True, "users": [u.to_dict() for u in users]}


@router.post("/users")
async def create_user(
    data: UserCreateAdmin,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create user (admin only)."""
    username = data.username.strip()
    password = data.password
    email = data.email.strip()

    # Validate
    if not username or not password or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Username, password, and email are required"},
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

    if data.role not in ["user", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Role must be 'user' or 'admin'"},
        )

    # Check duplicates
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Username already exists"},
        )

    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Email already in use"},
        )

    # Create user
    user = User(
        username=username,
        email=email,
        role=data.role,
        status=data.status,
        password_hash=get_password_hash(password),
    )
    db.add(user)
    await db.commit()

    return {
        "success": True,
        "message": "User created successfully",
        "user": user.to_dict(),
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdateAdmin,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user info (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "User not found"},
        )

    # Update username
    if data.username is not None:
        new_username = data.username.strip()
        if new_username and new_username != user.username:
            result = await db.execute(
                select(User).where(User.username == new_username, User.id != user_id)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"success": False, "error": "Username already exists"},
                )
            user.username = new_username

    # Update email
    if data.email is not None:
        new_email = data.email.strip()
        if new_email and new_email != user.email:
            result = await db.execute(
                select(User).where(User.email == new_email, User.id != user_id)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"success": False, "error": "Email already in use"},
                )
            user.email = new_email

    # Update role
    if data.role is not None:
        if data.role not in ["user", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "error": "Role must be 'user' or 'admin'"},
            )
        # Prevent admin from removing their own admin role
        if user_id == current_user.id and data.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "error": "Cannot remove your own admin role"},
            )
        user.role = data.role

    # Update status
    if data.status is not None:
        if data.status not in ["pending", "approved", "rejected"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "error": "Invalid status"},
            )
        user.status = data.status

    await db.commit()

    return {
        "success": True,
        "message": "User updated successfully",
        "user": user.to_dict(),
    }


@router.put("/users/{user_id}/approve")
async def approve_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "User not found"},
        )

    if user.status == "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "User already approved"},
        )

    user.status = "approved"
    await db.commit()

    return {"success": True, "message": "User approved"}


@router.put("/users/{user_id}/reject")
async def reject_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "User not found"},
        )

    if user.status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "User already rejected"},
        )

    user.status = "rejected"
    await db.commit()

    return {"success": True, "message": "User rejected"}


@router.put("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    data: PasswordReset,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset user password."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "User not found"},
        )

    if not data.new_password or len(data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Password must be at least 6 characters"},
        )

    user.password_hash = get_password_hash(data.new_password)
    await db.commit()

    return {"success": True, "message": "Password reset successfully"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete user."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Cannot delete your own account"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "User not found"},
        )

    await db.delete(user)
    await db.commit()

    return {"success": True, "message": "User deleted"}


# ============ Device Properties ============


@router.get("/device-properties")
async def get_device_properties(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all device properties."""
    result = await db.execute(select(DeviceProperty))
    properties = result.scalars().all()

    return {"success": True, "properties": [p.to_dict() for p in properties]}


@router.put("/device-properties")
async def set_device_property(
    data: DevicePropertySet,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Set device property (admin only)."""
    if not data.merchant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Merchant ID is required"},
        )

    if not data.property:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Property is required"},
        )

    result = await db.execute(
        select(DeviceProperty).where(DeviceProperty.merchant_id == data.merchant_id)
    )
    device_prop = result.scalar_one_or_none()

    if device_prop:
        device_prop.property = data.property
    else:
        device_prop = DeviceProperty(merchant_id=data.merchant_id, property=data.property)
        db.add(device_prop)

    await db.commit()

    return {
        "success": True,
        "message": "Device property updated",
        "property": device_prop.to_dict(),
    }


@router.delete("/device-properties/{merchant_id}")
async def delete_device_property(
    merchant_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete device property."""
    result = await db.execute(
        select(DeviceProperty).where(DeviceProperty.merchant_id == merchant_id)
    )
    device_prop = result.scalar_one_or_none()

    if not device_prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Device property not found"},
        )

    await db.delete(device_prop)
    await db.commit()

    return {"success": True, "message": "Device property deleted"}
