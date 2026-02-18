# backend/models/scan_result.py
from extensions import db
from datetime import datetime


class ScanResult(db.Model):
    """扫描结果模型"""
    __tablename__ = 'scan_results'

    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=False)
    merchant_id = db.Column(db.String(100))
    name = db.Column(db.String(200))
    version = db.Column(db.String(50))
    type = db.Column(db.String(50))
    full_data = db.Column(db.Text)
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'ip': self.ip,
            'merchantId': self.merchant_id,
            'name': self.name,
            'version': self.version,
            'type': self.type,
            'status': 'success' if self.merchant_id else 'error',
            'fullData': self.full_data
        }


class ScanSession(db.Model):
    """扫描会话模型 - 记录最后扫描时间"""
    __tablename__ = 'scan_sessions'

    id = db.Column(db.Integer, primary_key=True, default=1)
    last_scan_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get_session():
        session = ScanSession.query.get(1)
        if not session:
            session = ScanSession(id=1)
            db.session.add(session)
            db.session.commit()
        return session
