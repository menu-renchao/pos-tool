from datetime import datetime
import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.api.deps import get_db, get_current_active_user, get_current_admin_user
from app.models import User, MobileDevice
from app.config import settings

router = APIRouter()

UPLOAD_FOLDER = "uploads/mobile_devices"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_local_now():
    return datetime.now()


class MobileDeviceCreate(BaseModel):
    name: str
    deviceType: Optional[str] = ""
    sn: Optional[str] = ""
    systemVersion: Optional[str] = ""


class MobileDeviceUpdate(BaseModel):
    name: Optional[str] = None
    deviceType: Optional[str] = None
    sn: Optional[str] = None
    systemVersion: Optional[str] = None
    imageA: Optional[str] = None
    imageB: Optional[str] = None


class MobileDeviceOccupy(BaseModel):
    purpose: Optional[str] = ""
    endTime: str


# ============ Device Management (Admin) ============


@router.get("/devices")
async def get_devices(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all mobile devices."""
    result = await db.execute(select(MobileDevice).order_by(MobileDevice.created_at.desc()))
    devices = result.scalars().all()

    return {"success": True, "devices": [d.to_dict() for d in devices]}


@router.post("/devices")
async def create_device(
    data: MobileDeviceCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create mobile device (admin only)."""
    if not data.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Device name is required"},
        )

    device = MobileDevice(
        name=data.name,
        device_type=data.deviceType,
        sn=data.sn,
        system_version=data.systemVersion,
    )
    db.add(device)
    await db.commit()

    return {
        "success": True,
        "message": "Device created successfully",
        "device": device.to_dict(),
    }


@router.put("/devices/{device_id}")
async def update_device(
    device_id: int,
    data: MobileDeviceUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update mobile device (admin only)."""
    result = await db.execute(select(MobileDevice).where(MobileDevice.id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Device not found"},
        )

    if data.name is not None:
        device.name = data.name
    if data.deviceType is not None:
        device.device_type = data.deviceType
    if data.sn is not None:
        device.sn = data.sn
    if data.systemVersion is not None:
        device.system_version = data.systemVersion
    if data.imageA is not None:
        device.image_a = data.imageA
    if data.imageB is not None:
        device.image_b = data.imageB

    await db.commit()

    return {
        "success": True,
        "message": "Device updated successfully",
        "device": device.to_dict(),
    }


@router.delete("/devices/{device_id}")
async def delete_device(
    device_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete mobile device (admin only)."""
    result = await db.execute(select(MobileDevice).where(MobileDevice.id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Device not found"},
        )

    # Delete associated images
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if device.image_a:
        try:
            os.remove(os.path.join(base_dir, device.image_a))
        except:
            pass
    if device.image_b:
        try:
            os.remove(os.path.join(base_dir, device.image_b))
        except:
            pass

    await db.delete(device)
    await db.commit()

    return {"success": True, "message": "Device deleted"}


@router.post("/devices/{device_id}/upload")
async def upload_image(
    device_id: int,
    image: UploadFile = File(...),
    type: str = Form("a"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload device image (admin only)."""
    result = await db.execute(select(MobileDevice).where(MobileDevice.id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Device not found"},
        )

    if not image.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "No file selected"},
        )

    if not allowed_file(image.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Unsupported file format"},
        )

    # Ensure upload directory exists
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    upload_dir = os.path.join(base_dir, UPLOAD_FOLDER)
    os.makedirs(upload_dir, exist_ok=True)

    # Generate filename
    from werkzeug.utils import secure_filename

    filename = secure_filename(f"{device_id}_{type}_{image.filename}")
    filepath = os.path.join(upload_dir, filename)

    # Save file
    content = await image.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # Save relative path
    relative_path = os.path.join(UPLOAD_FOLDER, filename).replace("\\", "/")
    if type == "a":
        device.image_a = relative_path
    else:
        device.image_b = relative_path

    await db.commit()

    return {
        "success": True,
        "message": "Image uploaded successfully",
        "path": relative_path,
    }


# ============ Borrowing (All Users) ============


@router.put("/devices/{device_id}/occupy")
async def set_occupancy(
    device_id: int,
    data: MobileDeviceOccupy,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Borrow device (all users)."""
    result = await db.execute(select(MobileDevice).where(MobileDevice.id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Device not found"},
        )

    if not data.endTime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "End time is required"},
        )

    # Parse time
    end_time_str = data.endTime.replace("Z", "+00:00")
    if "." in end_time_str:
        parts = end_time_str.split(".")
        end_time_str = parts[0] + parts[1][-6:]
    try:
        end_time = datetime.fromisoformat(end_time_str)
        if end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": f"Invalid time format: {str(e)}"},
        )

    # Set occupancy
    device.occupier_id = current_user.id
    device.purpose = data.purpose
    device.start_time = get_local_now()
    device.end_time = end_time

    await db.commit()

    return {
        "success": True,
        "message": "Device borrowed successfully",
        "device": device.to_dict(),
    }


@router.put("/devices/{device_id}/release")
async def release_occupancy(
    device_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return device."""
    result = await db.execute(select(MobileDevice).where(MobileDevice.id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Device not found"},
        )

    # Only borrower or admin can return
    if device.occupier_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "error": "Not authorized to return this device"},
        )

    device.occupier_id = None
    device.purpose = None
    device.start_time = None
    device.end_time = None

    await db.commit()

    return {
        "success": True,
        "message": "Device returned",
        "device": device.to_dict(),
    }
