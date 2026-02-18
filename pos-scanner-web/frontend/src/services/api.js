import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
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

  // 获取设备列表
  getDevices: () => api.get('/devices'),

  // 获取设备详情
  getDeviceDetails: (ip) => api.get(`/device/${ip}/details`)
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
  }
};

export default api;