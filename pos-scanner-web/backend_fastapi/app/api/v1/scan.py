import asyncio
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.deps import get_db
from app.models import ScanResult, ScanSession, DeviceProperty, DeviceOccupancy, User
from app.services.scan_service import ScanPosService

router = APIRouter()

# Scan status storage
scan_status = {
    "is_scanning": False,
    "progress": 0,
    "current_ip": "",
    "results": [],
    "error": None,
}


class ScanStartRequest(BaseModel):
    local_ip: str


def get_local_now():
    """Get local time."""
    return datetime.now()


@router.get("/scan/ips")
async def get_local_ips():
    """Get local IP addresses."""
    try:
        service = ScanPosService()
        ips = service.get_local_ips()
        return {"success": True, "ips": ips}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/scan/start")
async def start_scan(
    data: ScanStartRequest,
    db: AsyncSession = Depends(get_db),
):
    """Start scanning."""
    global scan_status

    if scan_status["is_scanning"]:
        return {"success": False, "error": "Scan in progress"}

    local_ip = data.local_ip
    if not local_ip:
        return {"success": False, "error": "No IP address selected"}

    # Reset scan status
    scan_status = {
        "is_scanning": True,
        "progress": 0,
        "current_ip": "",
        "results": [],
        "error": None,
    }

    # Start scan in background
    asyncio.create_task(perform_scan(local_ip, db))

    return {"success": True, "message": "Scan started"}


async def perform_scan(local_ip: str, db: AsyncSession):
    """Execute scan task - incremental update mode."""
    global scan_status

    try:
        service = ScanPosService(local_ip=local_ip)
        now = get_local_now()

        # Get network range
        network = service._get_local_network()
        hosts = list(network.hosts())
        total_hosts = len(hosts)

        # Scan open ports
        open_ips = await service._scan_open_ips_async(hosts, 22080, scan_status, total_hosts)

        # Get device info
        scanned_merchant_ids = set()
        total_open = len(open_ips) if open_ips else 1

        for i, ip in enumerate(open_ips):
            scan_status["progress"] = 50 + (i + 1) * 50 // total_open
            scan_status["current_ip"] = ip

            result = await service._fetch_and_process_async(ip, 22080)
            scan_status["results"].append(result)

            merchant_id = result.get("merchantId", "")
            if merchant_id:
                scanned_merchant_ids.add(merchant_id)

                # Check if device exists
                db_result = await db.execute(
                    select(ScanResult).where(ScanResult.merchant_id == merchant_id)
                )
                existing = db_result.scalar_one_or_none()

                if existing:
                    existing.ip = result["ip"]
                    existing.name = result.get("name", "")
                    existing.version = result.get("version", "")
                    existing.type = result.get("type", "")
                    existing.full_data = json.dumps(result.get("fullData", {}))
                    existing.is_online = True
                    existing.last_online_time = now
                    existing.scanned_at = now
                else:
                    scan_result = ScanResult(
                        ip=result["ip"],
                        merchant_id=merchant_id,
                        name=result.get("name", ""),
                        version=result.get("version", ""),
                        type=result.get("type", ""),
                        full_data=json.dumps(result.get("fullData", {})),
                        is_online=True,
                        last_online_time=now,
                    )
                    db.add(scan_result)
            else:
                # No merchant_id, check by IP
                db_result = await db.execute(
                    select(ScanResult).where(
                        ScanResult.ip == result["ip"], ScanResult.merchant_id == ""
                    )
                )
                existing = db_result.scalar_one_or_none()

                if existing:
                    existing.name = result.get("name", "")
                    existing.version = result.get("version", "")
                    existing.type = result.get("type", "")
                    existing.full_data = json.dumps(result.get("fullData", {}))
                    existing.is_online = True
                    existing.last_online_time = now
                    existing.scanned_at = now
                else:
                    scan_result = ScanResult(
                        ip=result["ip"],
                        merchant_id="",
                        name=result.get("name", ""),
                        version=result.get("version", ""),
                        type=result.get("type", ""),
                        full_data=json.dumps(result.get("fullData", {})),
                        is_online=True,
                        last_online_time=now,
                    )
                    db.add(scan_result)

            await db.commit()

        # Mark non-scanned devices as offline
        if scanned_merchant_ids:
            db_result = await db.execute(
                select(ScanResult).where(
                    ScanResult.merchant_id != "", ScanResult.is_online == True
                )
            )
            all_online = db_result.scalars().all()
            for device in all_online:
                if device.merchant_id not in scanned_merchant_ids:
                    device.is_online = False
            await db.commit()

        # Update scan session time
        db_result = await db.execute(select(ScanSession).where(ScanSession.id == 1))
        session = db_result.scalar_one_or_none()
        if session:
            session.last_scan_at = now
            await db.commit()

        scan_status["is_scanning"] = False
        scan_status["progress"] = 100

    except Exception as e:
        scan_status["is_scanning"] = False
        scan_status["error"] = str(e)
        print(f"Scan failed: {e}")


