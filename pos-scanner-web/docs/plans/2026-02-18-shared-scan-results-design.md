# 共享扫描结果功能设计

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:writing-plans to create implementation plan.

**Goal:** 让所有用户共享扫描结果，无需每次进入都重新扫描，显示上次更新时间提示。

**Architecture:** 使用 SQLite 数据库持久化扫描结果，每次扫描替换旧数据并记录时间。用户进入页面自动加载已有结果，可手动刷新。超过24小时的旧数据自动清理。

**Tech Stack:** Flask-SQLAlchemy, SQLite, React

---

## 数据模型

### ScanResult 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| ip | String(50) | 设备IP地址 |
| merchant_id | String(100) | 商户ID |
| name | String(200) | 设备名称 |
| version | String(50) | 版本号 |
| type | String(50) | 设备类型(OS) |
| full_data | Text | 完整JSON数据 |
| scanned_at | DateTime | 扫描时间 |

### ScanSession 表（单行）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键(固定为1) |
| last_scan_at | DateTime | 最后扫描时间 |

---

## 后端改动

### 1. 新增模型 `models/scan_result.py`
- `ScanResult` 类：存储每台设备信息
- `ScanSession` 类：记录扫描会话时间

### 2. 修改 `app.py`
- 扫描完成后：清空旧结果 → 保存新结果到数据库 → 更新 ScanSession
- `/api/devices`：从数据库读取，返回 `{devices, lastScanAt}`
- `init_db()`：清理超过24小时的旧数据

---

## 前端改动

### 修改 `ScanPage.jsx`
- 进入页面时调用 `/api/devices` 加载已有结果
- 工具栏右侧显示"上次更新: XX分钟前"（灰色小字）
- 扫描完成后自动刷新显示

---

## 用户体验流程

1. 用户进入扫描页面 → 自动显示已有结果 + 更新时间
2. 用户点击"扫描"→ 后台执行 → 完成后更新结果和时间
3. 服务器重启 → 检查24小时过期 → 清理旧数据
