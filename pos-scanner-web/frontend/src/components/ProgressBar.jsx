import React from 'react';

const ProgressBar = ({ progress, currentIP, isScanning }) => {
  return (
    <div className="progress-container">
      <div className="progress-header">
        <span className="progress-text">
          {isScanning ? `正在扫描: ${currentIP} (${progress}%)` : '准备扫描...'}
        </span>
        <span className="progress-percent">{progress}%</span>
      </div>
      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${progress}%` }}
        ></div>
      </div>
    </div>
  );
};

export default ProgressBar;