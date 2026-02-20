package models

import (
	"time"

	"gorm.io/gorm"
)

type DeviceProperty struct {
	ID         uint           `gorm:"primaryKey" json:"id"`
	MerchantID string         `gorm:"size:100;uniqueIndex;not null" json:"merchant_id"`
	Property   string         `gorm:"size:100;not null" json:"property"`
	UpdatedAt  time.Time      `json:"updated_at"`
	DeletedAt  gorm.DeletedAt `gorm:"index" json:"-"`
}

func (DeviceProperty) TableName() string {
	return "device_properties"
}

func (d *DeviceProperty) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"merchantId": d.MerchantID,
		"property":   d.Property,
		"updatedAt":  d.UpdatedAt.Format(time.RFC3339),
	}
}
