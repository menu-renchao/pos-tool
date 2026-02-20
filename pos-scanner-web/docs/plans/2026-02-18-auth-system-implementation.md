# 用户认证系统实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 POS Scanner Web 添加完整的用户认证系统，支持注册（管理员审核）、登录和管理员功能。

**Architecture:** 后端使用 Flask-JWT-Extended + Flask-SQLAlchemy 实现 JWT 认证和用户管理；前端使用 React Context 管理认证状态，react-router-dom 实现路由保护。

**Tech Stack:** Flask-JWT-Extended, Flask-SQLAlchemy, SQLite, react-router-dom, React Context

---

## Phase 1: 后端基础设施

### Task 1: 安装后端依赖

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: 添加新依赖**

在 `backend/requirements.txt` 末尾添加：

```txt
flask-jwt-extended>=4.5.0
flask-sqlalchemy>=3.0.0
```

**Step 2: 安装依赖**

Run: `cd backend && pip install -r requirements.txt`
Expected: Successfully installed flask-jwt-extended flask-sqlalchemy

**Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add JWT and SQLAlchemy dependencies"
```

---

### Task 2: 创建 Flask 扩展初始化模块

**Files:**
- Create: `backend/extensions.py`

**Step 1: 创建扩展模块**

创建 `backend/extensions.py`:

```python
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
jwt = JWTManager()
```

**Step 2: Commit**

```bash
git add backend/extensions.py
git commit -m "feat: add Flask extensions module (db, jwt)"
```

---

### Task 3: 创建用户模型

**Files:**
- Create: `backend/models/__init__.py`
- Create: `backend/models/user.py`

**Step 1: 创建 models 包**

创建 `backend/models/__init__.py`:

```python
from .user import User
```

**Step 2: 创建用户模型**

创建 `backend/models/user.py`:

```python
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.String(20), default='user')
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
```

**Step 3: Commit**

```bash
git add backend/models/
git commit -m "feat: add User model with password hashing"
```

---

### Task 4: 更新配置文件

**Files:**
- Modify: `backend/config.py`

**Step 1: 更新配置**

更新 `backend/config.py`:

```python
import os
from datetime import timedelta


class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000')

    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```

**Step 2: Commit**

```bash
git add backend/config.py
git commit -m "feat: add JWT and SQLAlchemy configuration"
```

---

### Task 5: 更新主应用入口

**Files:**
- Modify: `backend/app.py`

**Step 1: 更新 app.py**

更新 `backend/app.py`，在文件开头添加导入并初始化扩展：

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
from scan_service import ScanPosService
import threading
from concurrent.futures import ThreadPoolExecutor
import json
from config import Config
import concurrent.futures

# 新增导入
from extensions import db, jwt
from models import User
from routes.auth import auth_bp
from routes.admin import admin_bp

app = Flask(__name__)
app.config.from_object(Config)

# 初始化扩展
db.init_app(app)
jwt.init_app(app)

CORS(app, origins=app.config['CORS_ORIGINS'])

# ... 保留现有的扫描状态和路由代码 ...

# 注册认证蓝图
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/api/admin')


# 在 app.run 之前添加数据库初始化
@app.before_request
def create_tables():
    if not hasattr(app, '_db_initialized'):
        db.create_all()
        # 创建默认管理员
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@example.com', role='admin', status='approved')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
        app._db_initialized = True


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
```

**Step 2: Commit**

```bash
git add backend/app.py
git commit -m "feat: integrate db and jwt extensions, register auth blueprints"
```

---

## Phase 2: 认证路由

### Task 6: 创建认证蓝图

**Files:**
- Create: `backend/routes/__init__.py`
- Create: `backend/routes/auth.py`

**Step 1: 创建 routes 包**

创建 `backend/routes/__init__.py`:

```python
from .auth import auth_bp
from .admin import admin_bp
```

**Step 2: 创建认证路由**

创建 `backend/routes/auth.py`:

