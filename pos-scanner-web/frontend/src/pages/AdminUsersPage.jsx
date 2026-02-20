import React, { useState, useEffect } from 'react';
import { adminService } from '../services/authService';
import { deviceAPI } from '../services/api';
import axios from 'axios';

const API_BASE = '/api/admin';

const createAuthAxios = () => {
  const token = localStorage.getItem('access_token');
  return axios.create({
    baseURL: API_BASE,
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  });
};

const AdminUsersPage = () => {
  const [activeTab, setActiveTab] = useState('users'); // 'users' or 'claims'
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchText, setSearchText] = useState('');
  const [error, setError] = useState('');

  // 认领申请相关状态
  const [claims, setClaims] = useState([]);
  const [claimsLoading, setClaimsLoading] = useState(false);

  // 弹窗状态
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // create, edit
  const [selectedUser, setSelectedUser] = useState(null);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    name: '',
    password: '',
    role: 'user',
    status: 'approved'
  });

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const result = await adminService.getUsers(statusFilter);
      if (result.success && result.data) {
        const userList = result.data.users || result.users || [];
        setUsers(userList);
        setFilteredUsers(userList);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError('获取用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 搜索过滤
  useEffect(() => {
    if (!searchText.trim()) {
      setFilteredUsers(users);
    } else {
      const keyword = searchText.toLowerCase();
      const filtered = users.filter(user =>
        (user.username || '').toLowerCase().includes(keyword) ||
        (user.email || '').toLowerCase().includes(keyword) ||
        (user.name || '').toLowerCase().includes(keyword)
      );
      setFilteredUsers(filtered);
    }
  }, [searchText, users]);

  const fetchClaims = async () => {
    setClaimsLoading(true);
    try {
      const result = await deviceAPI.getClaims('pending');
      console.log('认领申请结果:', result);
      if (result.success) {
        setClaims(result.data?.claims || result.claims || []);
      } else {
        console.error('获取失败:', result.error);
      }
    } catch (err) {
      console.error('获取认领申请失败:', err);
    } finally {
      setClaimsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchClaims(); // 同时获取认领申请，用于显示数量
  }, [statusFilter]);

  useEffect(() => {
    if (activeTab === 'claims') {
      fetchClaims(); // 切换到认领审核tab时刷新
    }
  }, [activeTab]);

  // 打开创建弹窗
  const openCreateModal = () => {
    setModalMode('create');
    setSelectedUser(null);
    setFormData({
      username: '',
      email: '',
      name: '',
      password: '',
      role: 'user',
      status: 'approved'
    });
    setShowModal(true);
  };

  // 打开编辑弹窗
  const openEditModal = (user) => {
    setModalMode('edit');
    setSelectedUser(user);
    setFormData({
      username: user.username,
      email: user.email,
      name: user.name || '',
      password: '',
      role: user.role,
      status: user.status
    });
    setShowModal(true);
  };

  // 关闭弹窗
  const closeModal = () => {
    setShowModal(false);
    setSelectedUser(null);
  };

  // 创建/更新用户
  const handleSaveUser = async () => {
    if (!formData.username || !formData.name) {
      alert('用户名和姓名不能为空');
      return;
    }

    if (modalMode === 'create' && !formData.password) {
      alert('密码不能为空');
      return;
    }

    if (formData.password && formData.password.length < 6) {
      alert('密码至少6个字符');
      return;
    }

    try {
      const authAxios = createAuthAxios();

      if (modalMode === 'create') {
        await authAxios.post('/users', {
          username: formData.username,
          email: formData.email,
          name: formData.name,
          password: formData.password,
          role: formData.role,
          status: formData.status
        });
      } else {
        const updateData = {
          username: formData.username,
          email: formData.email,
          name: formData.name,
          role: formData.role,
          status: formData.status
        };
        await authAxios.put(`/users/${selectedUser.id}`, updateData);

        // 如果有新密码，单独重置
        if (formData.password) {
          await adminService.resetUserPassword(selectedUser.id, formData.password);
        }
      }

      fetchUsers();
      closeModal();
    } catch (err) {
      alert(err.response?.data?.error || '操作失败');
    }
  };

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

  // 认领审核处理
  const handleApproveClaim = async (claimId) => {
    try {
      const result = await deviceAPI.approveClaim(claimId);
      if (result.success) {
        alert(result.message || '审核通过');
        fetchClaims();
      } else {
        alert(result.error || '操作失败');
      }
    } catch (err) {
      alert('操作失败');
    }
  };

  const handleRejectClaim = async (claimId) => {
    if (!window.confirm('确定要拒绝此认领申请吗？')) return;
    try {
      const result = await deviceAPI.rejectClaim(claimId);
      if (result.success) {
        alert(result.message || '已拒绝');
        fetchClaims();
      } else {
        alert(result.error || '操作失败');
      }
    } catch (err) {
      alert('操作失败');
    }
  };

  const getStatusBadge = (status) => {
    const configs = {
      pending: { bg: 'rgba(255, 149, 0, 0.12)', color: '#FF9500', label: '待审核' },
      approved: { bg: 'rgba(52, 199, 89, 0.12)', color: '#34C759', label: '已通过' },
      rejected: { bg: 'rgba(255, 59, 48, 0.12)', color: '#FF3B30', label: '已拒绝' }
    };
    const config = configs[status];
    return (
      <span style={{
        padding: '4px 10px',
        borderRadius: '6px',
        fontSize: '12px',
        fontWeight: '500',
        backgroundColor: config.bg,
        color: config.color,
      }}>
        {config.label}
      </span>
    );
  };

  const formatTime = (isoString) => {
    if (!isoString) return '——';
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', {
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
          <h1 style={styles.title}>管理中心</h1>
          <p style={styles.subtitle}>审核注册申请、设备认领和管理用户账户</p>
        </div>
        <div style={styles.headerActions}>
          {activeTab === 'users' && (
            <button onClick={openCreateModal} style={styles.createBtn}>
              + 添加用户
            </button>
          )}
        </div>
      </div>

      {/* Tab 切换 */}
      <div style={styles.tabContainer}>
        <button
          style={{...styles.tab, ...(activeTab === 'users' ? styles.tabActive : {})}}
          onClick={() => setActiveTab('users')}
        >
          用户管理
        </button>
        <button
          style={{...styles.tab, ...(activeTab === 'claims' ? styles.tabActive : {})}}
          onClick={() => setActiveTab('claims')}
        >
          认领审核 {(claims || []).length > 0 && <span style={styles.badge}>{(claims || []).length}</span>}
        </button>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {/* 用户管理 Tab */}
      {activeTab === 'users' && (
        <>
          <div style={styles.filterCard}>
            <div style={styles.filterGroup}>
              <div style={styles.filter}>
                <label style={styles.filterLabel}>筛选状态</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  style={styles.select}
                >
                  <option value="all">全部</option>
                  <option value="pending">待审核</option>
                  <option value="approved">已通过</option>
                  <option value="rejected">已拒绝</option>
                </select>
              </div>
              <input
                type="text"
                placeholder="搜索用户名/邮箱..."
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                style={styles.searchInput}
              />
            </div>
            <div style={styles.stats}>
              <span style={styles.statItem}>共 {(filteredUsers || []).length} 个用户</span>
            </div>
          </div>

          {loading ? (
            <div style={styles.loading}>
              <div style={styles.spinner}></div>
              <span>加载中...</span>
            </div>
          ) : (filteredUsers || []).length === 0 ? (
            <div style={styles.empty}>
              <svg style={styles.emptyIcon} viewBox="0 0 24 24" fill="none">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" fill="currentColor"/>
              </svg>
              <p>{searchText ? '未找到匹配用户' : '暂无用户数据'}</p>
            </div>
          ) : (
            <div style={styles.tableContainer}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>ID</th>
                    <th style={styles.th}>姓名</th>
                    <th style={styles.th}>用户名</th>
                    <th style={styles.th}>邮箱</th>
                    <th style={styles.th}>角色</th>
                    <th style={styles.th}>状态</th>
                    <th style={styles.th}>注册时间</th>
                    <th style={styles.th}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((user) => (
                    <tr key={user.id} style={styles.tr}>
                      <td style={styles.td}>{user.id}</td>
                      <td style={{...styles.td, fontWeight: '500'}}>{user.name || user.username}</td>
                      <td style={styles.td}>{user.username}</td>
                      <td style={styles.td}>{user.email || '——'}</td>
                      <td style={styles.td}>
                        <span style={{
                          ...styles.roleBadge,
                          backgroundColor: user.role === 'admin' ? 'rgba(88, 86, 214, 0.12)' : 'rgba(0, 122, 255, 0.12)',
                          color: user.role === 'admin' ? '#5856D6' : '#007AFF',
                        }}>
                          {user.role === 'admin' ? '管理员' : '用户'}
                        </span>
                      </td>
                      <td style={styles.td}>{getStatusBadge(user.status)}</td>
                      <td style={styles.td}>{new Date(user.created_at).toLocaleString('zh-CN')}</td>
                      <td style={styles.td}>
                        <div style={styles.actions}>
                          <button onClick={() => openEditModal(user)} style={styles.btnEdit}>编辑</button>
                          {user.status === 'pending' && (
                            <>
                              <button onClick={() => handleApprove(user.id)} style={styles.btnApprove}>通过</button>
                              <button onClick={() => handleReject(user.id)} style={styles.btnReject}>拒绝</button>
                            </>
                          )}
                          <button onClick={() => handleDelete(user.id)} style={styles.btnDelete}>删除</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* 认领审核 Tab */}
      {activeTab === 'claims' && (
        <>
          <div style={styles.filterCard}>
            <div style={styles.filter}>
              <span style={styles.filterLabel}>待审核的设备认领申请</span>
            </div>
            <div style={styles.stats}>
              <span style={styles.statItem}>共 {(claims || []).length} 条申请</span>
            </div>
          </div>

          {claimsLoading ? (
            <div style={styles.loading}>
              <div style={styles.spinner}></div>
              <span>加载中...</span>
            </div>
          ) : (claims || []).length === 0 ? (
            <div style={styles.empty}>
              <svg style={styles.emptyIcon} viewBox="0 0 24 24" fill="none">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" fill="currentColor"/>
              </svg>
              <p>暂无待审核的认领申请</p>
            </div>
          ) : (
            <div style={styles.tableContainer}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>商家ID</th>
                    <th style={styles.th}>设备名称</th>
                    <th style={styles.th}>申请人</th>
                    <th style={styles.th}>申请时间</th>
                    <th style={styles.th}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {claims.map((claim) => (
                    <tr key={claim.id} style={styles.tr}>
                      <td style={{...styles.td, fontWeight: '500'}}>{claim.merchantId}</td>
                      <td style={styles.td}>{claim.deviceName}</td>
                      <td style={styles.td}>
                        <span style={{
                          ...styles.roleBadge,
                          backgroundColor: 'rgba(0, 122, 255, 0.12)',
                          color: '#007AFF',
                        }}>
                          {claim.username}
                        </span>
                      </td>
                      <td style={styles.td}>{formatTime(claim.createdAt)}</td>
                      <td style={styles.td}>
                        <div style={styles.actions}>
                          <button onClick={() => handleApproveClaim(claim.id)} style={styles.btnApprove}>通过</button>
                          <button onClick={() => handleRejectClaim(claim.id)} style={styles.btnReject}>拒绝</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* 用户编辑弹窗 */}
      {showModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.modal}>
            <div style={styles.modalHeader}>
              <h3>{modalMode === 'create' ? '添加用户' : '编辑用户'}</h3>
              <button onClick={closeModal} style={styles.closeBtn}>×</button>
            </div>
            <div style={styles.modalBody}>
              <div style={styles.field}>
                <label>用户名 *</label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={e => setFormData({ ...formData, username: e.target.value })}
                  style={styles.input}
                  placeholder="至少3个字符"
                />
              </div>
              <div style={styles.field}>
                <label>姓名 *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={e => setFormData({ ...formData, name: e.target.value })}
                  style={styles.input}
                  placeholder="真实姓名"
                />
              </div>
              <div style={styles.field}>
                <label>邮箱</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={e => setFormData({ ...formData, email: e.target.value })}
                  style={styles.input}
                  placeholder="user@example.com（选填）"
                />
              </div>
              <div style={styles.field}>
                <label>密码 {modalMode === 'create' ? '*' : '(留空不修改)'}</label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={e => setFormData({ ...formData, password: e.target.value })}
                  style={styles.input}
                  placeholder="至少6个字符"
                />
              </div>
              <div style={styles.field}>
                <label>角色</label>
                <select
                  value={formData.role}
                  onChange={e => setFormData({ ...formData, role: e.target.value })}
                  style={styles.input}
                >
                  <option value="user">普通用户</option>
                  <option value="admin">管理员</option>
                </select>
              </div>
              <div style={styles.field}>
                <label>状态</label>
                <select
                  value={formData.status}
                  onChange={e => setFormData({ ...formData, status: e.target.value })}
                  style={styles.input}
                >
                  <option value="pending">待审核</option>
                  <option value="approved">已通过</option>
                  <option value="rejected">已拒绝</option>
                </select>
              </div>
            </div>
            <div style={styles.modalActions}>
              <button onClick={closeModal} style={styles.btnCancel}>取消</button>
              <button onClick={handleSaveUser} style={styles.btnSave}>
                {modalMode === 'create' ? '创建' : '保存'}
              </button>
            </div>
          </div>
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
    marginBottom: '16px',
  },
  headerActions: {
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
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
  title: {
    fontSize: '20px',
    fontWeight: '600',
    color: '#1D1D1F',
    marginBottom: '2px',
    letterSpacing: '-0.01em',
  },
  subtitle: {
    fontSize: '13px',
    color: '#86868B',
  },
  tabContainer: {
    display: 'flex',
    gap: '4px',
    marginBottom: '12px',
    backgroundColor: '#F2F2F7',
    padding: '4px',
    borderRadius: '10px',
    width: 'fit-content',
  },
  tab: {
    padding: '8px 16px',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
    backgroundColor: 'transparent',
    color: '#86868B',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  tabActive: {
    backgroundColor: 'white',
    color: '#1D1D1F',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
  },
  badge: {
    backgroundColor: '#FF3B30',
    color: 'white',
    fontSize: '11px',
    padding: '2px 6px',
    borderRadius: '10px',
    fontWeight: '600',
  },
  error: {
    padding: '10px 14px',
    backgroundColor: '#FFF2F0',
    border: '1px solid #FFCCC7',
    borderRadius: '8px',
    color: '#FF4D4F',
    marginBottom: '12px',
    fontSize: '13px',
  },
  filterCard: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    backgroundColor: 'white',
    borderRadius: '10px',
    boxShadow: '0 1px 4px rgba(0, 0, 0, 0.04)',
    marginBottom: '12px',
  },
  filter: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  filterGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  searchInput: {
    padding: '6px 12px',
    border: '1px solid #D1D1D6',
    borderRadius: '8px',
    fontSize: '14px',
    width: '180px',
    outline: 'none',
  },
  filterLabel: {
    fontSize: '13px',
    fontWeight: '500',
    color: '#86868B',
  },
  select: {
    padding: '6px 12px',
    border: '1px solid #D1D1D6',
    borderRadius: '8px',
    fontSize: '14px',
    backgroundColor: 'white',
    cursor: 'pointer',
    minWidth: '100px',
  },
  stats: {
    display: 'flex',
    gap: '12px',
  },
  statItem: {
    fontSize: '13px',
    color: '#86868B',
  },
  loading: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px',
    color: '#86868B',
    gap: '12px',
    fontSize: '13px',
  },
  spinner: {
    width: '24px',
    height: '24px',
    border: '2px solid #E5E5EA',
    borderTopColor: '#007AFF',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px',
    color: '#86868B',
    gap: '8px',
    fontSize: '13px',
  },
  emptyIcon: {
    width: '36px',
    height: '36px',
    color: '#C7C7CC',
  },
  tableContainer: {
    backgroundColor: 'white',
    borderRadius: '10px',
    boxShadow: '0 1px 4px rgba(0, 0, 0, 0.04)',
    overflow: 'hidden',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  th: {
    padding: '10px 12px',
    textAlign: 'left',
    fontSize: '11px',
    fontWeight: '600',
    color: '#86868B',
    textTransform: 'uppercase',
    letterSpacing: '0.03em',
    backgroundColor: '#F2F2F7',
    borderBottom: '1px solid #E5E5EA',
  },
  tr: {
    transition: 'background-color 0.15s ease',
  },
  td: {
    padding: '10px 12px',
    borderBottom: '1px solid #F2F2F7',
    fontSize: '13px',
    color: '#1D1D1F',
  },
  roleBadge: {
    padding: '3px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '500',
  },
  actions: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap',
  },
  btnEdit: {
    padding: '4px 10px',
    backgroundColor: '#5856D6',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '500',
    cursor: 'pointer',
  },
  btnApprove: {
    padding: '4px 10px',
    backgroundColor: '#34C759',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '500',
    cursor: 'pointer',
  },
  btnReject: {
    padding: '4px 10px',
    backgroundColor: '#FF3B30',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '500',
    cursor: 'pointer',
  },
  btnDelete: {
    padding: '4px 10px',
    backgroundColor: '#8E8E93',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '500',
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
  modalActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
    padding: '16px 20px',
    borderTop: '1px solid #E5E5EA',
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
};

// Add spinner animation
const styleSheet = document.createElement('style');
styleSheet.textContent = `
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;
document.head.appendChild(styleSheet);

export default AdminUsersPage;
