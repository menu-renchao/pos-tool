# Claude 项目说明

## 语言设置

**所有对话和交流均使用中文（简体）。**

## 项目概述

这是一个 POS 设备扫描管理系统，包含：

- **前端**: React + Vite + Ant Design
- **后端**: Python Flask (原有) / Go Gin (重构中)
- **数据库**: SQLite

## 目录结构

```
pos-scanner-web/
├── frontend/          # React 前端
├── backend/           # Python Flask 后端
├── backend-go/        # Go Gin 后端（重构版本）
└── docs/              # 项目文档
```

## 开发说明

- 默认管理员账号: `admin` / `admin123`
- 前端开发端口: 3000
- 后端 API 端口: 5000
