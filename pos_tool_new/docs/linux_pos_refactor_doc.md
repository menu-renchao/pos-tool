# Linux POS 模块重构技术文档

## 目标
将现有的 PyQt6 桌面应用程序重构为 Go + SQLite + React 的 Web 应用。

---

## 一、现有系统架构分析

### 1.1 文件结构
```
linux_pos/
├── __init__.py              # 模块初始化
├── linux_service.py         # 核心业务服务层 (856行)
├── linux_window.py          # PyQt6 UI组件 (1307行)
└── tail_log_window.py       # 实时日志窗口 (400行)

work_threads.py              # 多线程工作线程 (916行)
backend.py                   # 基础后端类
base_tab.py                  # UI基础组件
```

### 1.2 技术栈对比

| 层次 | 当前技术 | 目标技术 |
|------|----------|----------|
| 前端 | PyQt6 | React + TypeScript |
| 后端 | Python | Go (Gin/Echo) |
| 数据存储 | 内存/文件 | SQLite |
| 通信 | Qt Signals | RESTful API + WebSocket |
| SSH | Paramiko | golang.org/x/crypto/ssh |

---

## 二、功能模块清单

### 2.1 核心功能矩阵

| 功能模块 | 方法名 | 描述 | API设计 |
|----------|--------|------|---------|
| SSH连接测试 | `test_ssh()` | 测试SSH连接是否成功 | `POST /api/ssh/test` |
| 停止POS | `stop_pos_linux()` | 停止远程POS服务 | `POST /api/pos/stop` |
| 启动POS | `start_pos_linux()` | 启动远程POS服务 | `POST /api/pos/start` |
| 重启POS | `restart_pos_linux()` | 重启远程POS服务 | `POST /api/pos/restart` |
| 替换WAR包 | `replace_war_linux()` | 上传并替换远程WAR包 | `POST /api/war/replace` |
| 本地MD5 | `on_check_local_md5()` | 计算本地文件MD5 | `POST /api/file/local-md5` |
| 远程MD5 | `get_file_md5()` | 获取远程文件MD5 | `POST /api/file/remote-md5` |
| 扫描升级包 | `scan_upgrade_packages()` | 扫描远程升级包目录 | `GET /api/upgrade/packages` |
| 上传升级包 | `upload_and_extract_package()` | 上传并解压升级包 | `POST /api/upgrade/upload` |
| 执行升级 | `upload_and_execute_upgrade()` | 执行升级脚本 | `POST /api/upgrade/execute` |
| 重启Tomcat | `restart_tomcat()` | 重启Tomcat服务 | `POST /api/tomcat/restart` |
| 数据备份 | `backup_data()` | 执行数据备份 | `POST /api/backup/create` |
| 数据恢复 | `restore_data()` | 恢复备份数据 | `POST /api/backup/restore` |
| 列出备份 | `list_backup_items()` | 列出可用备份项 | `GET /api/backup/list` |
| 扫描日志 | `scan_remote_logs()` | 扫描远程日志文件 | `GET /api/logs/scan` |
| 下载日志 | `download_remote_logs()` | 下载日志文件 | `GET /api/logs/download` |
| 实时日志 | `stream_remote_log_tail()` | 实时日志流 | `WebSocket /ws/logs/tail` |
| 获取应用版本 | `get_app_version()` | 获取POS应用版本 | `GET /api/version/app` |
| 获取CDH版本 | `get_clouddatahub_version()` | 获取CloudDataHub版本 | `GET /api/version/clouddatahub` |
| 修改配置文件 | `modify_remote_files()` | 批量修改远程配置 | `POST /api/config/modify` |
| 一键升级(WAR) | `pipeline_package_upgrade()` | 完整升级流程(WAR) | `POST /api/pipeline/war-upgrade` |
| 一键升级(包) | `pipeline_package_upgrade()` | 完整升级流程(包) | `POST /api/pipeline/package-upgrade` |

---

## 三、数据库设计 (SQLite)

