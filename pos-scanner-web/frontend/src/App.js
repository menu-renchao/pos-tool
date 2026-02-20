import React, { useState, useEffect } from 'react';
import { scanAPI } from './services/api';
import ProgressBar from './components/ProgressBar';
import SearchBar from './components/SearchBar';
import ScanTable from './components/ScanTable';
import DetailModal from './components/DetailModal';
import './App.css';

function App() {
  const [localIPs, setLocalIPs] = useState([]);
  const [selectedIP, setSelectedIP] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [currentIP, setCurrentIP] = useState('');
  const [devices, setDevices] = useState([]);
  const [filteredDevices, setFilteredDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [showModal, setShowModal] = useState(false);

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

  // 显示详情
  const handleShowDetails = (device) => {
    setSelectedDevice(device);
    setShowModal(true);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Menusifu设备管理平台</h1>
      </header>

      <main className="app-main">
        <div className="control-panel">
          <div className="scan-controls">
            <div className="ip-selector">
              <label>选择网段:</label>
              <select
                value={selectedIP}
                onChange={(e) => setSelectedIP(e.target.value)}
                disabled={isScanning}
              >
                {localIPs.map(ip => (
                  <option key={ip} value={ip}>{ip}</option>
                ))}
              </select>
            </div>

            <button
              className={`btn ${isScanning ? 'btn-stop' : 'btn-start'}`}
              onClick={isScanning ? stopScan : startScan}
              disabled={!selectedIP}
            >
              {isScanning ? '停止扫描' : '开始扫描'}
            </button>
          </div>

          {isScanning && (
            <ProgressBar
              progress={scanProgress}
              currentIP={currentIP}
              isScanning={isScanning}
            />
          )}
        </div>

        <SearchBar
          searchIP={searchConditions.ip}
          searchID={searchConditions.id}
          searchName={searchConditions.name}
          searchVersion={searchConditions.version}
          onSearchChange={(field, value) => setSearchConditions(prev => ({
            ...prev,
            [field]: value
          }))}
          onSearch={handleSearch}
          onClear={clearSearch}
        />

        <div className="results-info">
          找到 {filteredDevices.length} 台设备
        </div>

        <ScanTable
          devices={filteredDevices}
          onOpenDevice={handleOpenDevice}
          onShowDetails={handleShowDetails}
          onRemarkChange={(ip, remark) => {
            // 处理备注更新
            console.log(`更新设备 ${ip} 的备注:`, remark);
          }}
        />

        {showModal && (
          <DetailModal
            device={selectedDevice}
            onClose={() => setShowModal(false)}
          />
        )}
      </main>
    </div>
  );
}

export default App;