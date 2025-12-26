import React from 'react';

const ScanTable = ({ devices, onOpenDevice, onShowDetails, onRemarkChange }) => {
  const handleRemarkChange = (ip, remark) => {
    onRemarkChange(ip, remark);
    // 这里可以添加保存备注到后端的逻辑
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
            <th>备注</th>
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
                <input
                  type="text"
                  className="remark-input"
                  value={device.remark || ''}
                  onChange={(e) => handleRemarkChange(device.ip, e.target.value)}
                  placeholder="添加备注"
                />
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