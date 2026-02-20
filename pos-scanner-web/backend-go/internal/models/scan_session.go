package models

import (
	"time"

	"gorm.io/gorm"
)

type ScanSession struct {
	ID          uint           `gorm:"primaryKey;default:1" json:"id"`
	LastScanAt  time.Time      `json:"last_scan_at"`
	DeletedAt   gorm.DeletedAt `gorm:"index" json:"-"`
}

func (ScanSession) TableName() string {
	return "scan_sessions"
}
