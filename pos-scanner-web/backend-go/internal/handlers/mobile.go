package handlers

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"pos-scanner-backend/internal/config"
	"pos-scanner-backend/internal/middleware"
	"pos-scanner-backend/internal/models"
	"pos-scanner-backend/internal/repository"
	"pos-scanner-backend/pkg/response"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type MobileHandler struct {
	mobileRepo *repository.MobileRepository
	userRepo   *repository.UserRepository
}

func NewMobileHandler(mobileRepo *repository.MobileRepository, userRepo *repository.UserRepository) *MobileHandler {
	return &MobileHandler{
		mobileRepo: mobileRepo,
		userRepo:   userRepo,
	}
}

type CreateMobileDeviceRequest struct {
	Name          string `json:"name" binding:"required"`
	DeviceType    string `json:"deviceType"`
	SN            string `json:"sn"`
	SystemVersion string `json:"systemVersion"`
}

type UpdateMobileDeviceRequest struct {
	Name          string `json:"name"`
	DeviceType    string `json:"deviceType"`
	SN            string `json:"sn"`
	SystemVersion string `json:"systemVersion"`
	ImageA        string `json:"imageA"`
	ImageB        string `json:"imageB"`
}

type OccupyMobileDeviceRequest struct {
	Purpose string `json:"purpose"`
	EndTime string `json:"endTime" binding:"required"`
}

// GetDevices returns all mobile devices
func (h *MobileHandler) GetDevices(c *gin.Context) {
	// Cleanup expired occupancies
	h.mobileRepo.CleanupExpiredOccupancies()

	devices, err := h.mobileRepo.List()
	if err != nil {
		response.InternalError(c, "Failed to get devices")
		return
	}

	deviceDicts := make([]map[string]interface{}, len(devices))
	for i, d := range devices {
		deviceDicts[i] = d.ToDict()
	}

	response.Success(c, gin.H{"devices": deviceDicts})
}

// CreateDevice creates a new mobile device
func (h *MobileHandler) CreateDevice(c *gin.Context) {
	var req CreateMobileDeviceRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, "Invalid request")
		return
	}

	if req.Name == "" {
		response.BadRequest(c, "Device name cannot be empty")
		return
	}

	var deviceType, sn, systemVersion *string
	if req.DeviceType != "" {
		deviceType = &req.DeviceType
	}
	if req.SN != "" {
		sn = &req.SN
	}
	if req.SystemVersion != "" {
		systemVersion = &req.SystemVersion
	}

	device := &models.MobileDevice{
		Name:          req.Name,
		DeviceType:    deviceType,
		SN:            sn,
		SystemVersion: systemVersion,
	}

	if err := h.mobileRepo.Create(device); err != nil {
		response.InternalError(c, "Failed to create device")
		return
	}

	// Reload with occupier
	device, _ = h.mobileRepo.GetByID(device.ID)

	response.CreatedWithMessage(c, "Device created successfully", gin.H{"device": device.ToDict()})
}

// UpdateDevice updates a mobile device
func (h *MobileHandler) UpdateDevice(c *gin.Context) {
	deviceID, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		response.BadRequest(c, "Invalid device ID")
		return
	}

	device, err := h.mobileRepo.GetByID(uint(deviceID))
	if err != nil {
		response.NotFound(c, "Device not found")
		return
	}

	var req UpdateMobileDeviceRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, "Invalid request")
		return
	}

	if req.Name != "" {
		device.Name = req.Name
	}
	if req.DeviceType != "" {
		device.DeviceType = &req.DeviceType
	}
	if req.SN != "" {
		device.SN = &req.SN
	}
	if req.SystemVersion != "" {
		device.SystemVersion = &req.SystemVersion
	}
	if req.ImageA != "" {
		device.ImageA = &req.ImageA
	}
	if req.ImageB != "" {
		device.ImageB = &req.ImageB
	}

	device.UpdatedAt = time.Now()

	if err := h.mobileRepo.Update(device); err != nil {
		response.InternalError(c, "Failed to update device")
		return
	}

	// Reload
	device, _ = h.mobileRepo.GetByID(device.ID)

	response.SuccessWithMessage(c, "Device updated successfully", gin.H{"device": device.ToDict()})
}

