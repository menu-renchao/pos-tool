from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.session import Base


class MobileDevice(Base):
    """Mobile device model."""

    __tablename__ = "mobile_devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    device_type = Column(String(100))
    sn = Column(String(100))
    image_a = Column(String(500))
    image_b = Column(String(500))
    system_version = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Occupancy related
    occupier_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    purpose = Column(String(500))
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    # Relationship
    occupier = relationship("User", back_populates="occupied_devices")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "deviceType": self.device_type,
            "sn": self.sn,
            "imageA": self.image_a,
            "imageB": self.image_b,
            "systemVersion": self.system_version,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
            "isOccupied": self.end_time is not None and self.end_time > datetime.now(),
            "occupier": self.occupier.username if self.occupier else None,
            "occupierId": self.occupier_id,
            "purpose": self.purpose,
            "startTime": self.start_time.isoformat() if self.start_time else None,
            "endTime": self.end_time.isoformat() if self.end_time else None,
        }