### 3.1 ER图

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   ssh_configs   │     │   operations    │     │   backup_items  │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │     │ id (PK)         │
│ name            │────▶│ ssh_config_id   │     │ host            │
│ host            │     │ type            │     │ item_name       │
│ username        │     │ status          │     │ is_zip          │
│ password        │     │ start_time      │     │ created_at      │
│ created_at      │     │ end_time        │     │ size            │
│ updated_at      │     │ error_message   │     └─────────────────┘
│ is_default      │     │ progress        │
└─────────────────┘     │ env             │
                        └─────────────────┘

┌─────────────────┐     ┌─────────────────┐
│   file_configs  │     │   operation_logs│
├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │
│ name            │     │ operation_id    │
│ file_path       │     │ level           │
│ replacements    │     │ message         │
│ enabled         │     │ timestamp       │
│ env_type        │     └─────────────────┘
└─────────────────┘
```

### 3.2 表结构定义

```sql
-- SSH连接配置表
CREATE TABLE ssh_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    host VARCHAR(50) NOT NULL,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_default BOOLEAN DEFAULT 0
);

-- 操作记录表
CREATE TABLE operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ssh_config_id INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL,  -- restart_pos, replace_war, backup, restore, etc.
    status VARCHAR(20) NOT NULL,  -- pending, running, success, failed
    start_time DATETIME,
    end_time DATETIME,
    error_message TEXT,
    progress INTEGER DEFAULT 0,
    env VARCHAR(10),  -- QA, PROD, DEV
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ssh_config_id) REFERENCES ssh_configs(id)
);

-- 操作日志表
CREATE TABLE operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id INTEGER NOT NULL,
    level VARCHAR(10) NOT NULL,  -- info, warning, error, success
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (operation_id) REFERENCES operations(id)
);

-- 备份项记录表
CREATE TABLE backup_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host VARCHAR(50) NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    is_zip BOOLEAN NOT NULL,
    size INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 文件配置表（用于配置文件修改）
CREATE TABLE file_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    replacements TEXT NOT NULL,  -- JSON格式存储替换规则
    enabled BOOLEAN DEFAULT 1,
    env_type VARCHAR(10),  -- QA, PROD, DEV, ALL
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_operations_status ON operations(status);
CREATE INDEX idx_operations_type ON operations(type);
CREATE INDEX idx_operation_logs_operation ON operation_logs(operation_id);
CREATE INDEX idx_backup_items_host ON backup_items(host);
```

---

## 四、Go 后端架构设计

### 4.1 项目结构

```
backend-go/
├── cmd/
│   └── server/
│       └── main.go              # 应用入口
├── internal/
│   ├── config/
│   │   └── config.go            # 配置管理
│   ├── handler/
│   │   ├── ssh.go               # SSH相关API
│   │   ├── pos.go               # POS操作API
│   │   ├── war.go               # WAR包管理API
│   │   ├── backup.go            # 备份恢复API
│   │   ├── log.go               # 日志管理API
│   │   ├── config.go            # 配置文件API
│   │   ├── version.go           # 版本查询API
│   │   └── pipeline.go          # 流水线API
│   ├── service/
│   │   ├── ssh_client.go        # SSH客户端服务
│   │   ├── pos_service.go       # POS服务
│   │   ├── file_service.go      # 文件操作服务
│   │   ├── backup_service.go    # 备份恢复服务
│   │   └── log_service.go       # 日志服务
│   ├── model/
│   │   ├── ssh_config.go        # SSH配置模型
│   │   ├── operation.go         # 操作模型
│   │   └── backup.go            # 备份模型
│   ├── repository/
│   │   ├── ssh_config_repo.go   # SSH配置仓库
│   │   ├── operation_repo.go    # 操作仓库
│   │   └── backup_repo.go       # 备份仓库
│   └── middleware/
│       ├── cors.go              # CORS中间件
│       └── logger.go            # 日志中间件
├── pkg/
│   ├── ssh/
│   │   ├── client.go            # SSH客户端封装
│   │   ├── sftp.go              # SFTP操作封装
│   │   └── command.go           # 命令执行封装
│   ├── response/
│   │   └── response.go          # 统一响应格式
│   └── validator/
│       └── validator.go         # 参数验证
├── db/
│   ├── migrations/
│   │   └── 001_init.sql         # 数据库迁移
│   └── db.go                    # 数据库连接
├── go.mod
└── go.sum
```

### 4.2 核心接口定义

```go
// internal/service/ssh_client.go
package service

