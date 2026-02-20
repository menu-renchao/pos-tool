import React, { useState, useEffect } from 'react';
import { scanAPI, deviceAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { adminService } from '../services/authService';
import ScanTable from '../components/ScanTable';
import DetailModal from '../components/DetailModal';

const ScanPage = () => {
  const { isAdmin, user } = useAuth();
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

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [totalDevices, setTotalDevices] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  // 设备性质编辑
  const [propertyModal, setPropertyModal] = useState({ show: false, device: null });
  const [propertyValue, setPropertyValue] = useState('');

  // 设备占用编辑
  const [occupancyModal, setOccupancyModal] = useState({ show: false, device: null });
  const [occupancyPurpose, setOccupancyPurpose] = useState('');
  const [occupancyEndTime, setOccupancyEndTime] = useState('');

  // 搜索条件
  const [searchText, setSearchText] = useState('');

  // 获取本地IP列表
  useEffect(() => {
    const fetchLocalIPs = async () => {
      try {
        const response = await scanAPI.getLocalIPs();
        if (response.data.success && response.data.data) {
          const ips = response.data.data.ips || [];
          setLocalIPs(ips);
          if (ips.length > 0) {
            setSelectedIP(ips[0]);
          }
        }
      } catch (error) {
        console.error('获取本地IP失败:', error);
      }
    };
    fetchLocalIPs();
  }, []);

  // 加载设备列表（分页+搜索）
  const loadDevices = async (page = currentPage, size = pageSize, search = searchText) => {
    try {
      const response = await scanAPI.getDevices(page, size, search);
      if (response.data.success && response.data.data) {
        setDevices(response.data.data.devices || []);
        setFilteredDevices(response.data.data.devices || []);
        setTotalDevices(response.data.data.total || 0);
        setTotalPages(response.data.data.totalPages || 0);
        setLastScanAt(response.data.data.lastScanAt);
      }
    } catch (error) {
      console.error('加载设备列表失败:', error);
    }
  };

  // 初始加载
  useEffect(() => {
    loadDevices(1, pageSize, '');
  }, []);

  // 页码改变
  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
    loadDevices(newPage, pageSize, searchText);
  };

  // 每页数量改变
  const handlePageSizeChange = (newSize) => {
    setPageSize(newSize);
    setCurrentPage(1);
    loadDevices(1, newSize, searchText);
  };

  // 轮询扫描状态
  useEffect(() => {
    let intervalId;
    if (isScanning) {
      intervalId = setInterval(async () => {
        try {
          const response = await scanAPI.getScanStatus();
          const status = response.data.data || response.data;
          setScanProgress(status.progress || 0);
          setCurrentIP(status.current_ip || '');
          if (status.results) {
            setDevices(status.results);
            setFilteredDevices(status.results);
          }
          if (!status.is_scanning) {
            setIsScanning(false);
            // 扫描完成后重新获取设备列表
            loadDevices(1, pageSize, searchText);
            setCurrentPage(1);
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

  // 搜索处理（后端搜索）
  const handleSearch = () => {
    setCurrentPage(1);
    loadDevices(1, pageSize, searchText);
  };

  // 清除搜索
  const clearSearch = () => {
    setSearchText('');
    setCurrentPage(1);
    loadDevices(1, pageSize, '');
  };

  // 打开设备
  const handleOpenDevice = (ip) => {
    window.open(`http://${ip}:22080`, '_blank');
  };

  // 格式化最后扫描时间
  const formatLastScanTime = (isoString) => {
    if (!isoString || isoString === '') return '';
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return '';
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

  // 编辑设备性质
  const handleEditProperty = (device) => {
    setPropertyModal({ show: true, device });
    setPropertyValue(device.property || '');
  };

  // 保存设备性质
  const handleSaveProperty = async () => {
    if (!propertyModal.device) return;
    try {
      const result = await adminService.setDeviceProperty(
        propertyModal.device.merchantId,
        propertyValue
      );
      if (result.success) {
        // 刷新设备列表
        loadDevices(currentPage, pageSize, searchText);
        setPropertyModal({ show: false, device: null });
      } else {
        alert(result.error);
      }
    } catch (error) {
      alert('保存失败');
    }
  };

  // 编辑设备占用
  const handleEditOccupancy = (device) => {
    setOccupancyModal({ show: true, device });
    setOccupancyPurpose(device.occupancy?.purpose || '');
    // 默认结束时间为2小时后
    if (device.occupancy?.endTime) {
      setOccupancyEndTime(device.occupancy.endTime.slice(0, 16));
    } else {
      const defaultEnd = new Date(Date.now() + 2 * 60 * 60 * 1000);
      setOccupancyEndTime(defaultEnd.toISOString().slice(0, 16));
    }
  };

  // 保存设备占用
  const handleSaveOccupancy = async () => {
    if (!occupancyModal.device) return;
    if (!occupancyEndTime) {
      alert('请选择结束时间');
      return;
    }
    try {
      const result = await deviceAPI.setOccupancy(
        occupancyModal.device.merchantId,
        occupancyPurpose,
        null, // start_time 使用当前时间
        new Date(occupancyEndTime).toISOString()
      );
      if (result.success) {
        // 刷新设备列表
        loadDevices(currentPage, pageSize, searchText);
        setOccupancyModal({ show: false, device: null });
      } else {
        alert(result.error);
      }
    } catch (error) {
      alert('保存失败');
    }
  };

  // 释放设备占用
  const handleReleaseOccupancy = async () => {
    if (!occupancyModal.device) return;
    if (!window.confirm('确定要释放此设备吗？')) return;
    try {
      const result = await deviceAPI.releaseOccupancy(occupancyModal.device.merchantId);
      if (result.success) {
        // 刷新设备列表
        loadDevices(currentPage, pageSize, searchText);
        setOccupancyModal({ show: false, device: null });
      } else {
        alert(result.error);
      }
    } catch (error) {
      alert('释放失败');
    }
  };

  // 刷新设备列表
  const refreshDevices = async () => {
    loadDevices(currentPage, pageSize);
  };

  // 删除离线设备（仅管理员）
  const handleDeleteDevice = async (device) => {
    if (!device.merchantId) return;
    if (!window.confirm(`确定要删除设备 ${device.name || device.merchantId} 吗？\n此操作不可恢复。`)) return;

    try {
      const response = await deviceAPI.deleteDevice(device.merchantId);
      if (response.success) {
        // 刷新设备列表
        loadDevices(currentPage, pageSize, searchText);
      } else {
        alert(response.error || '删除失败');
      }
    } catch (error) {
      console.error('删除设备失败:', error);
      alert('删除失败');
    }
  };

  // 认领设备
  const handleClaimDevice = async (device) => {
    if (!device.merchantId) return;
    if (!window.confirm(`确定要认领设备 ${device.name || device.merchantId} 吗？\n认领申请将提交给管理员审核。`)) return;

    try {
      const response = await deviceAPI.submitClaim(device.merchantId);
      if (response.success) {
        alert(response.message || '认领申请已提交');
      } else {
        alert(response.error || '提交失败');
      }
    } catch (error) {
      console.error('认领设备失败:', error);
      const errorMsg = error.response?.data?.error || error.message || '提交失败';
      alert(errorMsg);
    }
  };

  // 重置认领状态（仅管理员）
  const handleResetOwner = async (device) => {
    if (!device.merchantId) return;
    if (!window.confirm(`确定要重置设备 ${device.name || device.merchantId} 的认领状态吗？`)) return;

    try {
      const response = await deviceAPI.resetOwner(device.merchantId);
      if (response.success) {
        // 刷新设备列表
        loadDevices(currentPage, pageSize, searchText);
      } else {
        alert(response.error || '重置失败');
      }
    } catch (error) {
      console.error('重置认领状态失败:', error);
      alert('重置失败');
    }
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
              {(localIPs || []).map(ip => (
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
            placeholder="搜索IP/ID/名称/版本..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            style={styles.searchInput}
          />
          <button onClick={handleSearch} style={styles.searchBtn}>搜索</button>
          {searchText && (
            <button onClick={clearSearch} style={styles.clearBtn}>清除</button>
          )}
        </div>

        <div style={styles.toolbarRight}>
          {lastScanAt && (
            <span style={styles.lastScan}>上次扫描: {formatLastScanTime(lastScanAt)}</span>
          )}
          <span style={styles.count}>{totalDevices} 台设备</span>
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
          onEditProperty={handleEditProperty}
          onEditOccupancy={handleEditOccupancy}
          onDeleteDevice={handleDeleteDevice}
          onClaimDevice={handleClaimDevice}
          onResetOwner={handleResetOwner}
          isAdmin={isAdmin()}
          currentUserId={user?.id}
        />
      </div>

      {/* 分页 */}
      {totalDevices > 0 && (
        <div style={styles.pagination}>
          <div style={styles.paginationInfo}>
            共 {totalDevices} 条，每页
            <select
              value={pageSize}
              onChange={(e) => handlePageSizeChange(Number(e.target.value))}
              style={styles.pageSizeSelect}
            >
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
            </select>
            条
          </div>
          <div style={styles.paginationBtns}>
            <button
              onClick={() => handlePageChange(1)}
              disabled={currentPage === 1}
              style={{ ...styles.pageBtn, ...(currentPage === 1 ? styles.pageBtnDisabled : {}) }}
            >
              首页
            </button>
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              style={{ ...styles.pageBtn, ...(currentPage === 1 ? styles.pageBtnDisabled : {}) }}
            >
              上一页
            </button>
            <span style={styles.pageNum}>
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              style={{ ...styles.pageBtn, ...(currentPage === totalPages ? styles.pageBtnDisabled : {}) }}
            >
              下一页
            </button>
            <button
              onClick={() => handlePageChange(totalPages)}
              disabled={currentPage === totalPages}
              style={{ ...styles.pageBtn, ...(currentPage === totalPages ? styles.pageBtnDisabled : {}) }}
            >
              末页
            </button>
          </div>
        </div>
      )}

      {showModal && (
        <DetailModal
          device={selectedDevice}
          onClose={() => setShowModal(false)}
        />
      )}

      {/* 设备分类编辑弹窗 */}
      {propertyModal.show && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalContent}>
            <div style={styles.modalHeader}>
              <h3>编辑分类</h3>
              <button onClick={() => setPropertyModal({ show: false, device: null })} style={styles.closeBtn}>×</button>
            </div>
            <div style={styles.modalBody}>
              <p style={styles.modalInfo}>
                商家ID: <strong>{propertyModal.device?.merchantId}</strong>
              </p>
              <p style={styles.modalInfo}>
                设备名称: <strong>{propertyModal.device?.name || '——'}</strong>
              </p>
              <div style={styles.fieldGroup}>
                <label>分类</label>
                <input
                  type="text"
                  value={propertyValue}
                  onChange={(e) => setPropertyValue(e.target.value)}
                  placeholder="如：测试组专用、PC等"
                  style={styles.input}
                />
              </div>
              <div style={styles.modalActions}>
                <button onClick={() => setPropertyModal({ show: false, device: null })} style={styles.btnCancel}>取消</button>
                <button onClick={handleSaveProperty} style={styles.btnSave}>保存</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 设备借用编辑弹窗 */}
      {occupancyModal.show && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalContent}>
            <div style={styles.modalHeader}>
              <h3>{occupancyModal.device?.isOccupied ? '借用详情' : '借用设备'}</h3>
              <button onClick={() => setOccupancyModal({ show: false, device: null })} style={styles.closeBtn}>×</button>
            </div>
            <div style={styles.modalBody}>
              <p style={styles.modalInfo}>
                商家ID: <strong>{occupancyModal.device?.merchantId}</strong>
              </p>
              <p style={styles.modalInfo}>
                设备名称: <strong>{occupancyModal.device?.name || '——'}</strong>
              </p>
              <p style={styles.modalInfo}>
                借用人: <strong style={{ color: '#007AFF' }}>{occupancyModal.device?.occupancy?.username || user?.name || user?.username}</strong>
              </p>

              {occupancyModal.device?.isOccupied && !isAdmin() && occupancyModal.device?.occupancy?.userId !== user?.id ? (
                <>
                  <p style={styles.modalInfo}>
                    用途: <strong>{occupancyModal.device?.occupancy?.purpose || '——'}</strong>
                  </p>
                  <p style={styles.modalInfo}>
                    归还时间: <strong>{occupancyModal.device?.occupancy?.endTime ? new Date(occupancyModal.device?.occupancy?.endTime).toLocaleString('zh-CN') : '——'}</strong>
                  </p>
                  <div style={styles.modalActions}>
                    <button onClick={() => setOccupancyModal({ show: false, device: null })} style={styles.btnCancel}>关闭</button>
                  </div>
                </>
              ) : (
                <>
                  <div style={styles.fieldGroup}>
                    <label>用途</label>
                    <input
                      type="text"
                      value={occupancyPurpose}
                      onChange={(e) => setOccupancyPurpose(e.target.value)}
                      placeholder="请输入用途"
                      style={styles.input}
                    />
                  </div>

                  <div style={styles.fieldGroup}>
                    <label>归还时间</label>
                    <input
                      type="datetime-local"
                      value={occupancyEndTime}
                      onChange={(e) => setOccupancyEndTime(e.target.value)}
                      style={styles.input}
                    />
                  </div>

                  <div style={styles.modalActions}>
                    <button onClick={() => setOccupancyModal({ show: false, device: null })} style={styles.btnCancel}>取消</button>
                    {occupancyModal.device?.isOccupied && (
                      <button onClick={handleReleaseOccupancy} style={styles.btnDanger}>归还</button>
                    )}
                    <button onClick={handleSaveOccupancy} style={styles.btnSave}>
                      {occupancyModal.device?.isOccupied ? '更新' : '借用'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
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
    padding: '6px 12px',
    border: '1px solid #D1D1D6',
    borderRadius: '6px',
    fontSize: '13px',
    width: '200px',
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
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  modalContent: {
    backgroundColor: 'white',
    borderRadius: '12px',
    width: '360px',
    maxWidth: '90%',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderBottom: '1px solid #E5E5EA',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    fontSize: '20px',
    cursor: 'pointer',
    color: '#86868B',
    padding: 0,
  },
  modalBody: {
    padding: '20px',
  },
  modalInfo: {
    fontSize: '13px',
    color: '#86868B',
    marginBottom: '8px',
  },
  fieldGroup: {
    marginTop: '16px',
    marginBottom: '20px',
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #D1D1D6',
    borderRadius: '8px',
    fontSize: '14px',
    outline: 'none',
    marginTop: '6px',
  },
  modalActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
  },
  btnCancel: {
    padding: '8px 16px',
    backgroundColor: '#F2F2F7',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    cursor: 'pointer',
  },
  btnSave: {
    padding: '8px 16px',
    backgroundColor: '#007AFF',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    cursor: 'pointer',
  },
  btnDanger: {
    padding: '8px 16px',
    backgroundColor: '#FF3B30',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    cursor: 'pointer',
  },
  pagination: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    backgroundColor: 'white',
    borderRadius: '10px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.06)',
  },
  paginationInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '13px',
    color: '#86868B',
  },
  pageSizeSelect: {
    padding: '4px 8px',
    border: '1px solid #D1D1D6',
    borderRadius: '6px',
    fontSize: '13px',
    margin: '0 4px',
  },
  paginationBtns: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  pageBtn: {
    padding: '6px 12px',
    backgroundColor: '#F2F2F7',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  pageBtnDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  pageNum: {
    padding: '0 12px',
    fontSize: '13px',
    color: '#1D1D1F',
    fontWeight: '500',
  },
};

export default ScanPage;
