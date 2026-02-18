# 共享扫描结果功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现扫描结果数据库持久化，所有用户共享结果，显示上次更新时间。

**Architecture:** 新增 ScanResult 和 ScanSession 数据库模型，扫描时保存到 SQLite，前端加载时获取结果和更新时间，启动时清理24小时过期数据。

**Tech Stack:** Flask-SQLAlchemy, SQLite, React

---

### Task 1: 创建扫描结果数据模型

**Files:**
- Create: `backend/models/scan_result.py`
- Modify: `backend/models/__init__.py`

**Step 1: 创建 ScanResult 和 ScanSession 模型**

```python
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
```

**Step 2: 更新 models/__init__.py 导出**

```python
# backend/models/__init__.py
from .user import User
from .scan_result import ScanResult, ScanSession
```

**Step 3: 提交**

```bash
git add backend/models/scan_result.py backend/models/__init__.py
git commit -m "feat: add ScanResult and ScanSession models"
```

---

### Task 2: 修改后端扫描逻辑

**Files:**
- Modify: `backend/app.py`

**Step 1: 导入新模型**

在 `from models import User` 后添加：

```python
from models import User, ScanResult, ScanSession
```

**Step 2: 添加清理过期数据的函数**

在 `init_db()` 函数后添加：

```python
def cleanup_old_results():
    """清理超过24小时的扫描结果"""
    from datetime import timedelta
    threshold = datetime.utcnow() - timedelta(hours=24)
    deleted = ScanResult.query.filter(ScanResult.scanned_at < threshold).delete()
    if deleted > 0:
        logger.info(f"已清理 {deleted} 条过期扫描结果")
        db.session.commit()
```

需要在文件顶部添加导入：

```python
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
```

**Step 3: 修改 init_db 函数**

```python
def init_db():
    """初始化数据库和默认管理员"""
    global _db_initialized
    if _db_initialized:
        return

    db.create_all()
    # 创建默认管理员
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', role='admin', status='approved')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

    # 初始化扫描会话
    ScanSession.get_session()

    # 清理过期数据
    cleanup_old_results()

    _db_initialized = True
```

**Step 4: 修改 perform_scan 函数保存结果到数据库**

找到 `scan_status['results'].append(result)` 行，替换整个 `perform_scan` 函数：

```python
def perform_scan(local_ip):
    """执行扫描任务"""
    global scan_status
    try:
        service = ScanPosService(local_ip=local_ip)

        # 获取网络范围
        network = service._get_local_network()
        hosts = list(network.hosts())
        total_hosts = len(hosts)

        # 扫描开放端口
        open_ips = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=200) as port_executor:
            futures = {port_executor.submit(service._scan_port, ip, 22080): ip for ip in hosts}
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                scan_status['progress'] = (i + 1) * 50 // total_hosts
                scan_status['current_ip'] = str(futures[future])

                if future.result():
                    open_ips.append(str(future.result()))

        # 清空旧结果
        ScanResult.query.delete()

        # 获取设备信息并保存到数据库
        total_open = len(open_ips)
        for i, ip in enumerate(open_ips):
            scan_status['progress'] = 50 + (i + 1) * 50 // total_open if total_open > 0 else 100
            scan_status['current_ip'] = ip

            result = service._fetch_and_process(ip, 22080)

            # 保存到数据库
            scan_result = ScanResult(
                ip=result['ip'],
                merchant_id=result.get('merchantId', ''),
                name=result.get('name', ''),
                version=result.get('version', ''),
                type=result.get('type', ''),
                full_data=json.dumps(result.get('fullData', {}))
            )
            db.session.add(scan_result)
            scan_status['results'].append(result)

        # 更新扫描会话时间
        session = ScanSession.get_session()
        session.last_scan_at = datetime.utcnow()

        db.session.commit()

        scan_status['is_scanning'] = False
        scan_status['progress'] = 100

    except Exception as e:
        scan_status['is_scanning'] = False
        scan_status['error'] = str(e)
        logger.error(f"扫描失败: {e}")
```

