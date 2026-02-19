from fastapi import APIRouter

from .auth import router as auth_router
from .admin import router as admin_router
from .device import router as device_router
from .mobile import router as mobile_router
from .scan import router as scan_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(device_router, prefix="/device", tags=["device"])
api_router.include_router(mobile_router, prefix="/mobile", tags=["mobile"])
api_router.include_router(scan_router, tags=["scan"])
