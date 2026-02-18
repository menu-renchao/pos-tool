import React from 'react';

const ScanTable = ({ devices, onOpenDevice, onShowDetails, onEditProperty, onEditOccupancy, isAdmin }) => {
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

  return (
    <div className="scan-table-container">
      <table className="scan-table">
        <thead>
          <tr>
            <th>IP</th>
            <th>设备类型</th>
            <th>商家ID</th>
            <th>名称</th>
            <th>版本</th>
            <th>设备性质</th>
            <th>占用状态</th>
            <th>释放时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {devices.map((device, index) => (
            <tr key={device.ip} className={index % 2 === 0 ? 'even' : 'odd'}>
              <td>{device.ip}</td>
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
                    title="编辑设备性质"
                  >
                    ✏️
                  </button>
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
                    空闲
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
                  {device.merchantId || device.name ? (
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
                  ) : (
                    <span className="offline-label">POS已离线</span>
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