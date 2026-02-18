# backend/models/mobile_device.py
from extensions import db
from datetime import datetime


class MobileDevice(db.Model):
    """移动设备模型"""
    __tablename__ = 'mobile_devices'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # 设备名称
    device_type = db.Column(db.String(100))  # 设备类型
    image_a = db.Column(db.String(500))  # A面图片路径
    image_b = db.Column(db.String(500))  # B面图片路径
    system_version = db.Column(db.String(100))  # 系统版本
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 占用相关
    occupier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    purpose = db.Column(db.String(500))  # 用途
    start_time = db.Column(db.DateTime)  # 占用开始时间
    end_time = db.Column(db.DateTime)  # 占用结束时间（释放时间）

    # 关联用户
    occupier = db.relationship('User', backref='occupied_devices')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'deviceType': self.device_type,
            'imageA': self.image_a,
            'imageB': self.image_b,
            'systemVersion': self.system_version,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'isOccupied': self.end_time is not None and self.end_time > datetime.now(),
            'occupier': self.occupier.username if self.occupier else None,
            'occupierId': self.occupier_id,
            'purpose': self.purpose,
            'startTime': self.start_time.isoformat() if self.start_time else None,
            'endTime': self.end_time.isoformat() if self.end_time else None
        }
