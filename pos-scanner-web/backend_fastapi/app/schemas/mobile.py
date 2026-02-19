from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MobileDeviceBase(BaseModel):
    name: str
    device_type: Optional[str] = None
    sn: Optional[str] = None
    system_version: Optional[str] = None


class MobileDeviceCreate(MobileDeviceBase):
    pass


class MobileDeviceUpdate(BaseModel):
    name: Optional[str] = None
    deviceType: Optional[str] = None
    sn: Optional[str] = None
    systemVersion: Optional[str] = None
    imageA: Optional[str] = None
    imageB: Optional[str] = None


class MobileDeviceResponse(BaseModel):
    id: int
    name: str
    deviceType: Optional[str] = None
    sn: Optional[str] = None
    imageA: Optional[str] = None
    imageB: Optional[str] = None
    systemVersion: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    isOccupied: bool = False
    occupier: Optional[str] = None
    occupierId: Optional[int] = None
    purpose: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None

    class Config:
        from_attributes = True


class MobileDeviceOccupy(BaseModel):
    purpose: Optional[str] = ""
    endTime: str