**Step 5: 修改 get_devices 接口返回最后扫描时间**

```python
@app.route('/api/devices', methods=['GET'])
def get_devices():
    """获取所有设备列表"""
    results = ScanResult.query.all()
    session = ScanSession.get_session()

    return jsonify({
        'success': True,
        'devices': [r.to_dict() for r in results],
        'lastScanAt': session.last_scan_at.isoformat() if session.last_scan_at else None
    })
```

**Step 6: 提交**

```bash
git add backend/app.py
git commit -m "feat: persist scan results to database"
```

---

### Task 3: 修改前端显示上次更新时间

**Files:**
- Modify: `frontend/src/pages/ScanPage.jsx`
- Modify: `frontend/src/services/api.js`

**Step 1: 修改 api.js 添加获取设备接口**

在 `scanAPI` 对象中已有 `getScanStatus`，确认或添加：

```javascript
getDevices: () => axios.get(`${API_BASE}/devices`),
```

**Step 2: 修改 ScanPage.jsx 添加状态**

在 state 声明部分添加：

```javascript
const [lastScanAt, setLastScanAt] = useState(null);
```

**Step 3: 添加加载已有结果的 useEffect**

在现有 useEffect 后添加：

```javascript
// 加载已有扫描结果
useEffect(() => {
  const loadDevices = async () => {
    try {
      const response = await scanAPI.getDevices();
      if (response.data.success) {
        setDevices(response.data.devices);
        setFilteredDevices(response.data.devices);
        setLastScanAt(response.data.lastScanAt);
      }
    } catch (error) {
      console.error('加载设备列表失败:', error);
    }
  };
  loadDevices();
}, []);
```

**Step 4: 修改扫描完成时更新 lastScanAt**

在轮询扫描状态的 useEffect 中，`setIsScanning(false)` 后添加：

```javascript
if (!status.is_scanning) {
  setIsScanning(false);
  // 重新获取最后扫描时间
  const devicesRes = await scanAPI.getDevices();
  if (devicesRes.data.success) {
    setLastScanAt(devicesRes.data.lastScanAt);
  }
  if (intervalId) clearInterval(intervalId);
}
```

**Step 5: 添加时间格式化函数**

在组件内添加：

```javascript
const formatLastScanTime = (isoString) => {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);

  if (diffMins < 1) return '刚刚';
  if (diffMins < 60) return `${diffMins}分钟前`;
  if (diffHours < 24) return `${diffHours}小时前`;
  return date.toLocaleDateString('zh-CN');
};
```

**Step 6: 修改工具栏右侧显示**

将 `{filteredDevices.length} 台设备` 改为：

```javascript
<div style={styles.toolbarRight}>
  {lastScanAt && (
    <span style={styles.lastScan}>上次更新: {formatLastScanTime(lastScanAt)}</span>
  )}
  <span style={styles.count}>{filteredDevices.length} 台设备</span>
</div>
```

**Step 7: 添加样式**

在 styles 对象中添加：

```javascript
lastScan: {
  fontSize: '12px',
  color: '#86868B',
  marginRight: '12px',
},
```

**Step 8: 提交**

```bash
git add frontend/src/pages/ScanPage.jsx frontend/src/services/api.js
git commit -m "feat: display last scan time on frontend"
```

---

### Task 4: 测试验证

**Step 1: 重启后端服务**

```bash
cd backend
python app.py
```

**Step 2: 重启前端服务**

```bash
cd frontend
npm run dev
```

**Step 3: 验证功能**
1. 登录系统
2. 查看是否显示"上次更新"时间（首次应为空或显示旧时间）
3. 点击扫描，等待完成
4. 刷新页面，确认结果保留且显示更新时间
5. 检查数据库文件是否创建了 scan_results 和 scan_sessions 表

**Step 4: 最终提交**

```bash
git add -A
git commit -m "feat: complete shared scan results feature"
```
