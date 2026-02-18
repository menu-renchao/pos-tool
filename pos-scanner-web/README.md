# POS Scanner Web - 设备管理平台

MenuSifu POS 设备扫描与管理平台

## 功能特性

- POS 设备自动扫描与发现
- 移动设备管理（图片、占用状态）
- 用户认证与权限管理
- 设备占用状态追踪

## 快速部署

### 方式一：Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone <repo-url>
cd pos-scanner-web

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 设置 SECRET_KEY 和 JWT_SECRET_KEY

# 3. 一键部署
./deploy.sh docker

# 访问: http://localhost
```

### 方式二：本地部署

**后端：**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

**前端：**
```bash
cd frontend
npm install
npm run dev
```

访问: http://localhost:3000

### 方式三：一键脚本

```bash
./deploy.sh local   # 本地部署
./deploy.sh docker  # Docker部署
./deploy.sh stop    # 停止服务
./deploy.sh logs    # 查看日志
```

## 默认账号

- 用户名：`admin`
- 密码：`admin123`

> 首次登录后请立即修改密码！

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| SECRET_KEY | Flask 密钥 | *必须修改* |
| JWT_SECRET_KEY | JWT 密钥 | *必须修改* |
| CORS_ORIGINS | 允许的跨域来源 | localhost:3000 |

## 项目结构

```
pos-scanner-web/
├── backend/           # Flask 后端
│   ├── app.py        # 主应用
│   ├── config.py     # 配置
│   ├── models/       # 数据模型
│   ├── routes/       # API 路由
│   └── uploads/      # 上传文件
├── frontend/          # React 前端
│   ├── src/          # 源代码
│   └── package.json  # 依赖
├── docker-compose.yml # Docker 编排
└── deploy.sh         # 部署脚本
```

## 技术栈

- **后端**: Flask, Flask-JWT-Extended, SQLAlchemy
- **前端**: React, Vite
- **部署**: Docker, Nginx
