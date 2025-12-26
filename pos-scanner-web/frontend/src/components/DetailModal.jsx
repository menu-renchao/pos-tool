import React from 'react';

const DetailModal = ({ device, onClose }) => {
  if (!device) return null;

  const renderData = (data, indent = 0) => {
    if (typeof data === 'object' && data !== null) {
      return (
        <div style={{ marginLeft: `${indent * 20}px` }}>
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="data-row">
              <strong>{key}:</strong>
              {typeof value === 'object' ? renderData(value, indent + 1) : <span>{String(value)}</span>}
            </div>
          ))}
        </div>
      );
    }
    return <span>{String(data)}</span>;
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>设备详情 - {device.ip}</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          {device.fullData ? (
            renderData(device.fullData)
          ) : (
            <p>无数据</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default DetailModal;