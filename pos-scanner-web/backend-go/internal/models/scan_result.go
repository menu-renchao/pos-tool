package models

import (
	"time"

	"gorm.io/gorm"
)

type ScanResult struct {
	ID             uint           `gorm:"primaryKey" json:"id"`
	IP             string         `gorm:"size:50;not null" json:"ip"`
	MerchantID     *string        `gorm:"size:100;index" json:"merchant_id"`
	Name           *string        `gorm:"size:200" json:"name"`
	Version        *string        `gorm:"size:50" json:"version"`
	Type           *string        `gorm:"size:50" json:"type"`
	FullData       *string        `gorm:"type:text" json:"full_data"`
	ScannedAt      time.Time      `json:"scanned_at"`
	IsOnline       bool           `gorm:"default:true" json:"is_online"`
	LastOnlineTime time.Time      `json:"last_online_time"`
	OwnerID        *uint          `gorm:"index" json:"owner_id"`
	DeletedAt      gorm.DeletedAt `gorm:"index" json:"-"`
}

func (ScanResult) TableName() string {
	return "scan_results"
}

func (s *ScanResult) ToDict() map[string]interface{} {
	merchantID := ""
	if s.MerchantID != nil {
		merchantID = *s.MerchantID
	}

	status := "error"
	if merchantID != "" {
		status = "success"
	}

	result := map[string]interface{}{
		"ip":              s.IP,
		"merchantId":      merchantID,
		"name":            s.Name,
		"version":         s.Version,
		"type":            s.Type,
		"status":          status,
		"fullData":        s.FullData,
		"isOnline":        s.IsOnline,
		"lastOnlineTime":  s.LastOnlineTime.Format(time.RFC3339),
		"ownerId":         s.OwnerID,
	}
	return result
}