```python
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from extensions import db
from models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()

    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip()

    # 验证输入
    if not username or not password or not email:
        return jsonify({'success': False, 'error': '所有字段都必填'}), 400

    if len(username) < 3:
        return jsonify({'success': False, 'error': '用户名至少3个字符'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'error': '密码至少6个字符'}), 400

    # 检查用户名是否存在
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'error': '用户名已存在'}), 400

    # 检查邮箱是否存在
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': '邮箱已被注册'}), 400

    # 创建用户
    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '注册成功，请等待管理员审核'
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码必填'}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({'success': False, 'error': '用户名或密码错误'}), 401

    if user.status != 'approved':
        return jsonify({'success': False, 'error': '账户尚未通过审核'}), 403

    # 创建 Token
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)

    return jsonify({
        'success': True,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    })


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """用户登出"""
    # JWT 无状态，客户端删除 Token 即可
    return jsonify({'success': True, 'message': '登出成功'})


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    """获取当前用户信息"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    return jsonify({'success': True, 'user': user.to_dict()})


@auth_bp.route('/password', methods=['PUT'])
@jwt_required()
def change_password():
    """修改密码"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'success': False, 'error': '旧密码和新密码必填'}), 400

    if not user.check_password(old_password):
        return jsonify({'success': False, 'error': '旧密码错误'}), 400

    if len(new_password) < 6:
        return jsonify({'success': False, 'error': '新密码至少6个字符'}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({'success': True, 'message': '密码修改成功'})
```

**Step 3: Commit**

```bash
git add backend/routes/
git commit -m "feat: add authentication routes (register, login, profile, password)"
```

---

### Task 7: 创建管理员路由

**Files:**
- Create: `backend/routes/admin.py`

**Step 1: 创建管理员路由**

创建 `backend/routes/admin.py`:

```python
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import User
import functools

admin_bp = Blueprint('admin', __name__)


def admin_required(fn):
    """管理员权限装饰器"""
    @functools.wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user or user.role != 'admin':
            return jsonify({'success': False, 'error': '需要管理员权限'}), 403

        return fn(*args, **kwargs)
    return wrapper


@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    """获取用户列表"""
    status = request.args.get('status')  # pending, approved, rejected, all

    query = User.query
    if status and status != 'all':
        query = query.filter_by(status=status)

    users = query.order_by(User.created_at.desc()).all()
    return jsonify({
        'success': True,
        'users': [u.to_dict() for u in users]
    })


@admin_bp.route('/users/<int:user_id>/approve', methods=['PUT'])
@admin_required
def approve_user(user_id):
    """审核通过用户"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    if user.status == 'approved':
        return jsonify({'success': False, 'error': '用户已通过审核'}), 400

    user.status = 'approved'
    db.session.commit()

    return jsonify({'success': True, 'message': '审核通过'})


@admin_bp.route('/users/<int:user_id>/reject', methods=['PUT'])
@admin_required
def reject_user(user_id):
    """审核拒绝用户"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    if user.status == 'rejected':
        return jsonify({'success': False, 'error': '用户已被拒绝'}), 400

    user.status = 'rejected'
    db.session.commit()

    return jsonify({'success': True, 'message': '已拒绝'})


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['PUT'])
@admin_required
def reset_user_password(user_id):
    """重置用户密码"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    data = request.get_json()
    new_password = data.get('new_password', '')

    if not new_password or len(new_password) < 6:
        return jsonify({'success': False, 'error': '密码至少6个字符'}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({'success': True, 'message': '密码已重置'})


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """删除用户"""
    current_user_id = get_jwt_identity()

    if user_id == current_user_id:
        return jsonify({'success': False, 'error': '不能删除自己的账户'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({'success': True, 'message': '用户已删除'})
```

**Step 2: Commit**

```bash
git add backend/routes/admin.py
git commit -m "feat: add admin routes (user management, approval)"
```

---

## Phase 3: 前端基础设施

### Task 8: 安装前端依赖

**Files:**
- Modify: `frontend/package.json`

**Step 1: 安装 react-router-dom**

Run: `cd frontend && npm install react-router-dom`
Expected: added react-router-dom to package.json

**Step 2: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: add react-router-dom dependency"
```

---

### Task 9: 创建认证服务

**Files:**
- Create: `frontend/src/services/authService.js`

**Step 1: 创建认证 API 服务**

创建 `frontend/src/services/authService.js`:

```javascript
import axios from 'axios';

const API_BASE = '/api/auth';
const ADMIN_BASE = '/api/admin';

// 创建带认证的 axios 实例
const createAuthAxios = () => {
  const instance = axios.create();
  const token = localStorage.getItem('access_token');
  if (token) {
    instance.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }
  return instance;
};

