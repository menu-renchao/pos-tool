import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

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

export default api;