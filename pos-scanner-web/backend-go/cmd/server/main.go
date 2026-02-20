package main

import (
	"fmt"
	"log"

	"pos-scanner-backend/internal/config"
	"pos-scanner-backend/internal/handlers"
	"pos-scanner-backend/internal/middleware"
	"pos-scanner-backend/internal/models"
	"pos-scanner-backend/internal/repository"
	"pos-scanner-backend/internal/services"

	"github.com/gin-gonic/gin"
	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
)

func main() {
	// Initialize config
	if err := config.Init(); err != nil {
		log.Fatalf("Failed to initialize config: %v", err)
	}

	// Set Gin mode
	gin.SetMode(config.AppConfig.Server.Mode)

	// Initialize database
	db, err := gorm.Open(sqlite.Open(config.AppConfig.Database.Path), &gorm.Config{})
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}

	// Auto migrate
	if err := db.AutoMigrate(
		&models.User{},
		&models.ScanResult{},
		&models.DeviceProperty{},
		&models.DeviceOccupancy{},
		&models.DeviceClaim{},
		&models.MobileDevice{},
		&models.ScanSession{},
	); err != nil {
		log.Fatalf("Failed to migrate database: %v", err)
	}

	// Create default admin if not exists
	var adminCount int64
	db.Model(&models.User{}).Where("username = ?", "admin").Count(&adminCount)
	if adminCount == 0 {
		adminName := "admin"
		adminEmail := "admin@example.com"
		admin := &models.User{
			Username: "admin",
			Email:    &adminEmail,
			Name:     &adminName,
			Role:     "admin",
			Status:   "approved",
		}
		if err := admin.SetPassword("admin123"); err != nil {
			log.Fatalf("Failed to set admin password: %v", err)
		}
		if err := db.Create(admin).Error; err != nil {
			log.Fatalf("Failed to create admin: %v", err)
		}
		log.Println("Default admin user created")
	}

	// Initialize repositories
	userRepo := repository.NewUserRepository(db)
	deviceRepo := repository.NewDeviceRepository(db)
	mobileRepo := repository.NewMobileRepository(db)

	// Initialize services
	authService := services.NewAuthService(userRepo)
	scanService := services.NewScanService()

	// Initialize handlers
	authHandler := handlers.NewAuthHandler(authService, userRepo)
	adminHandler := handlers.NewAdminHandler(userRepo, deviceRepo)
	deviceHandler := handlers.NewDeviceHandler(deviceRepo, userRepo)
	mobileHandler := handlers.NewMobileHandler(mobileRepo, userRepo)
	scanHandler := handlers.NewScanHandler(scanService, deviceRepo)

	// Create Gin router
	router := gin.New()
	router.Use(gin.Logger())
	router.Use(gin.Recovery())
	router.Use(middleware.CORS())

	// API routes
	api := router.Group("/api")
	{
		// Auth routes
		auth := api.Group("/auth")
		{
			auth.POST("/register", authHandler.Register)
			auth.POST("/login", authHandler.Login)
			auth.POST("/logout", middleware.Auth(), authHandler.Logout)
			auth.GET("/profile", middleware.Auth(), authHandler.Profile)
			auth.PUT("/password", middleware.Auth(), authHandler.ChangePassword)
		}

		// Admin routes
		admin := api.Group("/admin")
		admin.Use(middleware.Auth())
		admin.Use(middleware.AdminOnly(userRepo))
		{
			admin.GET("/users", adminHandler.GetUsers)
			admin.POST("/users", adminHandler.CreateUser)
			admin.PUT("/users/:id", adminHandler.UpdateUser)
			admin.PUT("/users/:id/approve", adminHandler.ApproveUser)
			admin.PUT("/users/:id/reject", adminHandler.RejectUser)
			admin.PUT("/users/:id/reset-password", adminHandler.ResetUserPassword)
			admin.DELETE("/users/:id", adminHandler.DeleteUser)
			admin.GET("/device-properties", adminHandler.GetDeviceProperties)
			admin.PUT("/device-properties", adminHandler.SetDeviceProperty)
			admin.DELETE("/device-properties/:merchant_id", adminHandler.DeleteDeviceProperty)
		}

		// Device routes
		device := api.Group("/device")
		device.Use(middleware.Auth())
		{
			device.GET("/occupancy", deviceHandler.GetOccupancies)
			device.PUT("/occupancy", deviceHandler.SetOccupancy)
			device.DELETE("/occupancy/:merchant_id", deviceHandler.ReleaseOccupancy)
			device.POST("/claim", deviceHandler.SubmitClaim)
			device.GET("/claims", deviceHandler.GetClaims)
			device.POST("/claim/:id/approve", middleware.AdminOnly(userRepo), deviceHandler.ApproveClaim)
			device.POST("/claim/:id/reject", middleware.AdminOnly(userRepo), deviceHandler.RejectClaim)
			device.DELETE("/:merchant_id/owner", middleware.AdminOnly(userRepo), deviceHandler.ResetOwner)
			device.DELETE("/:merchant_id", middleware.AdminOnly(userRepo), deviceHandler.DeleteDevice)
		}

		// Mobile device routes
		mobile := api.Group("/mobile")
		mobile.Use(middleware.Auth())
		{
			mobile.GET("/devices", mobileHandler.GetDevices)
			mobile.POST("/devices", middleware.AdminOnly(userRepo), mobileHandler.CreateDevice)
			mobile.PUT("/devices/:id", middleware.AdminOnly(userRepo), mobileHandler.UpdateDevice)
			mobile.DELETE("/devices/:id", middleware.AdminOnly(userRepo), mobileHandler.DeleteDevice)
			mobile.POST("/devices/:id/upload", middleware.AdminOnly(userRepo), mobileHandler.UploadImage)
			mobile.PUT("/devices/:id/occupy", mobileHandler.OccupyDevice)
			mobile.PUT("/devices/:id/release", mobileHandler.ReleaseDevice)
		}

		// Scan routes (no auth required for basic scanning)
		scan := api.Group("/scan")
		{
			scan.GET("/ips", scanHandler.GetLocalIPs)
			scan.POST("/start", scanHandler.StartScan)
			scan.GET("/status", scanHandler.GetScanStatus)
			scan.POST("/stop", scanHandler.StopScan)
			scan.GET("/device/:ip/details", scanHandler.GetDeviceDetails)
		}

		// Devices list (main endpoint for frontend)
		api.GET("/devices", middleware.Auth(), deviceHandler.GetDevices)
	}

	// Static files for uploads
	router.Static("/uploads", config.AppConfig.Upload.Path)

	// Start server
	port := config.AppConfig.Server.Port
	if port == "" {
		port = "5000"
	}

	fmt.Printf("Server starting on port %s...\n", port)
	if err := router.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