// DeleteDevice deletes a mobile device
func (h *MobileHandler) DeleteDevice(c *gin.Context) {
	deviceID, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		response.BadRequest(c, "Invalid device ID")
		return
	}

	device, err := h.mobileRepo.GetByID(uint(deviceID))
	if err != nil {
		response.NotFound(c, "Device not found")
		return
	}

	// Delete associated images
	if device.ImageA != nil && *device.ImageA != "" {
		imagePath := filepath.Join(config.AppConfig.Upload.Path, *device.ImageA)
		os.Remove(imagePath)
	}
	if device.ImageB != nil && *device.ImageB != "" {
		imagePath := filepath.Join(config.AppConfig.Upload.Path, *device.ImageB)
		os.Remove(imagePath)
	}

	if err := h.mobileRepo.Delete(uint(deviceID)); err != nil {
		response.InternalError(c, "Failed to delete device")
		return
	}

	response.SuccessWithMessage(c, "Device deleted", nil)
}

// UploadImage uploads an image for a mobile device
func (h *MobileHandler) UploadImage(c *gin.Context) {
	deviceID, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		response.BadRequest(c, "Invalid device ID")
		return
	}

	device, err := h.mobileRepo.GetByID(uint(deviceID))
	if err != nil {
		response.NotFound(c, "Device not found")
		return
	}

	file, err := c.FormFile("image")
	if err != nil {
		response.BadRequest(c, "No image uploaded")
		return
	}

	imageType := c.DefaultPostForm("type", "a")
	if imageType != "a" && imageType != "b" {
		imageType = "a"
	}

	// Check file extension
	ext := strings.ToLower(filepath.Ext(file.Filename))
	if ext != ".png" && ext != ".jpg" && ext != ".jpeg" && ext != ".gif" {
		response.BadRequest(c, "Unsupported file format")
		return
	}

	// Create upload directory
	uploadDir := filepath.Join(config.AppConfig.Upload.Path, "mobile_devices")
	if err := os.MkdirAll(uploadDir, 0755); err != nil {
		response.InternalError(c, "Failed to create upload directory")
		return
	}

	// Generate unique filename
	filename := fmt.Sprintf("%d_%s_%s%s", deviceID, imageType, uuid.New().String()[:8], ext)
	filePath := filepath.Join(uploadDir, filename)

	// Save file
	if err := c.SaveUploadedFile(file, filePath); err != nil {
		response.InternalError(c, "Failed to save file")
		return
	}

	// Update device
	relativePath := filepath.Join("mobile_devices", filename)
	if imageType == "a" {
		device.ImageA = &relativePath
	} else {
		device.ImageB = &relativePath
	}
	device.UpdatedAt = time.Now()

	if err := h.mobileRepo.Update(device); err != nil {
		response.InternalError(c, "Failed to update device")
		return
	}

	response.Success(c, gin.H{
		"message": "Image uploaded successfully",
		"path":    relativePath,
	})
}

// OccupyDevice occupies a mobile device
func (h *MobileHandler) OccupyDevice(c *gin.Context) {
	userID := middleware.GetUserID(c)

	deviceID, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		response.BadRequest(c, "Invalid device ID")
		return
	}

	device, err := h.mobileRepo.GetByID(uint(deviceID))
	if err != nil {
		response.NotFound(c, "Device not found")
		return
	}

	var req OccupyMobileDeviceRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, "Invalid request")
		return
	}

	if req.EndTime == "" {
		response.BadRequest(c, "End time cannot be empty")
		return
	}

	endTime, err := parseDateTime(req.EndTime)
	if err != nil {
		response.BadRequest(c, "Invalid end time format")
		return
	}

	now := time.Now()
	device.OccupierID = &userID
	device.Purpose = &req.Purpose
	device.StartTime = &now
	device.EndTime = &endTime

	if err := h.mobileRepo.Update(device); err != nil {
		response.InternalError(c, "Failed to occupy device")
		return
	}

	// Reload
	device, _ = h.mobileRepo.GetByID(device.ID)

	response.SuccessWithMessage(c, "Device occupied", gin.H{"device": device.ToDict()})
}

// ReleaseDevice releases a mobile device
func (h *MobileHandler) ReleaseDevice(c *gin.Context) {
	userID := middleware.GetUserID(c)

	deviceID, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		response.BadRequest(c, "Invalid device ID")
		return
	}

	device, err := h.mobileRepo.GetByID(uint(deviceID))
	if err != nil {
		response.NotFound(c, "Device not found")
		return
	}

	// Check permission
	user, _ := h.userRepo.GetByID(userID)
	if device.OccupierID != nil && *device.OccupierID != userID && (user == nil || user.Role != "admin") {
		response.Forbidden(c, "Not authorized to release this device")
		return
	}

	device.OccupierID = nil
	device.Purpose = nil
	device.StartTime = nil
	device.EndTime = nil

	if err := h.mobileRepo.Update(device); err != nil {
		response.InternalError(c, "Failed to release device")
		return
	}

	// Reload
	device, _ = h.mobileRepo.GetByID(device.ID)

	response.SuccessWithMessage(c, "Device released", gin.H{"device": device.ToDict()})
}