@router.get("/scan/status")
async def get_scan_status():
    """Get scan status."""
    return scan_status


@router.post("/scan/stop")
async def stop_scan():
    """Stop scanning."""
    global scan_status
    scan_status["is_scanning"] = False
    return {"success": True, "message": "Scan stopped"}


@router.get("/devices")
async def get_devices(db: AsyncSession = Depends(get_db)):
    """Get all devices list."""
    # Clean up expired occupancies
    await cleanup_expired_occupancies(db)

    # Get all scan results
    result = await db.execute(select(ScanResult))
    results = result.scalars().all()

    # Get scan session
    session_result = await db.execute(select(ScanSession).where(ScanSession.id == 1))
    session = session_result.scalar_one_or_none()

    # Get device properties
    props_result = await db.execute(select(DeviceProperty))
    properties = props_result.scalars().all()
    property_map = {p.merchant_id: p.property for p in properties}

    # Get device occupancies
    occ_result = await db.execute(select(DeviceOccupancy))
    occupancies = occ_result.scalars().all()
    occupancy_map = {o.merchant_id: o for o in occupancies}

    # Get users
    users_result = await db.execute(select(User))
    users = users_result.scalars().all()
    user_map = {u.id: u for u in users}

    # Assemble device data
    devices = []
    now = get_local_now()

    for r in results:
        device_dict = r.to_dict()
        device_dict["property"] = property_map.get(r.merchant_id, "Personal PC")

        occupancy = occupancy_map.get(r.merchant_id)
        if occupancy:
            end_time = occupancy.end_time
            if end_time.tzinfo is not None:
                end_time = end_time.replace(tzinfo=None)

            if end_time > now:
                device_dict["occupancy"] = occupancy.to_dict()
                device_dict["isOccupied"] = True
            else:
                device_dict["occupancy"] = None
                device_dict["isOccupied"] = False
        else:
            device_dict["occupancy"] = None
            device_dict["isOccupied"] = False

        if r.owner_id and r.owner_id in user_map:
            owner = user_map[r.owner_id]
            device_dict["owner"] = {"id": owner.id, "username": owner.username}
        else:
            device_dict["owner"] = None

        devices.append(device_dict)

    return {
        "success": True,
        "devices": devices,
        "lastScanAt": session.last_scan_at.isoformat() if session and session.last_scan_at else None,
    }


async def cleanup_expired_occupancies(db: AsyncSession):
    """Clean up expired occupancy records."""
    now = get_local_now()
    result = await db.execute(select(DeviceOccupancy))
    occupancies = result.scalars().all()
    count = 0

    for occupancy in occupancies:
        end_time = occupancy.end_time
        if end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)
        if end_time < now:
            await db.delete(occupancy)
            count += 1

    if count > 0:
        await db.commit()
    return count


@router.get("/device/{ip}/details")
async def get_device_details(ip: str):
    """Get device details."""
    try:
        service = ScanPosService()
        full_data = await service.fetch_company_profile_async(ip)

        # Filter unnecessary fields
        def filter_data(data):
            exclude_keys = {"appInstance", "images", "result", "printLogo"}
            if isinstance(data, dict):
                return {
                    k: filter_data(v)
                    for k, v in data.items()
                    if v is not None and k not in exclude_keys
                }
            elif isinstance(data, list):
                return [filter_data(item) for item in data if item is not None]
            else:
                return data

        filtered_data = filter_data(full_data)
        return {"success": True, "data": filtered_data}
    except Exception as e:
        return {"success": False, "error": str(e)}
