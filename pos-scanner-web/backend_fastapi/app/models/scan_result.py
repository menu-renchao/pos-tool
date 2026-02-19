from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.db.session import Base


class ScanResult(Base):
    """Scan result model."""

    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String(50), nullable=False)
    merchant_id = Column(String(100), index=True)
    name = Column(String(200))
    version = Column(String(50))
    type = Column(String(50))
    full_data = Column(Text)
    scanned_at = Column(DateTime, default=datetime.utcnow)
    is_online = Column(Boolean, default=True)
    last_online_time = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"))

    def to_dict(self):
        return {
            "ip": self.ip,
            "merchantId": self.merchant_id,
            "name": self.name,
            "version": self.version,
            "type": self.type,
            "status": "success" if self.merchant_id else "error",
            "fullData": self.full_data,
            "isOnline": self.is_online,
            "lastOnlineTime": self.last_online_time.isoformat() if self.last_online_time else None,
            "ownerId": self.owner_id,
        }


class DeviceClaim(Base):
    """Device claim request model."""

    __tablename__ = "device_claims"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(String(100), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    processed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "merchantId": self.merchant_id,
            "userId": self.user_id,
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "processedAt": self.processed_at.isoformat() if self.processed_at else None,
        }


class ScanSession(Base):
    """Scan session model - records last scan time."""

    __tablename__ = "scan_sessions"

    id = Column(Integer, primary_key=True, default=1)
    last_scan_at = Column(DateTime, default=datetime.utcnow)
