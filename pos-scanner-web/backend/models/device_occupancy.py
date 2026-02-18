# backend/models/device_occupancy.py
from extensions import db
from datetime import datetime


class DeviceOccupancy(db.Model):
    """设备占用模型 - 与商家ID关联"""
    __tablename__ = 'device_occupancies'

    id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    purpose = db.Column(db.String(500))  # 用途
    start_time = db.Column(db.DateTime, nullable=False)  # 开始时间
    end_time = db.Column(db.DateTime, nullable=False)  # 结束时间（释放时间）
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 关联用户
    user = db.relationship('User', backref='occupancies')

    def to_dict(self):
        return {
            'merchantId': self.merchant_id,
            'userId': self.user_id,
            'username': self.user.username if self.user else None,
            'purpose': self.purpose,
            'startTime': self.start_time.isoformat() if self.start_time else None,
            'endTime': self.end_time.isoformat() if self.end_time else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }
