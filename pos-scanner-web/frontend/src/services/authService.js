import axios from 'axios';

const API_BASE = '/api/auth';
const ADMIN_BASE = '/api/admin';

// 创建带认证的 axios 实例
const createAuthAxios = () => {
  const token = localStorage.getItem('access_token');
  return axios.create({
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  });
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
      const authAxios = createAuthAxios();
      await authAxios.post(`${API_BASE}/logout`);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
    }
  },

  getProfile: async () => {
    const authAxios = createAuthAxios();
    const response = await authAxios.get(`${API_BASE}/profile`);
    return response.data;
  },

  changePassword: async (oldPassword, newPassword) => {
    const authAxios = createAuthAxios();
    const response = await authAxios.put(`${API_BASE}/password`, {
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
    const authAxios = createAuthAxios();
    const response = await authAxios.get(`${ADMIN_BASE}/users?status=${status}`);
    return response.data;
  },

  approveUser: async (userId) => {
    const authAxios = createAuthAxios();
    const response = await authAxios.put(`${ADMIN_BASE}/users/${userId}/approve`);
    return response.data;
  },

  rejectUser: async (userId) => {
    const authAxios = createAuthAxios();
    const response = await authAxios.put(`${ADMIN_BASE}/users/${userId}/reject`);
    return response.data;
  },

  resetUserPassword: async (userId, newPassword) => {
    const authAxios = createAuthAxios();
    const response = await authAxios.put(`${ADMIN_BASE}/users/${userId}/reset-password`, {
      new_password: newPassword
    });
    return response.data;
  },

  deleteUser: async (userId) => {
    const authAxios = createAuthAxios();
    const response = await authAxios.delete(`${ADMIN_BASE}/users/${userId}`);
    return response.data;
  },

  // 设备性质管理
  getDeviceProperties: async () => {
    const authAxios = createAuthAxios();
    const response = await authAxios.get(`${ADMIN_BASE}/device-properties`);
    return response.data;
  },

  setDeviceProperty: async (merchantId, property) => {
    const authAxios = createAuthAxios();
    const response = await authAxios.put(`${ADMIN_BASE}/device-properties`, {
      merchant_id: merchantId,
      property: property
    });
    return response.data;
  },

  deleteDeviceProperty: async (merchantId) => {
    const authAxios = createAuthAxios();
    const response = await authAxios.delete(`${ADMIN_BASE}/device-properties/${encodeURIComponent(merchantId)}`);
    return response.data;
  }
};