import (
    "context"
    "golang.org/x/crypto/ssh"
)

type SSHClientInterface interface {
    Connect(ctx context.Context, host, username, password string) (*ssh.Client, error)
    ExecuteCommand(ctx context.Context, client *ssh.Client, cmd string) (stdout, stderr string, exitCode int, error)
    UploadFile(ctx context.Context, client *ssh.Client, localPath, remotePath string, progressCallback func(int)) error
    DownloadFile(ctx context.Context, client *ssh.Client, remotePath, localPath string) error
    TestConnection(ctx context.Context, host, username, password string) (bool, error)
}

type SSHClient struct {
    timeout time.Duration
}

func NewSSHClient(timeout time.Duration) *SSHClient {
    return &SSHClient{timeout: timeout}
}
```

```go
// internal/service/pos_service.go
package service

type POSService struct {
    sshClient SSHClientInterface
    repo      repository.OperationRepository
}

type POSOperationRequest struct {
    Host     string `json:"host" binding:"required,ip"`
    Username string `json:"username" binding:"required"`
    Password string `json:"password" binding:"required"`
    Env      string `json:"env" binding:"omitempty,oneof=QA PROD DEV"`
}

func (s *POSService) StopPOS(ctx context.Context, req *POSOperationRequest) (*OperationResult, error)
func (s *POSService) StartPOS(ctx context.Context, req *POSOperationRequest) (*OperationResult, error)
func (s *POSService) RestartPOS(ctx context.Context, req *POSOperationRequest) (*OperationResult, error)
```

### 4.3 API Handler 示例

```go
// internal/handler/pos.go
package handler

import (
    "net/http"
    "github.com/gin-gonic/gin"
)

type POSHandler struct {
    posService *service.POSService
}

func (h *POSHandler) RestartPOS(c *gin.Context) {
    var req service.POSOperationRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, response.Error("参数错误: "+err.Error()))
        return
    }

    result, err := h.posService.RestartPOS(c.Request.Context(), &req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, response.Error(err.Error()))
        return
    }

    c.JSON(http.StatusOK, response.Success(result))
}
```

### 4.4 WebSocket 实时日志

```go
// internal/handler/log.go
package handler

import (
    "github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
    CheckOrigin: func(r *http.Request) bool {
        return true
    },
}

type LogTailRequest struct {
    Host     string `json:"host"`
    Username string `json:"username"`
    Password string `json:"password"`
    FilePath string `json:"filePath"`
}

