import React, { useState, useEffect } from 'react';
import { scanAPI } from '../services/api';
import ProgressBar from '../components/ProgressBar';
import ScanTable from '../components/ScanTable';
import DetailModal from '../components/DetailModal';

const ScanPage = () => {
  const [localIPs, setLocalIPs] = useState([]);
  const [selectedIP, setSelectedIP] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [currentIP, setCurrentIP] = useState('');
  const [devices, setDevices] = useState([]);
  const [filteredDevices, setFilteredDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [lastScanAt, setLastScanAt] = useState(null);

  // 搜索条件
  const [searchConditions, setSearchConditions] = useState({
    ip: '',
    id: '',
    name: '',
    version: ''
  });

  // 获取本地IP列表
  useEffect(() => {
    const fetchLocalIPs = async () => {
      try {
        const response = await scanAPI.getLocalIPs();
        if (response.data.success) {
          setLocalIPs(response.data.ips);
          if (response.data.ips.length > 0) {
            setSelectedIP(response.data.ips[0]);
          }
        }
      } catch (error) {
        console.error('获取本地IP失败:', error);
      }
    };
    fetchLocalIPs();
  }, []);

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

  // 轮询扫描状态
  useEffect(() => {
    let intervalId;
    if (isScanning) {
      intervalId = setInterval(async () => {
        try {
          const response = await scanAPI.getScanStatus();
          const status = response.data;
          setScanProgress(status.progress);
          setCurrentIP(status.current_ip);
          setDevices(status.results);
          setFilteredDevices(status.results);
          if (!status.is_scanning) {
            setIsScanning(false);
            // 重新获取最后扫描时间
            try {
              const devicesRes = await scanAPI.getDevices();
              if (devicesRes.data.success) {
                setLastScanAt(devicesRes.data.lastScanAt);
              }
            } catch (e) {
              console.error('更新扫描时间失败:', e);
            }
            if (intervalId) clearInterval(intervalId);
          }
        } catch (error) {
          console.error('获取扫描状态失败:', error);
          setIsScanning(false);
          if (intervalId) clearInterval(intervalId);
        }
      }, 1000);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isScanning]);

  // 开始扫描
  const startScan = async () => {
    if (!selectedIP) {
      alert('请选择IP地址');
      return;
    }
    try {
      setIsScanning(true);
      setDevices([]);
      setFilteredDevices([]);
      setScanProgress(0);
      const response = await scanAPI.startScan(selectedIP);
      if (!response.data.success) {
        alert(response.data.error);
        setIsScanning(false);
      }
    } catch (error) {
      console.error('开始扫描失败:', error);
      setIsScanning(false);
    }
  };

  // 停止扫描
  const stopScan = async () => {
    try {
      await scanAPI.stopScan();
      setIsScanning(false);
    } catch (error) {
      console.error('停止扫描失败:', error);
    }
  };

  // 搜索处理
  const handleSearch = () => {
    const filtered = devices.filter(device => {
      const ipMatch = device.ip.toLowerCase().includes(searchConditions.ip.toLowerCase());
      const idMatch = (device.merchantId || '').toLowerCase().includes(searchConditions.id.toLowerCase());
      const nameMatch = (device.name || '').toLowerCase().includes(searchConditions.name.toLowerCase());
      const versionMatch = (device.version || '').toLowerCase().includes(searchConditions.version.toLowerCase());
      return ipMatch && idMatch && nameMatch && versionMatch;
    });
    setFilteredDevices(filtered);
  };

  // 清除搜索
  const clearSearch = () => {
    setSearchConditions({ ip: '', id: '', name: '', version: '' });
    setFilteredDevices(devices);
  };

  // 打开设备
  const handleOpenDevice = (ip) => {
    window.open(`http://${ip}:22080`, '_blank');
  };

  // 格式化最后扫描时间
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

  // 显示详情
  const handleShowDetails = (device) => {
    setSelectedDevice(device);
    setShowModal(true);
  };

  return (
    <div style={styles.page}>
      {/* 合并的控制栏：扫描控制 + 搜索 */}
      <div style={styles.toolbar}>
        <div style={styles.toolbarLeft}>
          <div style={styles.ipGroup}>
            <label style={styles.label}>网段</label>
            <select
              value={selectedIP}
              onChange={(e) => setSelectedIP(e.target.value)}
              disabled={isScanning}
              style={styles.select}
            >
              {localIPs.map(ip => (
                <option key={ip} value={ip}>{ip}</option>
              ))}
            </select>
          </div>
          <button
            onClick={isScanning ? stopScan : startScan}
            disabled={!selectedIP}
            style={{
              ...styles.scanBtn,
              ...(isScanning ? styles.btnStop : styles.btnStart),
              ...(!selectedIP ? styles.btnDisabled : {})
            }}
          >
            {isScanning ? '停止' : '扫描'}
          </button>
        </div>

        <div style={styles.toolbarCenter}>
          <input
            type="text"
            placeholder="IP"
            value={searchConditions.ip}
            onChange={(e) => setSearchConditions(prev => ({ ...prev, ip: e.target.value }))}
            style={styles.searchInput}
          />
          <input
            type="text"
            placeholder="ID"
            value={searchConditions.id}
            onChange={(e) => setSearchConditions(prev => ({ ...prev, id: e.target.value }))}
            style={styles.searchInput}
          />
          <input
            type="text"
            placeholder="名称"
            value={searchConditions.name}
            onChange={(e) => setSearchConditions(prev => ({ ...prev, name: e.target.value }))}
            style={styles.searchInput}
          />
          <input
            type="text"
            placeholder="版本"
            value={searchConditions.version}
            onChange={(e) => setSearchConditions(prev => ({ ...prev, version: e.target.value }))}
            style={styles.searchInput}
          />
          <button onClick={handleSearch} style={styles.searchBtn}>搜索</button>
          <button onClick={clearSearch} style={styles.clearBtn}>清除</button>
        </div>

        <div style={styles.toolbarRight}>
          {lastScanAt && (
            <span style={styles.lastScan}>上次更新: {formatLastScanTime(lastScanAt)}</span>
          )}
          <span style={styles.count}>{filteredDevices.length} 台设备</span>
        </div>
      </div>

      {/* 进度条 */}
      {isScanning && (
        <div style={styles.progressWrap}>
          <div style={styles.progressHeader}>
            <span>扫描进度</span>
            <span>{scanProgress}% · {currentIP}</span>
          </div>
          <div style={styles.progressBar}>
            <div style={{ ...styles.progressFill, width: `${scanProgress}%` }}></div>
          </div>
        </div>
      )}

      {/* 表格 */}
      <div style={styles.tableWrap}>
        <ScanTable
          devices={filteredDevices}
          onOpenDevice={handleOpenDevice}
          onShowDetails={handleShowDetails}
        />
      </div>

      {showModal && (
        <DetailModal
          device={selectedDevice}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
};

const styles = {
  page: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '16px',
    padding: '12px 16px',
    backgroundColor: 'white',
    borderRadius: '10px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.06)',
    flexWrap: 'wrap',
  },
  toolbarLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  ipGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  label: {
    fontSize: '12px',
    fontWeight: '500',
    color: '#86868B',
  },
  select: {
    padding: '6px 10px',
    border: '1px solid #D1D1D6',
    borderRadius: '6px',
    fontSize: '13px',
    minWidth: '120px',
    outline: 'none',
  },
  scanBtn: {
    padding: '6px 14px',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  btnStart: {
    backgroundColor: '#007AFF',
    color: 'white',
  },
  btnStop: {
    backgroundColor: '#FF3B30',
    color: 'white',
  },
  btnDisabled: {
    backgroundColor: '#C7C7CC',
    cursor: 'not-allowed',
  },
  toolbarCenter: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flex: 1,
    flexWrap: 'wrap',
  },
  searchInput: {
    padding: '6px 10px',
    border: '1px solid #D1D1D6',
    borderRadius: '6px',
    fontSize: '13px',
    width: '90px',
    outline: 'none',
  },
  searchBtn: {
    padding: '6px 12px',
    backgroundColor: '#007AFF',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer',
  },
  clearBtn: {
    padding: '6px 12px',
    backgroundColor: '#F2F2F7',
    color: '#1D1D1F',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer',
  },
  toolbarRight: {
    display: 'flex',
    alignItems: 'center',
  },
  lastScan: {
    fontSize: '12px',
    color: '#86868B',
    marginRight: '12px',
  },
  count: {
    fontSize: '13px',
    color: '#86868B',
    fontWeight: '500',
  },
  progressWrap: {
    padding: '10px 16px',
    backgroundColor: 'white',
    borderRadius: '10px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.06)',
  },
  progressHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '6px',
    fontSize: '12px',
    color: '#86868B',
  },
  progressBar: {
    width: '100%',
    height: '4px',
    backgroundColor: '#E5E5EA',
    borderRadius: '2px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    background: 'linear-gradient(90deg, #007AFF, #5AC8FA)',
    borderRadius: '2px',
    transition: 'width 0.3s ease',
  },
  tableWrap: {
    backgroundColor: 'white',
    borderRadius: '10px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.06)',
    overflow: 'hidden',
  },
};

export default ScanPage;
