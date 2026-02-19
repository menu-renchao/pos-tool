from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DeviceOccupancyCreate(BaseModel):
    merchant_id: str
    purpose: Optional[str] = ""
    start_time: Optional[str] = None
    end_time: str


class DeviceOccupancyResponse(BaseModel):
    merchantId: str
    userId: int
    username: Optional[str] = None
    purpose: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    createdAt: Optional[str] = None

    class Config:
        from_attributes = True


class DeviceClaimResponse(BaseModel):
    id: int
    merchantId: str
    deviceName: Optional[str] = None
    userId: int
    username: Optional[str] = None
    status: str
    createdAt: Optional[str] = None
    processedAt: Optional[str] = None

    class Config:
        from_attributes = True
