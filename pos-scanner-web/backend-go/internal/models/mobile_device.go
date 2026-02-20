package models

import (
	"time"

	"gorm.io/gorm"
)

type MobileDevice struct {
	ID            uint           `gorm:"primaryKey" json:"id"`
	Name          string         `gorm:"size:200;not null" json:"name"`
	DeviceType    *string        `gorm:"size:100" json:"device_type"`
	SN            *string        `gorm:"size:100" json:"sn"`
	ImageA        *string        `gorm:"size:500" json:"image_a"`
	ImageB        *string        `gorm:"size:500" json:"image_b"`
	SystemVersion *string        `gorm:"size:100" json:"system_version"`
	CreatedAt     time.Time      `json:"created_at"`
	UpdatedAt     time.Time      `json:"updated_at"`
	OccupierID    *uint          `gorm:"index" json:"occupier_id"`
	Purpose       *string        `gorm:"size:500" json:"purpose"`
	StartTime     *time.Time     `json:"start_time"`
	EndTime       *time.Time     `json:"end_time"`
	Occupier      *User          `gorm:"foreignKey:OccupierID" json:"-"`
	DeletedAt     gorm.DeletedAt `gorm:"index" json:"-"`
}

func (MobileDevice) TableName() string {
	return "mobile_devices"
}

func (m *MobileDevice) ToDict() map[string]interface{} {
	isOccupied := false
	if m.EndTime != nil && m.EndTime.After(time.Now()) {
		isOccupied = true
	}

	occupier := ""
	if m.Occupier != nil {
		if m.Occupier.Name != nil && *m.Occupier.Name != "" {
			occupier = *m.Occupier.Name
		} else {
			occupier = m.Occupier.Username
		}
	}

	result := map[string]interface{}{
		"id":            m.ID,
		"name":          m.Name,
		"deviceType":    m.DeviceType,
		"sn":            m.SN,
		"imageA":        m.ImageA,
		"imageB":        m.ImageB,
		"systemVersion": m.SystemVersion,
		"createdAt":     m.CreatedAt.Format(time.RFC3339),
		"updatedAt":     m.UpdatedAt.Format(time.RFC3339),
		"isOccupied":    isOccupied,
		"occupier":      occupier,
		"occupierId":    m.OccupierID,
		"purpose":       m.Purpose,
	}

	if m.StartTime != nil {
		result["startTime"] = m.StartTime.Format(time.RFC3339)
	} else {
		result["startTime"] = nil
	}

	if m.EndTime != nil {
		result["endTime"] = m.EndTime.Format(time.RFC3339)
	} else {
		result["endTime"] = nil
	}

	return result
}
