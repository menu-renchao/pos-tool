from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.session import Base


class DeviceOccupancy(Base):
    """Device occupancy model - linked to merchant ID."""

    __tablename__ = "device_occupancies"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    purpose = Column(String(500))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="occupancies")

    def to_dict(self):
        return {
            "merchantId": self.merchant_id,
            "userId": self.user_id,
            "username": self.user.username if self.user else None,
            "purpose": self.purpose,
            "startTime": self.start_time.isoformat() if self.start_time else None,
            "endTime": self.end_time.isoformat() if self.end_time else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