func (h *LogHandler) TailLog(c *gin.Context) {
    conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
    if err != nil {
        return
    }
    defer conn.Close()

    var req LogTailRequest
    if err := conn.ReadJSON(&req); err != nil {
        return
    }

    // 创建日志流
    logChan := make(chan string, 100)
    stopChan := make(chan struct{})

    go h.logService.StreamRemoteLog(c.Request.Context(), &req, logChan, stopChan)

    for {
        select {
        case line := <-logChan:
            if err := conn.WriteMessage(websocket.TextMessage, []byte(line)); err != nil {
                close(stopChan)
                return
            }
        case <-c.Request.Context().Done():
            close(stopChan)
            return
        }
    }
}
```

---

## 五、React 前端架构设计

### 5.1 项目结构

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── api/
│   │   ├── client.ts           # Axios客户端配置
│   │   ├── ssh.ts              # SSH相关API
│   │   ├── pos.ts              # POS操作API
│   │   ├── backup.ts           # 备份恢复API
│   │   └── log.ts              # 日志API
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Progress.tsx
│   │   │   └── Toast.tsx
│   │   ├── SSHConnectionForm.tsx    # SSH连接表单
│   │   ├── POSControlPanel.tsx      # POS控制面板
│   │   ├── WARUpload.tsx            # WAR包上传组件
│   │   ├── BackupManager.tsx        # 备份管理组件
│   │   ├── LogViewer.tsx            # 日志查看器
│   │   ├── RealTimeLog.tsx          # 实时日志组件
│   │   └── EnvSelector.tsx          # 环境选择器
│   ├── hooks/
│   │   ├── useSSH.ts           # SSH连接Hook
│   │   ├── useOperation.ts     # 操作状态Hook
│   │   ├── useWebSocket.ts     # WebSocket Hook
│   │   └── useToast.ts         # 提示Hook
│   ├── pages/
│   │   ├── Dashboard.tsx       # 仪表盘
│   │   ├── POSManagement.tsx   # POS管理页面
│   │   ├── BackupRestore.tsx   # 备份恢复页面
│   │   └── LogManagement.tsx   # 日志管理页面
│   ├── store/
│   │   ├── index.ts            # Store配置
│   │   ├── sshSlice.ts         # SSH状态
│   │   └── operationSlice.ts   # 操作状态
│   ├── types/
│   │   ├── ssh.ts              # SSH类型定义
│   │   ├── operation.ts        # 操作类型定义
│   │   └── api.ts              # API响应类型
│   ├── utils/
│   │   ├── validation.ts       # 参数验证
│   │   └── formatters.ts       # 格式化工具
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── tsconfig.json
└── vite.config.ts
```

### 5.2 核心组件设计

#### SSH连接表单组件
```tsx
// src/components/SSHConnectionForm.tsx
import React, { useState } from 'react';
import { useSSH } from '../hooks/useSSH';

interface SSHConnectionFormProps {
  onConnected?: (config: SSHConfig) => void;
}

export const SSHConnectionForm: React.FC<SSHConnectionFormProps> = ({ onConnected }) => {
  const [host, setHost] = useState('');
  const [username, setUsername] = useState('menu');
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState<'idle' | 'testing' | 'connected' | 'failed'>('idle');

  const { testConnection } = useSSH();

  const handleTest = async () => {
    setStatus('testing');
    const result = await testConnection({ host, username, password });
    if (result.success) {
      setStatus('connected');
      onConnected?.({ host, username, password });
    } else {
      setStatus('failed');
    }
  };

  return (
    <div className="ssh-form">
      <div className="form-row">
        <label>主机IP:</label>
        <input
          type="text"
          value={host}
          onChange={(e) => setHost(e.target.value)}
          placeholder="192.168.0.100"
        />
      </div>
      {/* ... 其他字段 */}
      <button onClick={handleTest} disabled={status === 'testing'}>
        {status === 'testing' ? '测试中...' : '测试连接'}
      </button>
      <span className={`status ${status}`}>
        {status === 'connected' && '已连接'}
        {status === 'failed' && '连接失败'}
      </span>
    </div>
  );
};
```

#### 实时日志组件
```tsx
// src/components/RealTimeLog.tsx
import React, { useEffect, useRef, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

interface RealTimeLogProps {
  sshConfig: SSHConfig;
  filePath: string;
}

export const RealTimeLog: React.FC<RealTimeLogProps> = ({ sshConfig, filePath }) => {
  const [logs, setLogs] = useState<string[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const logContainerRef = useRef<HTMLDivElement>(null);

  const { isConnected, connect, disconnect, onMessage } = useWebSocket('/ws/logs/tail');

  useEffect(() => {
    connect({
      ...sshConfig,
      filePath
    });

    onMessage((message: string) => {
      if (!isPaused) {
        setLogs(prev => [...prev, message]);
      }
    });

    return () => disconnect();
  }, []);

  useEffect(() => {
    if (!isPaused && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, isPaused]);

  const highlightedLogs = logs.map((log, index) => {
    if (searchTerm && log.includes(searchTerm)) {
      return (
        <div key={index} className="log-line highlight">
          {log}
        </div>
      );
    }
    return <div key={index} className="log-line">{log}</div>;
  });

  return (
    <div className="real-time-log">
      <div className="toolbar">
        <input
          type="text"
          placeholder="搜索..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <button onClick={() => setIsPaused(!isPaused)}>
          {isPaused ? '继续' : '暂停'}
        </button>
        <button onClick={() => setLogs([])}>清空</button>
        <span className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '已连接' : '未连接'}
        </span>
      </div>
      <div className="log-container" ref={logContainerRef}>
        {highlightedLogs}
      </div>
    </div>
  );
};
```