// 认证 API
export const authService = {
  register: async (username, password, email) => {
    const response = await axios.post(`${API_BASE}/register`, {
      username,
      password,
      email
    });
    return response.data;
  },

  login: async (username, password) => {
    const response = await axios.post(`${API_BASE}/login`, {
      username,
      password
    });
    if (response.data.success) {
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('refresh_token', response.data.refresh_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }
    return response.data;
  },

  logout: async () => {
    try {
      const axios = createAuthAxios();
      await axios.post(`${API_BASE}/logout`);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
    }
  },

  getProfile: async () => {
    const axios = createAuthAxios();
    const response = await axios.get(`${API_BASE}/profile`);
    return response.data;
  },

  changePassword: async (oldPassword, newPassword) => {
    const axios = createAuthAxios();
    const response = await axios.put(`${API_BASE}/password`, {
      old_password: oldPassword,
      new_password: newPassword
    });
    return response.data;
  },

  getCurrentUser: () => {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  isAuthenticated: () => {
    return !!localStorage.getItem('access_token');
  }
};

// 管理员 API
export const adminService = {
  getUsers: async (status = 'all') => {
    const axios = createAuthAxios();
    const response = await axios.get(`${ADMIN_BASE}/users?status=${status}`);
    return response.data;
  },

  approveUser: async (userId) => {
    const axios = createAuthAxios();
    const response = await axios.put(`${ADMIN_BASE}/users/${userId}/approve`);
    return response.data;
  },

  rejectUser: async (userId) => {
    const axios = createAuthAxios();
    const response = await axios.put(`${ADMIN_BASE}/users/${userId}/reject`);
    return response.data;
  },

  resetUserPassword: async (userId, newPassword) => {
    const axios = createAuthAxios();
    const response = await axios.put(`${ADMIN_BASE}/users/${userId}/reset-password`, {
      new_password: newPassword
    });
    return response.data;
  },

  deleteUser: async (userId) => {
    const axios = createAuthAxios();
    const response = await axios.delete(`${ADMIN_BASE}/users/${userId}`);
    return response.data;
  }
};
```

**Step 2: Commit**

```bash
git add frontend/src/services/authService.js
git commit -m "feat: add authentication service (API calls)"
```

---

### Task 10: 创建认证上下文

**Files:**
- Create: `frontend/src/contexts/AuthContext.jsx`

**Step 1: 创建认证 Context**

创建 `frontend/src/contexts/AuthContext.jsx`:

```javascript
import React, { createContext, useState, useContext, useEffect } from 'react';
import { authService } from '../services/authService';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 初始化时检查是否有已登录用户
    const currentUser = authService.getCurrentUser();
    if (currentUser) {
      setUser(currentUser);
    }
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    const result = await authService.login(username, password);
    if (result.success) {
      setUser(result.user);
    }
    return result;
  };

  const logout = async () => {
    await authService.logout();
    setUser(null);
  };

  const isAdmin = () => {
    return user?.role === 'admin';
  };

  const value = {
    user,
    loading,
    login,
    logout,
    isAdmin,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
```

**Step 2: Commit**

```bash
git add frontend/src/contexts/AuthContext.jsx
git commit -m "feat: add AuthContext for state management"
```

---

### Task 11: 创建路由守卫组件

**Files:**
- Create: `frontend/src/components/auth/PrivateRoute.jsx`

**Step 1: 创建路由守卫**

创建 `frontend/src/components/auth/PrivateRoute.jsx`:

```javascript
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

export const PrivateRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '50px' }}>加载中...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

export const AdminRoute = ({ children }) => {
  const { isAuthenticated, isAdmin, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '50px' }}>加载中...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (!isAdmin()) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <h2>403 - 权限不足</h2>
        <p>您没有权限访问此页面</p>
      </div>
    );
  }

  return children;
};

export const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '50px' }}>加载中...</div>;
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return children;
};
```

**Step 2: Commit**

```bash
git add frontend/src/components/auth/PrivateRoute.jsx
git commit -m "feat: add route guards (PrivateRoute, AdminRoute)"
```

---

## Phase 4: 前端页面

### Task 12: 创建登录页面

**Files:**
- Create: `frontend/src/pages/LoginPage.jsx`

**Step 1: 创建登录页面**

创建 `frontend/src/pages/LoginPage.jsx`:

```javascript
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await login(username, password);
      if (result.success) {
        navigate('/');
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError('登录失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.form}>
        <h2 style={styles.title}>Menusifu设备管理平台</h2>
        <form onSubmit={handleSubmit}>
          <div style={styles.field}>
            <label style={styles.label}>用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={styles.input}
              required
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={styles.input}
              required
            />
          </div>
          {error && <div style={styles.error}>{error}</div>}
          <button type="submit" style={styles.button} disabled={loading}>
            {loading ? '登录中...' : '登录'}
          </button>
        </form>
        <div style={styles.link}>
          还没有账户？<Link to="/register">注册</Link>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#f5f5f5'
  },
  form: {
    backgroundColor: 'white',
    padding: '40px',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
    width: '100%',
    maxWidth: '400px'
  },
  title: {
    textAlign: 'center',
    marginBottom: '30px',
    color: '#333'
  },
  field: {
    marginBottom: '20px'
  },
  label: {
    display: 'block',
    marginBottom: '8px',
    fontWeight: '500'
  },
  input: {
    width: '100%',
    padding: '12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '14px',
    boxSizing: 'border-box'
  },
  button: {
    width: '100%',
    padding: '12px',
    backgroundColor: '#1890ff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '16px',
    cursor: 'pointer',
    marginTop: '10px'
  },
  error: {
    color: '#ff4d4f',
    marginBottom: '15px',
    textAlign: 'center'
  },
  link: {
    textAlign: 'center',
    marginTop: '20px',
    color: '#666'
  }
};

