import React from 'react';

const SearchBar = ({
  searchIP,
  searchID,
  searchName,
  searchVersion,
  onSearchChange,
  onSearch,
  onClear
}) => {
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      onSearch();
    }
  };

  return (
    <div className="search-bar">
      <div className="search-fields">
        <div className="search-field">
          <label>IP:</label>
          <input
            type="text"
            value={searchIP}
            onChange={(e) => onSearchChange('ip', e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入IP"
          />
        </div>

        <div className="search-field">
          <label>商家ID:</label>
          <input
            type="text"
            value={searchID}
            onChange={(e) => onSearchChange('id', e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入商家ID"
          />
        </div>

        <div className="search-field">
          <label>商家名称:</label>
          <input
            type="text"
            value={searchName}
            onChange={(e) => onSearchChange('name', e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入商家名称"
          />
        </div>

        <div className="search-field">
          <label>版本:</label>
          <input
            type="text"
            value={searchVersion}
            onChange={(e) => onSearchChange('version', e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入版本"
          />
        </div>
      </div>

      <div className="search-buttons">
        <button className="btn btn-primary" onClick={onSearch}>
          搜索
        </button>
        <button className="btn btn-secondary" onClick={onClear}>
          清除
        </button>
      </div>
    </div>
  );
};

export default SearchBar;