### 5.3 API 客户端设计

```typescript
// src/api/client.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.message || '请求失败';
    return Promise.reject(new Error(message));
  }
);

export default apiClient;
```

```typescript
// src/api/pos.ts
import apiClient from './client';
import { OperationResult, POSOperationRequest } from '../types/operation';

export const posApi = {
  testSSH: (data: SSHConfig) =>
    apiClient.post<{ success: boolean; message: string }>('/ssh/test', data),

  stopPOS: (data: POSOperationRequest) =>
    apiClient.post<OperationResult>('/pos/stop', data),

  startPOS: (data: POSOperationRequest) =>
    apiClient.post<OperationResult>('/pos/start', data),

  restartPOS: (data: POSOperationRequest) =>
    apiClient.post<OperationResult>('/pos/restart', data),

  restartTomcat: (data: POSOperationRequest) =>
    apiClient.post<OperationResult>('/tomcat/restart', data),
};
```

---

## 六、API 接口详细规范

### 6.1 通用响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": { ... },
  "timestamp": 1708425600000
}
```

### 6.2 接口列表

#### SSH 连接测试
```
POST /api/ssh/test
Request:
{
  "host": "192.168.0.100",
  "username": "menu",
  "password": "password123"
}
Response:
{
  "code": 0,
  "message": "连接成功",
  "data": {
    "success": true,
    "latency": 150
  }
}
```

#### 替换 WAR 包
```
POST /api/war/replace
Content-Type: multipart/form-data

Request:
- host: string
- username: string
- password: string
- war_file: File
- skip_md5_check: boolean (可选)

Response:
{
  "code": 0,
  "message": "WAR包替换成功",
  "data": {
    "operationId": "op_123456",
    "localMd5": "abc123...",
    "remoteMd5": "abc123...",
    "fileSize": 228000000
  }
}
```

#### 一键升级 (WAR包)
```
POST /api/pipeline/war-upgrade
Request:
{
  "host": "192.168.0.100",
  "username": "menu",
  "password": "password123",
  "warPath": "/local/path/to/kpos.war",
  "env": "QA",
  "skipMd5Check": false
}

Response (Server-Sent Events):
event: progress
data: {"percent": 20, "stage": "uploading", "message": "正在上传WAR包..."}

event: progress
data: {"percent": 40, "stage": "extracting", "message": "正在解压..."}

event: complete
data: {"success": true, "message": "升级完成"}
```

#### 实时日志 WebSocket
```
WebSocket /ws/logs/tail

Client -> Server:
{
  "type": "subscribe",
  "host": "192.168.0.100",
  "username": "menu",
  "password": "password123",
  "filePath": "/opt/tomcat7/logs/catalina.out"
}

Server -> Client:
{
  "type": "log",
  "content": "2024-02-20 10:00:00 INFO  Starting application...",
  "timestamp": 1708425600000
}