export default LoginPage;
```

**Step 2: Commit**

```bash
git add frontend/src/pages/LoginPage.jsx
git commit -m "feat: add login page"
```

---

### Task 13: 创建注册页面

**Files:**
- Create: `frontend/src/pages/RegisterPage.jsx`

**Step 1: 创建注册页面**

创建 `frontend/src/pages/RegisterPage.jsx`:

```javascript
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authService } from '../services/authService';

const RegisterPage = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }

    setLoading(true);

    try {
      const result = await authService.register(username, password, email);
      if (result.success) {
        setSuccess(true);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError('注册失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div style={styles.container}>
        <div style={styles.form}>
          <h2 style={styles.title}>注册成功</h2>
          <p style={styles.successText}>您的注册申请已提交，请等待管理员审核。</p>
          <button onClick={() => navigate('/login')} style={styles.button}>
            返回登录
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.form}>
        <h2 style={styles.title}>注册账户</h2>
        <form onSubmit={handleSubmit}>
          <div style={styles.field}>
            <label style={styles.label}>用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={styles.input}
              required
              minLength={3}
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>邮箱</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={styles.input}
              required
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={styles.input}
              required
              minLength={6}
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>确认密码</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              style={styles.input}
              required
            />
          </div>
          {error && <div style={styles.error}>{error}</div>}
          <button type="submit" style={styles.button} disabled={loading}>
            {loading ? '注册中...' : '注册'}
          </button>
        </form>
        <div style={styles.link}>
          已有账户？<Link to="/login">登录</Link>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#f5f5f5'
  },
  form: {
    backgroundColor: 'white',
    padding: '40px',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
    width: '100%',
    maxWidth: '400px'
  },
  title: {
    textAlign: 'center',
    marginBottom: '30px',
    color: '#333'
  },
  field: {
    marginBottom: '20px'
  },
  label: {
    display: 'block',
    marginBottom: '8px',
    fontWeight: '500'
  },
  input: {
    width: '100%',
    padding: '12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '14px',
    boxSizing: 'border-box'
  },
  button: {
    width: '100%',
    padding: '12px',
    backgroundColor: '#1890ff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '16px',
    cursor: 'pointer',
    marginTop: '10px'
  },
  error: {
    color: '#ff4d4f',
    marginBottom: '15px',
    textAlign: 'center'
  },
  successText: {
    textAlign: 'center',
    color: '#52c41a',
    marginBottom: '20px'
  },
  link: {
    textAlign: 'center',
    marginTop: '20px',
    color: '#666'
  }
};

export default RegisterPage;
```

**Step 2: Commit**

```bash
git add frontend/src/pages/RegisterPage.jsx
git commit -m "feat: add register page"
```

---

### Task 14: 创建用户管理页面

**Files:**
- Create: `frontend/src/pages/AdminUsersPage.jsx`

**Step 1: 创建用户管理页面**

创建 `frontend/src/pages/AdminUsersPage.jsx`:

```javascript
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { adminService } from '../services/authService';

