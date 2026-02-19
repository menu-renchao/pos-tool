from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime

from app.db.session import Base


class DeviceProperty(Base):
    """Device property model - linked to merchant ID."""

    __tablename__ = "device_properties"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(String(100), unique=True, nullable=False, index=True)
    property = Column(String(100), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "merchantId": self.merchant_id,
            "property": self.property,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
