import React from 'react';

const ScanTable = ({ devices = [], onOpenDevice, onShowDetails, onEditProperty, onEditOccupancy, onDeleteDevice, onClaimDevice, onResetOwner, isAdmin, currentUserId }) => {
  // 格式化时间显示
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

  // 格式化上次在线时间
  const formatLastOnlineTime = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="scan-table-container">
      <table className="scan-table">
        <thead>
          <tr>
            <th>IP</th>
            <th>类型</th>
            <th>商家ID</th>
            <th>名称</th>
            <th>版本</th>
            <th>分类</th>
            <th>负责人</th>
            <th>借用状态</th>
            <th>归还时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {devices.map((device, index) => (
            <tr key={device.id || `${device.ip}-${device.merchantId || index}`} className={index % 2 === 0 ? 'even' : 'odd'}>
              <td>
                <div className="ip-cell">
                  <span className="ip-address">{device.ip}</span>
                  {device.isOnline === true ? (
                    device.merchantId ? (
                      <span className="online-indicator" title="在线"></span>
                    ) : (
                      <span className="error-indicator" title="服务不可用"></span>
                    )
                  ) : device.isOnline === false ? (
                    <span className="offline-label">
                      (离线: {formatLastOnlineTime(device.lastOnlineTime)})
                    </span>
                  ) : null}
                </div>
              </td>
              <td>{device.type || '——'}</td>
              <td>{device.merchantId || (device.name && device.version ? 'Free Trials' : '——')}</td>
              <td>{device.name || '——'}</td>
              <td>{device.version || '——'}</td>
              <td>
                {device.property ? (
                  <span className="property-tag">{device.property}</span>
                ) : (
                  <span className="property-empty">——</span>
                )}
                {isAdmin && device.merchantId && (
                  <button
                    className="btn-edit-property"
                    onClick={() => onEditProperty(device)}
                    title="编辑分类"
                  >
                    ✏️
                  </button>
                )}
              </td>
              <td>
                {device.owner ? (
                  <div className="owner-cell">
                    <span className="owner-name">{device.owner.username}</span>
                    {isAdmin && (
                      <button
                        className="btn-reset-owner"
                        onClick={() => onResetOwner(device)}
                        title="重置负责人"
                      >
                        ×
                      </button>
                    )}
                  </div>
                ) : device.merchantId ? (
                  <button
                    className="btn btn-sm btn-claim"
                    onClick={() => onClaimDevice(device)}
                  >
                    认领
                  </button>
                ) : (
                  <span className="property-empty">——</span>
                )}
              </td>
              <td>
                {device.isOccupied ? (
                  <span
                    className="occupancy-occupied"
                    onClick={() => onEditOccupancy(device)}
                    title={`用途: ${device.occupancy?.purpose || '无'}`}
                  >
                    {device.occupancy?.username}
                  </span>
                ) : (
                  <span
                    className="occupancy-free"
                    onClick={() => device.merchantId && onEditOccupancy(device)}
                    style={{ cursor: device.merchantId ? 'pointer' : 'default' }}
                  >
                    可借用
                  </span>
                )}
              </td>
              <td>
                {device.isOccupied ? (
                  <span className="release-time">{formatTime(device.occupancy?.endTime)}</span>
                ) : (
                  <span className="property-empty">——</span>
                )}
              </td>
              <td>
                <div className="action-buttons">
                  {device.isOnline && device.merchantId ? (
                    <>
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={() => onOpenDevice(device.ip)}
                      >
                        打开
                      </button>
                      <button
                        className="btn btn-sm btn-success"
                        onClick={() => onShowDetails(device)}
                      >
                        详情
                      </button>
                    </>
                  ) : device.isOnline && !device.merchantId ? (
                    <span className="service-unavailable">服务不可用</span>
                  ) : !device.isOnline && isAdmin && device.merchantId ? (
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => onDeleteDevice(device)}
                      title="删除此离线设备"
                    >
                      删除
                    </button>
                  ) : !device.isOnline ? (
                    <span className="offline-label">离线</span>
                  ) : (
                    <span className="property-empty">——</span>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ScanTable;
