import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';

const API_BASE = '/api/mobile';

const createAuthAxios = () => {
  const token = localStorage.getItem('access_token');
  return axios.create({
    baseURL: API_BASE,
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  });
};

const MobileDevicesPage = () => {
  const { isAdmin, user } = useAuth();
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('card'); // card or list

  // 弹窗状态
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // create, edit, occupy
  const [selectedDevice, setSelectedDevice] = useState(null);

  // 表单数据
  const [formData, setFormData] = useState({
    name: '',
    deviceType: '',
    systemVersion: ''
  });
  const [occupancyData, setOccupancyData] = useState({
    purpose: '',
    endTime: ''
  });

  // 图片预览
  const [imageA, setImageA] = useState(null);
  const [imageB, setImageB] = useState(null);

  // 大图预览
  const [previewImage, setPreviewImage] = useState(null);

  const openImagePreview = (imageUrl) => {
    setPreviewImage(imageUrl);
  };

  const closeImagePreview = () => {
    setPreviewImage(null);
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    setLoading(true);
    try {
      const authAxios = createAuthAxios();
      const response = await authAxios.get('/devices');
      if (response.data.success) {
        setDevices(response.data.devices);
      }
    } catch (error) {
      console.error('获取设备列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 打开创建弹窗
  const openCreateModal = () => {
    setModalMode('create');
    setSelectedDevice(null);
    setFormData({ name: '', deviceType: '', systemVersion: '' });
    setImageA(null);
    setImageB(null);
    setShowModal(true);
  };

  // 打开编辑弹窗
  const openEditModal = (device) => {
    setModalMode('edit');
    setSelectedDevice(device);
    setFormData({
      name: device.name,
      deviceType: device.deviceType || '',
      systemVersion: device.systemVersion || ''
    });
    setImageA(null);
    setImageB(null);
    setShowModal(true);
  };

  // 打开占用弹窗
  const openOccupyModal = (device) => {
    setModalMode('occupy');
    setSelectedDevice(device);
    const defaultEnd = new Date(Date.now() + 2 * 60 * 60 * 1000);
    setOccupancyData({
      purpose: device.purpose || '',
      endTime: defaultEnd.toISOString().slice(0, 16)
    });
    setShowModal(true);
  };

  // 关闭弹窗
  const closeModal = () => {
    setShowModal(false);
    setSelectedDevice(null);
  };

  // 创建/更新设备
  const handleSaveDevice = async () => {
    if (!formData.name) {
      alert('请输入设备名称');
      return;
    }

    try {
      const authAxios = createAuthAxios();
      let deviceId = selectedDevice?.id;

      if (modalMode === 'create') {
        const response = await authAxios.post('/devices', formData);
        deviceId = response.data.device?.id;
      } else {
        await authAxios.put(`/devices/${selectedDevice.id}`, formData);
      }

      // 上传图片
      if (imageA && deviceId) {
        await uploadImage(deviceId, imageA, 'a');
      }
      if (imageB && deviceId) {
        await uploadImage(deviceId, imageB, 'b');
      }

      fetchDevices();
      closeModal();
    } catch (error) {
      alert(error.response?.data?.error || '操作失败');
    }
  };

  // 上传图片
  const uploadImage = async (deviceId, file, type) => {
    const formData = new FormData();
    formData.append('image', file);
    formData.append('type', type);

    const token = localStorage.getItem('access_token');
    await axios.post(`${API_BASE}/devices/${deviceId}/upload`, formData, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'multipart/form-data'
      }
    });
  };

  // 删除设备
  const handleDelete = async (deviceId) => {
    if (!window.confirm('确定要删除此设备吗？')) return;

    try {
      const authAxios = createAuthAxios();
      await authAxios.delete(`/devices/${deviceId}`);
      fetchDevices();
    } catch (error) {
      alert(error.response?.data?.error || '删除失败');
    }
  };

  // 设置占用
  const handleSetOccupancy = async () => {
    if (!occupancyData.endTime) {
      alert('请选择释放时间');
      return;
    }

    try {
      const authAxios = createAuthAxios();
      await authAxios.put(`/devices/${selectedDevice.id}/occupy`, {
        purpose: occupancyData.purpose,
        endTime: new Date(occupancyData.endTime).toISOString()
      });
      fetchDevices();
      closeModal();
    } catch (error) {
      alert(error.response?.data?.error || '操作失败');
    }
  };

  // 释放设备
  const handleRelease = async (deviceId) => {
    if (!window.confirm('确定要释放此设备吗？')) return;

    try {
      const authAxios = createAuthAxios();
      await authAxios.put(`/devices/${deviceId}/release`);
      fetchDevices();
    } catch (error) {
      alert(error.response?.data?.error || '释放失败');
    }
  };

  // 格式化时间
  const formatTime = (isoString) => {
    if (!isoString) return '——';
    return new Date(isoString).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>移动设备管理</h1>
          <p style={styles.subtitle}>管理测试用的移动设备</p>
        </div>
        <div style={styles.headerActions}>
          <div style={styles.viewToggle}>
            <button
              onClick={() => setViewMode('card')}
              style={{
                ...styles.toggleBtn,
                ...(viewMode === 'card' ? styles.toggleBtnActive : {})
              }}
              title="卡片视图"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M4 4h7v7H4zM4 13h7v7H4zM13 4h7v7h-7zM13 13h7v7h-7z"/>
              </svg>
            </button>
            <button
              onClick={() => setViewMode('list')}
              style={{
                ...styles.toggleBtn,
                ...(viewMode === 'list' ? styles.toggleBtnActive : {})
              }}
              title="列表视图"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M4 6h16v2H4zM4 11h16v2H4zM4 16h16v2H4z"/>
              </svg>
            </button>
          </div>
          {isAdmin() && (
            <button onClick={openCreateModal} style={styles.createBtn}>
              + 添加设备
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div style={styles.loading}>加载中...</div>
      ) : devices.length === 0 ? (
        <div style={styles.empty}>暂无设备</div>
      ) : viewMode === 'card' ? (
        <div style={styles.grid}>
          {devices.map(device => (
            <div key={device.id} style={styles.card}>
              <div style={styles.cardHeader}>
                <h3 style={styles.deviceName}>{device.name}</h3>
                <span style={styles.deviceType}>{device.deviceType || '未分类'}</span>
              </div>

              <div style={styles.images}>
                <div style={styles.imageBox}>
                  {device.imageA ? (
                    <img
                      src={`/${device.imageA}`}
                      alt="A面"
                      style={{ ...styles.image, cursor: 'pointer' }}
                      onClick={() => openImagePreview(`/${device.imageA}`)}
                    />
                  ) : (
                    <span style={styles.noImage}>A面</span>
                  )}
                </div>
                <div style={styles.imageBox}>
                  {device.imageB ? (
                    <img
                      src={`/${device.imageB}`}
                      alt="B面"
                      style={{ ...styles.image, cursor: 'pointer' }}
                      onClick={() => openImagePreview(`/${device.imageB}`)}
                    />
                  ) : (
                    <span style={styles.noImage}>B面</span>
                  )}
                </div>
              </div>

              <div style={styles.cardInfo}>
                <p><span style={styles.label}>系统版本:</span> {device.systemVersion || '——'}</p>
                <p>
                  <span style={styles.label}>占用状态:</span>{' '}
                  {device.isOccupied ? (
                    <span style={styles.occupied}>{device.occupier}</span>
                  ) : (
                    <span style={styles.free}>空闲</span>
                  )}
                </p>
                {device.isOccupied && (
                  <p><span style={styles.label}>释放时间:</span> {formatTime(device.endTime)}</p>
                )}
              </div>

              <div style={styles.cardActions}>
                {device.isOccupied ? (
                  (isAdmin() || device.occupierId === user?.id) ? (
                    <button
                      onClick={() => handleRelease(device.id)}
                      style={styles.releaseBtn}
                    >
                      释放
                    </button>
                  ) : (
                    <span style={styles.occupiedLabel}>已被 {device.occupier} 占用</span>
                  )
                ) : (
                  <button
                    onClick={() => openOccupyModal(device)}
                    style={styles.occupyBtn}
                  >
                    占用
                  </button>
                )}
                {isAdmin() && (
                  <>
                    <button onClick={() => openEditModal(device)} style={styles.editBtn}>编辑</button>
                    <button onClick={() => handleDelete(device.id)} style={styles.deleteBtn}>删除</button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={styles.listContainer}>
          <div style={styles.listHeader}>
            <div style={styles.listHeaderImages}>图片</div>
            <div style={styles.listHeaderName}>设备名称</div>
            <div style={styles.listHeaderType}>类型</div>
            <div style={styles.listHeaderVersion}>系统版本</div>
            <div style={styles.listHeaderStatus}>占用状态</div>
            <div style={styles.listHeaderEndTime}>释放时间</div>
            <div style={styles.listHeaderActions}>操作</div>
          </div>
          {devices.map(device => (
            <div key={device.id} style={styles.listRow}>
              <div style={styles.listImages}>
                {device.imageA ? (
                  <img
                    src={`/${device.imageA}`}
                    alt="A面"
                    style={{ ...styles.listImage, cursor: 'pointer' }}
                    onClick={() => openImagePreview(`/${device.imageA}`)}
                  />
                ) : (
                  <div style={styles.listNoImage}>A</div>
                )}
                {device.imageB ? (
                  <img
                    src={`/${device.imageB}`}
                    alt="B面"
                    style={{ ...styles.listImage, cursor: 'pointer' }}
                    onClick={() => openImagePreview(`/${device.imageB}`)}
                  />
                ) : (
                  <div style={styles.listNoImage}>B</div>
                )}
              </div>
              <div style={styles.listName}>{device.name}</div>
              <div style={styles.listType}>{device.deviceType || '未分类'}</div>
              <div style={styles.listVersion}>{device.systemVersion || '——'}</div>
              <div style={styles.listStatus}>
                {device.isOccupied ? (
                  <span style={styles.occupied}>{device.occupier}</span>
                ) : (
                  <span style={styles.free}>空闲</span>
                )}
              </div>
              <div style={styles.listEndTime}>
                {device.isOccupied ? formatTime(device.endTime) : '——'}
              </div>
              <div style={styles.listActions}>
                {device.isOccupied ? (
                  (isAdmin() || device.occupierId === user?.id) ? (
                    <button onClick={() => handleRelease(device.id)} style={styles.listReleaseBtn}>释放</button>
                  ) : null
                ) : (
                  <button onClick={() => openOccupyModal(device)} style={styles.listOccupyBtn}>占用</button>
                )}
                {isAdmin() && (
                  <>
                    <button onClick={() => openEditModal(device)} style={styles.listEditBtn}>编辑</button>
                    <button onClick={() => handleDelete(device.id)} style={styles.listDeleteBtn}>删除</button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 弹窗 */}
      {showModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.modal}>
            <div style={styles.modalHeader}>
              <h3>
                {modalMode === 'create' && '添加设备'}
                {modalMode === 'edit' && '编辑设备'}
                {modalMode === 'occupy' && '占用设备'}
              </h3>
              <button onClick={closeModal} style={styles.closeBtn}>×</button>
            </div>

            <div style={styles.modalBody}>
              {(modalMode === 'create' || modalMode === 'edit') && (
                <>
                  <div style={styles.field}>
                    <label>设备名称 *</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={e => setFormData({ ...formData, name: e.target.value })}
                      style={styles.input}
                    />
                  </div>
                  <div style={styles.field}>
                    <label>设备类型</label>
                    <input
                      type="text"
                      value={formData.deviceType}
                      onChange={e => setFormData({ ...formData, deviceType: e.target.value })}
                      style={styles.input}
                      placeholder="如：手机、平板等"
                    />
                  </div>
                  <div style={styles.field}>
                    <label>系统版本</label>
                    <input
                      type="text"
                      value={formData.systemVersion}
                      onChange={e => setFormData({ ...formData, systemVersion: e.target.value })}
                      style={styles.input}
                      placeholder="如：iOS 17.0, Android 14"
                    />
                  </div>
                  <div style={styles.field}>
                    <label>A面图片</label>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={e => setImageA(e.target.files[0])}
                      style={styles.fileInput}
                    />
                  </div>
                  <div style={styles.field}>
                    <label>B面图片</label>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={e => setImageB(e.target.files[0])}
                      style={styles.fileInput}
                    />
                  </div>
                </>
              )}

              {modalMode === 'occupy' && (
                <>
                  <p style={styles.modalInfo}>
                    设备: <strong>{selectedDevice?.name}</strong>
                  </p>
                  <p style={styles.modalInfo}>
                    占用人: <strong style={{ color: '#007AFF' }}>{user?.username}</strong>
                  </p>
                  <div style={styles.field}>
                    <label>用途</label>
                    <input
                      type="text"
                      value={occupancyData.purpose}
                      onChange={e => setOccupancyData({ ...occupancyData, purpose: e.target.value })}
                      style={styles.input}
                      placeholder="请输入用途"
                    />
                  </div>
                  <div style={styles.field}>
                    <label>释放时间</label>
                    <input
                      type="datetime-local"
                      value={occupancyData.endTime}
                      onChange={e => setOccupancyData({ ...occupancyData, endTime: e.target.value })}
                      style={styles.input}
                    />
                  </div>
                </>
              )}
            </div>

            <div style={styles.modalActions}>
              <button onClick={closeModal} style={styles.cancelBtn}>取消</button>
              <button
                onClick={modalMode === 'occupy' ? handleSetOccupancy : handleSaveDevice}
                style={styles.saveBtn}
              >
                {modalMode === 'create' ? '创建' : modalMode === 'edit' ? '保存' : '占用'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 图片预览弹窗 */}
      {previewImage && (
        <div style={styles.previewOverlay} onClick={closeImagePreview}>
          <button style={styles.previewCloseBtn} onClick={closeImagePreview}>×</button>
          <img src={previewImage} alt="预览" style={styles.previewImage} onClick={(e) => e.stopPropagation()} />
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    padding: '16px',
    maxWidth: '1200px',
    margin: '0 auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
  },
  title: {
    fontSize: '20px',
    fontWeight: '600',
    color: '#1D1D1F',
    marginBottom: '2px',
  },
  subtitle: {
    fontSize: '13px',
    color: '#86868B',
  },
  headerActions: {
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
  },
  viewToggle: {
    display: 'flex',
    backgroundColor: '#F2F2F7',
    borderRadius: '6px',
    padding: '2px',
  },
  toggleBtn: {
    padding: '6px 10px',
    backgroundColor: 'transparent',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    color: '#86868B',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  toggleBtnActive: {
    backgroundColor: 'white',
    color: '#1D1D1F',
    boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
  },
  createBtn: {
    padding: '8px 16px',
    backgroundColor: '#007AFF',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
  },
  backButton: {
    padding: '8px 16px',
    backgroundColor: '#F2F2F7',
    color: '#1D1D1F',
    borderRadius: '8px',
    textDecoration: 'none',
    fontSize: '14px',
    fontWeight: '500',
  },
  loading: {
    textAlign: 'center',
    padding: '40px',
    color: '#86868B',
  },
  empty: {
    textAlign: 'center',
    padding: '40px',
    color: '#86868B',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '16px',
  },
  card: {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '16px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  },
  deviceName: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#1D1D1F',
    margin: 0,
  },
  deviceType: {
    fontSize: '12px',
    color: '#86868B',
    backgroundColor: '#F2F2F7',
    padding: '2px 8px',
    borderRadius: '4px',
  },
  images: {
    display: 'flex',
    gap: '8px',
    marginBottom: '12px',
  },
  imageBox: {
    flex: 1,
    height: '100px',
    backgroundColor: '#F2F2F7',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  image: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  noImage: {
    fontSize: '12px',
    color: '#86868B',
  },
  cardInfo: {
    marginBottom: '12px',
  },
  label: {
    color: '#86868B',
    fontSize: '13px',
  },
  occupied: {
    color: '#FF9500',
    fontWeight: '500',
  },
  free: {
    color: '#34C759',
    fontWeight: '500',
  },
  occupiedLabel: {
    flex: 1,
    padding: '8px',
    color: '#86868B',
    fontSize: '12px',
    textAlign: 'center',
  },
  cardActions: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
  },
  occupyBtn: {
    flex: 1,
    padding: '8px',
    backgroundColor: '#007AFF',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    cursor: 'pointer',
  },
  releaseBtn: {
    flex: 1,
    padding: '8px',
    backgroundColor: '#FF9500',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    cursor: 'pointer',
  },
  editBtn: {
    padding: '8px 12px',
    backgroundColor: '#F2F2F7',
    color: '#1D1D1F',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    cursor: 'pointer',
  },
  deleteBtn: {
    padding: '8px 12px',
    backgroundColor: '#FFEBE9',
    color: '#FF3B30',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    cursor: 'pointer',
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
  modal: {
    backgroundColor: 'white',
    borderRadius: '12px',
    width: '400px',
    maxWidth: '90%',
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
  },
  modalBody: {
    padding: '20px',
  },
  modalInfo: {
    fontSize: '13px',
    color: '#86868B',
    marginBottom: '8px',
  },
  field: {
    marginBottom: '16px',
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #D1D1D6',
    borderRadius: '8px',
    fontSize: '14px',
    outline: 'none',
    marginTop: '6px',
    boxSizing: 'border-box',
  },
  fileInput: {
    marginTop: '6px',
    fontSize: '13px',
  },
  modalActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
    padding: '16px 20px',
    borderTop: '1px solid #E5E5EA',
  },
  cancelBtn: {
    padding: '8px 16px',
    backgroundColor: '#F2F2F7',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    cursor: 'pointer',
  },
  saveBtn: {
    padding: '8px 16px',
    backgroundColor: '#007AFF',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    cursor: 'pointer',
  },
  previewOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 2000,
    cursor: 'pointer',
  },
  previewImage: {
    maxWidth: '90%',
    maxHeight: '90%',
    objectFit: 'contain',
    borderRadius: '8px',
  },
  previewCloseBtn: {
    position: 'absolute',
    top: '20px',
    right: '20px',
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    border: 'none',
    color: 'white',
    fontSize: '24px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  // 列表视图样式
  listContainer: {
    backgroundColor: 'white',
    borderRadius: '12px',
    overflow: 'hidden',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
  },
  listHeader: {
    display: 'grid',
    gridTemplateColumns: '100px 1fr 100px 120px 100px 140px 160px',
    padding: '10px 16px',
    backgroundColor: '#F9F9F9',
    borderBottom: '1px solid #E5E5EA',
    gap: '12px',
    fontSize: '12px',
    fontWeight: '500',
    color: '#86868B',
  },
  listHeaderImages: {},
  listHeaderName: {},
  listHeaderType: {},
  listHeaderVersion: {},
  listHeaderStatus: {},
  listHeaderEndTime: {},
  listHeaderActions: {
    textAlign: 'right',
  },
  listRow: {
    display: 'grid',
    gridTemplateColumns: '100px 1fr 100px 120px 100px 140px 160px',
    alignItems: 'center',
    padding: '12px 16px',
    borderBottom: '1px solid #F2F2F7',
    gap: '12px',
  },
  listImages: {
    display: 'flex',
    gap: '6px',
  },
  listImage: {
    width: '40px',
    height: '40px',
    objectFit: 'cover',
    borderRadius: '4px',
  },
  listNoImage: {
    width: '40px',
    height: '40px',
    backgroundColor: '#F2F2F7',
    borderRadius: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '12px',
    color: '#86868B',
  },
  listName: {
    fontWeight: '500',
    color: '#1D1D1F',
    fontSize: '14px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  listType: {
    fontSize: '12px',
    color: '#86868B',
  },
  listVersion: {
    fontSize: '13px',
    color: '#1D1D1F',
  },
  listStatus: {
    fontSize: '13px',
  },
  listEndTime: {
    fontSize: '13px',
    color: '#86868B',
  },
  listActions: {
    display: 'flex',
    gap: '6px',
    justifyContent: 'flex-end',
  },
  listOccupyBtn: {
    padding: '5px 12px',
    backgroundColor: '#007AFF',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer',
  },
  listReleaseBtn: {
    padding: '5px 12px',
    backgroundColor: '#FF9500',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer',
  },
  listEditBtn: {
    padding: '5px 12px',
    backgroundColor: '#F2F2F7',
    color: '#1D1D1F',
    border: 'none',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer',
  },
  listDeleteBtn: {
    padding: '5px 12px',
    backgroundColor: '#FFEBE9',
    color: '#FF3B30',
    border: 'none',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer',
  },
};

export default MobileDevicesPage;
