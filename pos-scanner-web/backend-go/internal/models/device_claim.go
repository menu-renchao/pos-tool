package models

import (
	"time"

	"gorm.io/gorm"
)

type DeviceClaim struct {
	ID          uint           `gorm:"primaryKey" json:"id"`
	MerchantID  string         `gorm:"size:100;not null;index" json:"merchant_id"`
	UserID      uint           `gorm:"not null;index" json:"user_id"`
	Status      string         `gorm:"size:20;default:pending" json:"status"` // pending, approved, rejected
	CreatedAt   time.Time      `json:"created_at"`
	ProcessedAt *time.Time     `json:"processed_at"`
	ProcessedBy *uint          `json:"processed_by"`
	DeletedAt   gorm.DeletedAt `gorm:"index" json:"-"`
}

func (DeviceClaim) TableName() string {
	return "device_claims"
}

func (d *DeviceClaim) ToDict() map[string]interface{} {
	result := map[string]interface{}{
		"id":          d.ID,
		"merchantId":  d.MerchantID,
		"userId":      d.UserID,
		"status":      d.Status,
		"createdAt":   d.CreatedAt.Format(time.RFC3339),
		"processedAt": nil,
	}
	if d.ProcessedAt != nil {
		result["processedAt"] = d.ProcessedAt.Format(time.RFC3339)
	}
	return result
}
