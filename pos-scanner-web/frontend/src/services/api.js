import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 添加请求拦截器，自动带上 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 创建带认证的 axios 实例
const createAuthAxios = () => {
  const token = localStorage.getItem('access_token');
  return axios.create({
    baseURL: API_BASE_URL,
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  });
};

export const scanAPI = {
  // 获取本地IP列表
  getLocalIPs: () => api.get('/scan/ips'),

  // 开始扫描
  startScan: (localIP) => api.post('/scan/start', { local_ip: localIP }),

  // 获取扫描状态
  getScanStatus: () => api.get('/scan/status'),

  // 停止扫描
  stopScan: () => api.post('/scan/stop'),

  // 获取设备列表（支持分页和搜索）
  getDevices: (page = 1, pageSize = 50, search = '') => {
    const params = new URLSearchParams({ page, page_size: pageSize });
    if (search) params.append('search', search);
    return api.get(`/devices?${params.toString()}`);
  },

  // 获取设备详情
  getDeviceDetails: (ip) => api.get(`/scan/device/${ip}/details`)
};

// 设备占用 API（需要认证）
export const deviceAPI = {
  // 获取所有占用信息
  getOccupancies: async () => {
    const authAxios = createAuthAxios();
    const response = await authAxios.get('/device/occupancy');
    return response.data;
  },

  // 设置占用
  setOccupancy: async (merchantId, purpose, startTime, endTime) => {
    const authAxios = createAuthAxios();
    const response = await authAxios.put('/device/occupancy', {
      merchant_id: merchantId,
      purpose,
      start_time: startTime,
      end_time: endTime
    });
    return response.data;
  },

  // 释放占用
  releaseOccupancy: async (merchantId) => {
    const authAxios = createAuthAxios();
    const response = await authAxios.delete(`/device/occupancy/${encodeURIComponent(merchantId)}`);
    return response.data;
  },

  // 删除设备（仅管理员）
  deleteDevice: async (merchantId) => {
    const authAxios = createAuthAxios();
    const response = await authAxios.delete(`/device/${encodeURIComponent(merchantId)}`);
    return response.data;
  },

  // 提交认领申请
  submitClaim: async (merchantId) => {
    const authAxios = createAuthAxios();
    const response = await authAxios.post('/device/claim', { merchant_id: merchantId });
    return response.data;
  },

  // 获取认领申请列表（管理员）
  getClaims: async (status = 'pending') => {
    const authAxios = createAuthAxios();
    const response = await authAxios.get(`/device/claims?status=${status}`);
    return response.data;
  },

  // 审核通过认领申请（管理员）
  approveClaim: async (claimId) => {
    const authAxios = createAuthAxios();
    const response = await authAxios.post(`/device/claim/${claimId}/approve`);
    return response.data;
  },

  // 审核拒绝认领申请（管理员）
  rejectClaim: async (claimId) => {
    const authAxios = createAuthAxios();
    const response = await authAxios.post(`/device/claim/${claimId}/reject`);
    return response.data;
  },

  // 重置设备认领状态（管理员）
  resetOwner: async (merchantId) => {
    const authAxios = createAuthAxios();
    const response = await authAxios.delete(`/device/${encodeURIComponent(merchantId)}/owner`);
    return response.data;
  }
};

export default api;