Client -> Server (断开):
{
  "type": "unsubscribe"
}
```

---

## 七、迁移步骤建议

### Phase 1: 基础架构 (1-2周)
1. 搭建 Go 项目骨架
2. 实现 SQLite 数据库初始化
3. 实现基础 SSH 客户端封装
4. 搭建 React 项目骨架
5. 实现基础 UI 组件库

### Phase 2: 核心功能 (2-3周)
1. 实现 SSH 连接测试 API
2. 实现 POS 启动/停止/重启 API
3. 实现前端 SSH 连接表单
4. 实现前端 POS 控制面板

### Phase 3: 文件操作 (2周)
1. 实现 WAR 包上传替换 API
2. 实现文件 MD5 校验 API
3. 实现升级包管理 API
4. 实现前端文件上传组件

### Phase 4: 备份恢复 (1-2周)
1. 实现数据备份 API
2. 实现数据恢复 API
3. 实现备份项列表 API
4. 实现前端备份管理界面

### Phase 5: 日志系统 (1-2周)
1. 实现日志扫描 API
2. 实现日志下载 API
3. 实现 WebSocket 实时日志
4. 实现前端日志查看器

### Phase 6: 流水线与优化 (1-2周)
1. 实现一键升级流水线 API
2. 实现配置文件批量修改
3. 前端界面优化
4. 性能测试与优化

---

## 八、关键技术点

### 8.1 SSH 连接 (Go)
```go
import "golang.org/x/crypto/ssh"

func Connect(host, username, password string) (*ssh.Client, error) {
    config := &ssh.ClientConfig{
        User: username,
        Auth: []ssh.AuthMethod{
            ssh.Password(password),
        },
        HostKeyCallback: ssh.InsecureIgnoreHostKey(),
        Timeout: 10 * time.Second,
    }

    return ssh.Dial("tcp", host+":22", config)
}
```

### 8.2 文件上传进度
```go
type ProgressWriter struct {
    Total      int64
    Current    int64
    Callback   func(percent int)
}

func (pw *ProgressWriter) Write(p []byte) (int, error) {
    n := len(p)
    pw.Current += int64(n)
    percent := int(float64(pw.Current) / float64(pw.Total) * 100)
    pw.Callback(percent)
    return n, nil
}
```

### 8.3 命令执行
```go
func ExecuteCommand(client *ssh.Client, cmd string) (string, string, error) {
    session, err := client.NewSession()
    if err != nil {
        return "", "", err
    }
    defer session.Close()

    var stdout, stderr bytes.Buffer
    session.Stdout = &stdout
    session.Stderr = &stderr

    err = session.Run(cmd)
    return stdout.String(), stderr.String(), err
}
```

---

## 九、安全考虑

1. **密码存储**: SSH密码使用AES加密存储在数据库中
2. **API认证**: 使用JWT Token进行API认证
3. **HTTPS**: 生产环境强制使用HTTPS
4. **输入验证**: 所有输入参数进行严格验证
5. **日志脱敏**: 敏感信息(密码等)不记录到日志

---

## 十、测试策略

### 10.1 单元测试
- SSH客户端连接测试
- 命令执行测试
- 文件操作测试
- API Handler测试

### 10.2 集成测试
- 完整升级流程测试
- 备份恢复流程测试
- WebSocket连接测试

### 10.3 E2E测试
- 使用Playwright进行前端E2E测试
- 模拟完整用户操作流程

---

## 附录：现有代码功能映射表

| 现有Python方法 | Go方法 | React组件 |
|---------------|--------|-----------|
| `LinuxService.test_ssh()` | `(*SSHService).TestConnection()` | `SSHConnectionForm` |
| `LinuxService.stop_pos_linux()` | `(*POSService).Stop()` | `POSControlPanel` |
| `LinuxService.start_pos_linux()` | `(*POSService).Start()` | `POSControlPanel` |
| `LinuxService.restart_pos_linux()` | `(*POSService).Restart()` | `POSControlPanel` |
| `LinuxService.replace_war_linux()` | `(*WARService).Replace()` | `WARUpload` |
| `LinuxService.backup_data()` | `(*BackupService).Create()` | `BackupManager` |
| `LinuxService.restore_data()` | `(*BackupService).Restore()` | `BackupManager` |
| `LinuxService.stream_remote_log_tail()` | `(*LogService).StreamTail()` | `RealTimeLog` |
| `LinuxService.modify_remote_files()` | `(*ConfigService).ModifyBatch()` | `ConfigEditor` |
| `ReplaceWarThreadLinux` | goroutine + channel | - |
| `RemoteTailLogThread` | WebSocket handler | `useWebSocket` hook |