const AdminUsersPage = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [error, setError] = useState('');

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const result = await adminService.getUsers(statusFilter);
      if (result.success) {
        setUsers(result.users);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError('获取用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [statusFilter]);

  const handleApprove = async (userId) => {
    try {
      const result = await adminService.approveUser(userId);
      if (result.success) {
        fetchUsers();
      } else {
        alert(result.error);
      }
    } catch (err) {
      alert('操作失败');
    }
  };

  const handleReject = async (userId) => {
    if (!window.confirm('确定要拒绝此用户吗？')) return;
    try {
      const result = await adminService.rejectUser(userId);
      if (result.success) {
        fetchUsers();
      } else {
        alert(result.error);
      }
    } catch (err) {
      alert('操作失败');
    }
  };

  const handleResetPassword = async (userId) => {
    const newPassword = prompt('请输入新密码（至少6位）：');
    if (!newPassword || newPassword.length < 6) {
      alert('密码长度不足');
      return;
    }
    try {
      const result = await adminService.resetUserPassword(userId, newPassword);
      if (result.success) {
        alert('密码已重置');
      } else {
        alert(result.error);
      }
    } catch (err) {
      alert('操作失败');
    }
  };

  const handleDelete = async (userId) => {
    if (!window.confirm('确定要删除此用户吗？此操作不可恢复。')) return;
    try {
      const result = await adminService.deleteUser(userId);
      if (result.success) {
        fetchUsers();
      } else {
        alert(result.error);
      }
    } catch (err) {
      alert('操作失败');
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending: { backgroundColor: '#faad14', color: 'white' },
      approved: { backgroundColor: '#52c41a', color: 'white' },
      rejected: { backgroundColor: '#ff4d4f', color: 'white' }
    };
    const labels = {
      pending: '待审核',
      approved: '已通过',
      rejected: '已拒绝'
    };
    return (
      <span style={{ ...styles[status], padding: '2px 8px', borderRadius: '4px', fontSize: '12px' }}>
        {labels[status]}
      </span>
    );
  };

  if (loading) {
    return <div style={styles.container}>加载中...</div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1>用户管理</h1>
        <Link to="/" style={styles.backLink}>返回主页</Link>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      <div style={styles.filter}>
        <label>筛选状态：</label>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="all">全部</option>
          <option value="pending">待审核</option>
          <option value="approved">已通过</option>
          <option value="rejected">已拒绝</option>
        </select>
      </div>

      <table style={styles.table}>
        <thead>
          <tr>
            <th>ID</th>
            <th>用户名</th>
            <th>邮箱</th>
            <th>角色</th>
            <th>状态</th>
            <th>注册时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <td>{user.id}</td>
              <td>{user.username}</td>
              <td>{user.email}</td>
              <td>{user.role === 'admin' ? '管理员' : '用户'}</td>
              <td>{getStatusBadge(user.status)}</td>
              <td>{new Date(user.created_at).toLocaleString()}</td>
              <td>
                {user.status === 'pending' && (
                  <>
                    <button onClick={() => handleApprove(user.id)} style={styles.btnApprove}>通过</button>
                    <button onClick={() => handleReject(user.id)} style={styles.btnReject}>拒绝</button>
                  </>
                )}
                {user.role !== 'admin' && (
                  <>
                    <button onClick={() => handleResetPassword(user.id)} style={styles.btnReset}>重置密码</button>
                    <button onClick={() => handleDelete(user.id)} style={styles.btnDelete}>删除</button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {users.length === 0 && <div style={styles.empty}>暂无用户数据</div>}
    </div>
  );
};

const styles = {
  container: {
    padding: '20px',
    maxWidth: '1200px',
    margin: '0 auto'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px'
  },
  backLink: {
    color: '#1890ff',
    textDecoration: 'none'
  },
  error: {
    color: '#ff4d4f',
    padding: '10px',
    backgroundColor: '#fff2f0',
    borderRadius: '4px',
    marginBottom: '20px'
  },
  filter: {
    marginBottom: '20px'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    backgroundColor: 'white',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
  },
  empty: {
    textAlign: 'center',
    padding: '40px',
    color: '#999'
  },
  btnApprove: {
    padding: '4px 8px',
    backgroundColor: '#52c41a',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    marginRight: '5px'
  },
  btnReject: {
    padding: '4px 8px',
    backgroundColor: '#ff4d4f',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    marginRight: '5px'
  },
  btnReset: {
    padding: '4px 8px',
    backgroundColor: '#1890ff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    marginRight: '5px'
  },
  btnDelete: {
    padding: '4px 8px',
    backgroundColor: '#ff4d4f',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer'
  }
};

export default AdminUsersPage;
```

**Step 2: Commit**

```bash
git add frontend/src/pages/AdminUsersPage.jsx
git commit -m "feat: add admin users management page"
```

---

### Task 15: 更新 App.jsx 添加路由

**Files:**
- Modify: `frontend/src/App.jsx`

**Step 1: 更新 App.jsx**

更新 `frontend/src/App.jsx`，添加路由和导航栏：

```javascript
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { PrivateRoute, AdminRoute, PublicRoute } from './components/auth/PrivateRoute';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import AdminUsersPage from './pages/AdminUsersPage';
import ScanPage from './pages/ScanPage';
import './App.css';

// 导航栏组件
const Navbar = () => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <nav style={navStyles.nav}>
      <div style={navStyles.brand}>Menusifu设备管理平台</div>
      <div style={navStyles.links}>
        <Link to="/" style={navStyles.link}>扫描</Link>
        {isAdmin() && (
          <Link to="/admin/users" style={navStyles.link}>用户管理</Link>
        )}
        <span style={navStyles.user}>欢迎，{user?.username}</span>
        <button onClick={handleLogout} style={navStyles.logoutBtn}>登出</button>
      </div>
    </nav>
  );
};

// 主应用布局
const MainLayout = ({ children }) => {
  return (
    <>
      <Navbar />
      <main style={{ padding: '20px' }}>
        {children}
      </main>
    </>
  );
};

// 原扫描页面内容（从原 App.jsx 移动过来）
const ScanPageContent = () => {
  // 这里放置原来的扫描页面逻辑
  // 由于原文件较大，这里只展示结构
  return <div>扫描页面内容</div>;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* 公开路由 */}
          <Route path="/login" element={
            <PublicRoute><LoginPage /></PublicRoute>
          } />
          <Route path="/register" element={
            <PublicRoute><RegisterPage /></PublicRoute>
          } />

          {/* 受保护路由 */}
          <Route path="/" element={
            <PrivateRoute>
              <MainLayout>
                <ScanPage />
              </MainLayout>
            </PrivateRoute>
          } />

          {/* 管理员路由 */}
          <Route path="/admin/users" element={
            <AdminRoute>
              <MainLayout>
                <AdminUsersPage />
              </MainLayout>
            </AdminRoute>
          } />

          {/* 默认重定向 */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

const navStyles = {
  nav: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0 20px',
    height: '60px',
    backgroundColor: '#1890ff',
    color: 'white'
  },
  brand: {
    fontSize: '18px',
    fontWeight: 'bold'
  },
  links: {
    display: 'flex',
    alignItems: 'center',
    gap: '20px'
  },
  link: {
    color: 'white',
    textDecoration: 'none'
  },
  user: {
    fontSize: '14px'
  },
  logoutBtn: {
    padding: '6px 12px',
    backgroundColor: 'transparent',
    color: 'white',
    border: '1px solid white',
    borderRadius: '4px',
    cursor: 'pointer'
  }
};

export default App;
```

**Step 2: 创建 ScanPage.jsx**

将原 App.jsx 中的扫描逻辑移动到 `frontend/src/pages/ScanPage.jsx`（保留原有功能）

**Step 3: Commit**

```bash
git add frontend/src/App.jsx frontend/src/pages/ScanPage.jsx
git commit -m "feat: integrate authentication with routing"
```

---

## Phase 5: 验证和部署

### Task 16: 测试后端 API

**Step 1: 启动后端服务**

Run: `cd backend && python app.py`
Expected: Running on http://0.0.0.0:5000

**Step 2: 测试注册 API**

Run: `curl -X POST http://localhost:5000/api/auth/register -H "Content-Type: application/json" -d '{"username":"test","password":"123456","email":"test@test.com"}'`
Expected: {"success": true, "message": "注册成功，请等待管理员审核"}

**Step 3: 测试管理员登录**

Run: `curl -X POST http://localhost:5000/api/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}'`
Expected: {"success": true, "access_token": "...", ...}

---

### Task 17: 测试前端

**Step 1: 启动前端服务**

Run: `cd frontend && npm run dev`
Expected: Local: http://localhost:3000

**Step 2: 手动测试流程**
1. 访问 http://localhost:3000 → 应重定向到登录页
2. 点击注册 → 填写表单 → 提交 → 显示等待审核
3. 使用 admin/admin123 登录
4. 访问用户管理页面 → 审核通过新用户
5. 登出 → 使用新用户登录

---

## 完成检查清单

- [ ] 后端依赖安装完成
- [ ] 数据库模型创建完成
- [ ] 认证 API 正常工作
- [ ] 管理员 API 正常工作
- [ ] 前端路由保护生效
- [ ] 登录/注册流程正常
- [ ] 管理员审核功能正常
- [ ] 所有代码已提交
