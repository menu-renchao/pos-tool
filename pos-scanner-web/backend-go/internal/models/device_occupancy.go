package models

import (
	"time"

	"gorm.io/gorm"
)

type DeviceOccupancy struct {
	ID         uint           `gorm:"primaryKey" json:"id"`
	MerchantID string         `gorm:"size:100;uniqueIndex;not null" json:"merchant_id"`
	UserID     uint           `gorm:"not null;index" json:"user_id"`
	Purpose    *string        `gorm:"size:500" json:"purpose"`
	StartTime  time.Time      `json:"start_time"`
	EndTime    time.Time      `json:"end_time"`
	CreatedAt  time.Time      `json:"created_at"`
	User       *User          `gorm:"foreignKey:UserID" json:"-"`
	DeletedAt  gorm.DeletedAt `gorm:"index" json:"-"`
}

func (DeviceOccupancy) TableName() string {
	return "device_occupancies"
}

func (d *DeviceOccupancy) ToDict() map[string]interface{} {
	username := ""
	if d.User != nil {
		if d.User.Name != nil && *d.User.Name != "" {
			username = *d.User.Name
		} else {
			username = d.User.Username
		}
	}

	result := map[string]interface{}{
		"merchantId": d.MerchantID,
		"userId":     d.UserID,
		"username":   username,
		"purpose":    d.Purpose,
		"startTime":  d.StartTime.Format(time.RFC3339),
		"endTime":    d.EndTime.Format(time.RFC3339),
		"createdAt":  d.CreatedAt.Format(time.RFC3339),
	}
	return result
}
