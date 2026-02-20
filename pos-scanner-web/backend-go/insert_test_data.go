package main

import (
	"fmt"
	"log"
	"os"
	"time"

	"github.com/glebarez/sqlite"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

type User struct {
	ID           uint   `gorm:"primaryKey"`
	Username     string `gorm:"unique;not null"`
	PasswordHash string `gorm:"not null"`
	Email        *string
	Name         *string
	Role         string `gorm:"default:user"`
	Status       string `gorm:"default:pending"`
	CreatedAt    time.Time
	UpdatedAt    time.Time
}

type ScanResult struct {
	ID         uint   `gorm:"primaryKey"`
	IP         string `gorm:"unique;not null"`
	MerchantID *string
	Name       *string
	Version    *string
	Type       *string
	OwnerID    *uint
	CreatedAt  time.Time
	UpdatedAt  time.Time
}

type DeviceProperty struct {
	ID         uint   `gorm:"primaryKey"`
	MerchantID string `gorm:"unique;not null"`
	Property   string
}

type MobileDevice struct {
	ID            uint   `gorm:"primaryKey"`
	Name          string `gorm:"not null"`
	DeviceType    string
	SN            string
	SystemVersion string
	ImageA        string
	ImageB        string
	CreatedAt     time.Time
	UpdatedAt     time.Time
}

func main() {
	db, err := gorm.Open(sqlite.Open("data.db"), &gorm.Config{})
	if err != nil {
		log.Fatal("Failed to connect database:", err)
	}

	// 自动迁移表结构
	db.AutoMigrate(&User{}, &ScanResult{}, &DeviceProperty{}, &MobileDevice{})

	// 创建测试用户
	hashedPassword, _ := bcrypt.GenerateFromPassword([]byte("test123"), bcrypt.DefaultCost)
	testEmail := "test@example.com"
	testName := "测试用户"
	
	user := User{Username: "testuser", PasswordHash: string(hashedPassword), Email: &testEmail, Name: &testName, Role: "user", Status: "approved"}
	if err := db.Where("username = ?", "testuser").First(&User{}).Error; err != nil {
		db.Create(&user)
		fmt.Println("Created user: testuser")
	}

	// 创建测试 POS 设备
	merchantID1 := "M001"
	name1 := "测试店铺1"
	version1 := "1.0.0"
	deviceType1 := "Android"
	
	merchantID2 := "M002"
	name2 := "测试店铺2"
	version2 := "2.0.0"
	deviceType2 := "Windows"
	
	scanResults := []ScanResult{
		{IP: "192.168.1.100", MerchantID: &merchantID1, Name: &name1, Version: &version1, Type: &deviceType1},
		{IP: "192.168.1.101", MerchantID: &merchantID2, Name: &name2, Version: &version2, Type: &deviceType2},
		{IP: "192.168.1.102", MerchantID: nil, Name: nil, Version: nil, Type: nil},
	}
	
	for _, result := range scanResults {
		var existing ScanResult
		if err := db.Where("ip = ?", result.IP).First(&existing).Error; err != nil {
			db.Create(&result)
			fmt.Printf("Created scan result: %s\n", result.IP)
		}
	}

	// 创建测试设备性质
	properties := []DeviceProperty{
		{MerchantID: "M001", Property: "PC"},
		{MerchantID: "M002", Property: "移动端"},
	}
	
	for _, prop := range properties {
		var existing DeviceProperty
		if err := db.Where("merchant_id = ?", prop.MerchantID).First(&existing).Error; err != nil {
			db.Create(&prop)
			fmt.Printf("Created property: %s\n", prop.MerchantID)
		}
	}

	// 创建测试移动设备
	mobileDevices := []MobileDevice{
		{Name: "iPhone 14 Pro", DeviceType: "手机", SN: "SN001", SystemVersion: "iOS 17.0"},
		{Name: "iPad Pro", DeviceType: "平板", SN: "SN002", SystemVersion: "iPadOS 17.0"},
		{Name: "Samsung Galaxy S23", DeviceType: "手机", SN: "SN003", SystemVersion: "Android 14"},
	}
	
	for _, device := range mobileDevices {
		var existing MobileDevice
		if err := db.Where("sn = ?", device.SN).First(&existing).Error; err != nil {
			db.Create(&device)
			fmt.Printf("Created mobile device: %s\n", device.Name)
		}
	}

	fmt.Println("Test data inserted successfully!")
	os.Exit(0)
}
