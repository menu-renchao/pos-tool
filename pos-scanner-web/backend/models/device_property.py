# backend/models/device_property.py
from extensions import db
from datetime import datetime


class DeviceProperty(db.Model):
    """设备性质模型 - 与商家ID关联"""
    __tablename__ = 'device_properties'

    id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    property = db.Column(db.String(100), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'merchantId': self.merchant_id,
            'property': self.property,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }
