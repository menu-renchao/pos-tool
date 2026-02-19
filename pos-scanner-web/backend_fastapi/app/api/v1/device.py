from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.api.deps import get_db, get_current_active_user, get_current_admin_user
from app.models import User, DeviceOccupancy, ScanResult, DeviceClaim

router = APIRouter()


def get_local_now():
    """Get local time."""
    return datetime.now()


def parse_datetime(dt_str):
    """Parse datetime string, handling multiple formats."""
    if not dt_str:
        return None
    try:
        dt_str = dt_str.replace("Z", "+00:00")
        if "." in dt_str:
            parts = dt_str.split(".")
            dt_str = parts[0] + parts[1][-6:]
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception as e:
        print(f"Failed to parse datetime: {dt_str}, error: {e}")
        return None


class OccupancySet(BaseModel):
    merchant_id: str
    purpose: Optional[str] = ""
    start_time: Optional[str] = None
    end_time: str


# ============ Device Occupancy ============


@router.get("/occupancy")
async def get_occupancies(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all device occupancy info."""
    result = await db.execute(select(DeviceOccupancy))
    occupancies = result.scalars().all()

    return {"success": True, "occupancies": [o.to_dict() for o in occupancies]}


@router.put("/occupancy")
async def set_occupancy(
    data: OccupancySet,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Set device borrowing (all users)."""
    merchant_id = data.merchant_id
    purpose = data.purpose or ""
    start_time_str = data.start_time
    end_time_str = data.end_time

    if not merchant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Merchant ID is required"},
        )

    if not end_time_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "End time is required"},
        )

    start_time = parse_datetime(start_time_str) if start_time_str else get_local_now()
    end_time = parse_datetime(end_time_str)

    if end_time is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": f"Invalid time format: {end_time_str}"},
        )

    if end_time <= start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "End time must be after start time"},
        )

    result = await db.execute(
        select(DeviceOccupancy).where(DeviceOccupancy.merchant_id == merchant_id)
    )
    occupancy = result.scalar_one_or_none()

    if occupancy:
        occupancy.user_id = current_user.id
        occupancy.purpose = purpose
        occupancy.start_time = start_time
        occupancy.end_time = end_time
    else:
        occupancy = DeviceOccupancy(
            merchant_id=merchant_id,
            user_id=current_user.id,
            purpose=purpose,
            start_time=start_time,
            end_time=end_time,
        )
        db.add(occupancy)

    await db.commit()

    return {
        "success": True,
        "message": "Borrowing info updated",
        "occupancy": occupancy.to_dict(),
    }


