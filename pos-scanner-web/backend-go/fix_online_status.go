package main

import (
	"fmt"
	"log"

	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
)

type ScanResult struct {
	ID       uint   `gorm:"primaryKey"`
	IP       string `gorm:"size:50;not null"`
	IsOnline bool   `gorm:"default:true"`
}

func (ScanResult) TableName() string {
	return "scan_results"
}

func main() {
	db, err := gorm.Open(sqlite.Open("data.db"), &gorm.Config{})
	if err != nil {
		log.Fatal("Failed to connect database:", err)
	}

	// 更新所有设备的在线状态为 true
	result := db.Model(&ScanResult{}).Where("1 = 1").Update("is_online", true)
	if result.Error != nil {
		log.Fatal("Failed to update:", result.Error)
	}

	fmt.Printf("Updated %d devices to online\n", result.RowsAffected)
}