@router.delete("/occupancy/{merchant_id}")
async def release_occupancy(
    merchant_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return device."""
    result = await db.execute(
        select(DeviceOccupancy).where(DeviceOccupancy.merchant_id == merchant_id)
    )
    occupancy = result.scalar_one_or_none()

    if not occupancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Borrowing info not found"},
        )

    # Only borrower or admin can return
    if occupancy.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "error": "Not authorized to return this device"},
        )

    await db.delete(occupancy)
    await db.commit()

    return {"success": True, "message": "Device returned"}


@router.delete("/{merchant_id}")
async def delete_device(
    merchant_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete device (admin only)."""
    result = await db.execute(select(ScanResult).where(ScanResult.merchant_id == merchant_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Device not found"},
        )

    # Delete related occupancy and claims
    result = await db.execute(
        select(DeviceOccupancy).where(DeviceOccupancy.merchant_id == merchant_id)
    )
    occupancy = result.scalar_one_or_none()
    if occupancy:
        await db.delete(occupancy)

    result = await db.execute(select(DeviceClaim).where(DeviceClaim.merchant_id == merchant_id))
    claims = result.scalars().all()
    for claim in claims:
        await db.delete(claim)

    await db.delete(device)
    await db.commit()

    return {"success": True, "message": "Device deleted"}


# ============ Device Claims ============


@router.post("/claim")
async def submit_claim(
    data: BaseModel,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit device claim request."""
    # Extract merchant_id from request
    import json
    from fastapi import Request

    pass  # Will be handled in route


class ClaimRequest(BaseModel):
    merchant_id: str


@router.post("/claims")
async def submit_claim_v2(
    request: ClaimRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit device claim request."""
    merchant_id = request.merchant_id

    if not merchant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Merchant ID is required"},
        )

    # Check device exists
    result = await db.execute(select(ScanResult).where(ScanResult.merchant_id == merchant_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Device not found"},
        )

    # Check if already claimed
    if device.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Device already claimed"},
        )

    # Check for pending claims
    result = await db.execute(
        select(DeviceClaim).where(
            DeviceClaim.merchant_id == merchant_id, DeviceClaim.status == "pending"
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Device has pending claim request"},
        )

    # Check user's own pending claim
    result = await db.execute(
        select(DeviceClaim).where(
            DeviceClaim.user_id == current_user.id,
            DeviceClaim.merchant_id == merchant_id,
            DeviceClaim.status == "pending",
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "You already submitted a claim request"},
        )

    # Create claim
    claim = DeviceClaim(merchant_id=merchant_id, user_id=current_user.id)
    db.add(claim)
    await db.commit()

    return {"success": True, "message": "Claim request submitted, waiting for admin approval"}


@router.get("/claims")
async def get_claims(
    status_filter: str = "pending",
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get claim requests (admin only)."""
    result = await db.execute(
        select(DeviceClaim)
        .where(DeviceClaim.status == status_filter)
        .order_by(DeviceClaim.created_at.desc())
    )
    claims = result.scalars().all()

    result_list = []
    for claim in claims:
        user_result = await db.execute(select(User).where(User.id == claim.user_id))
        claim_user = user_result.scalar_one_or_none()

        device_result = await db.execute(
            select(ScanResult).where(ScanResult.merchant_id == claim.merchant_id)
        )
        device = device_result.scalar_one_or_none()

        result_list.append({
            "id": claim.id,
            "merchantId": claim.merchant_id,
            "deviceName": device.name if device else "Unknown device",
            "userId": claim.user_id,
            "username": claim_user.username if claim_user else "Unknown user",
            "status": claim.status,
            "createdAt": claim.created_at.isoformat() if claim.created_at else None,
            "processedAt": claim.processed_at.isoformat() if claim.processed_at else None,
        })

    return {"success": True, "claims": result_list}


@router.post("/claim/{claim_id}/approve")
async def approve_claim(
    claim_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve claim request (admin only)."""
    result = await db.execute(select(DeviceClaim).where(DeviceClaim.id == claim_id))
    claim = result.scalar_one_or_none()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Claim not found"},
        )

    if claim.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Claim already processed"},
        )

    # Check device
    result = await db.execute(select(ScanResult).where(ScanResult.merchant_id == claim.merchant_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Device not found"},
        )

    if device.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Device already claimed"},
        )

    # Update claim status
    claim.status = "approved"
    claim.processed_at = get_local_now()
    claim.processed_by = current_user.id

    # Set device owner
    device.owner_id = claim.user_id

    # Reject other pending claims
    result = await db.execute(
        select(DeviceClaim).where(
            DeviceClaim.merchant_id == claim.merchant_id,
            DeviceClaim.id != claim_id,
            DeviceClaim.status == "pending",
        )
    )
    other_claims = result.scalars().all()
    for other in other_claims:
        other.status = "rejected"
        other.processed_at = get_local_now()
        other.processed_by = current_user.id

    await db.commit()

    return {"success": True, "message": "Claim approved"}


@router.post("/claim/{claim_id}/reject")
async def reject_claim(
    claim_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject claim request (admin only)."""
    result = await db.execute(select(DeviceClaim).where(DeviceClaim.id == claim_id))
    claim = result.scalar_one_or_none()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Claim not found"},
        )

    if claim.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Claim already processed"},
        )

    claim.status = "rejected"
    claim.processed_at = get_local_now()
    claim.processed_by = current_user.id

    await db.commit()

    return {"success": True, "message": "Claim rejected"}


@router.delete("/{merchant_id}/owner")
async def reset_owner(
    merchant_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset device claim status (admin only)."""
    result = await db.execute(select(ScanResult).where(ScanResult.merchant_id == merchant_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Device not found"},
        )

    device.owner_id = None
    await db.commit()

    return {"success": True, "message": "Device ownership reset"}


# Fix the claim route
router.add_api_route("/claim", submit_claim_v2, methods=["POST"])
