package handlers

import (
	"encoding/json"
	"time"

	"pos-scanner-backend/internal/models"
	"pos-scanner-backend/internal/repository"
	"pos-scanner-backend/internal/services"
	"pos-scanner-backend/pkg/response"

	"github.com/gin-gonic/gin"
)

type ScanHandler struct {
	scanService *services.ScanService
	deviceRepo  *repository.DeviceRepository
}

func NewScanHandler(scanService *services.ScanService, deviceRepo *repository.DeviceRepository) *ScanHandler {
	return &ScanHandler{
		scanService: scanService,
		deviceRepo:  deviceRepo,
	}
}

type StartScanRequest struct {
	LocalIP string `json:"local_ip" binding:"required"`
}

// GetLocalIPs returns all local IP addresses
func (h *ScanHandler) GetLocalIPs(c *gin.Context) {
	ips, err := h.scanService.GetLocalIPs()
	if err != nil {
		response.InternalError(c, "获取本地IP失败")
		return
	}

	response.Success(c, gin.H{"ips": ips})
}

// StartScan starts a network scan
func (h *ScanHandler) StartScan(c *gin.Context) {
	var req StartScanRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, "请求格式无效")
		return
	}

	if req.LocalIP == "" {
		response.BadRequest(c, "请选择本地IP")
		return
	}

	err := h.scanService.StartScan(req.LocalIP, func(result map[string]interface{}) {
		// Save result to database
		h.saveScanResult(result)
	})

	if err != nil {
		response.BadRequest(c, err.Error())
		return
	}

	// Start a goroutine to update scan session when scan completes
	go func() {
		for {
			time.Sleep(500 * time.Millisecond)
			status := h.scanService.GetStatus()
			if !status.IsScanning {
				// Update scan session
				session, err := h.deviceRepo.GetScanSession()
				if err == nil {
					session.LastScanAt = time.Now()
					h.deviceRepo.UpdateScanSession(session)
				}
				return
			}
		}
	}()

	response.SuccessWithMessage(c, "扫描已开始", nil)
}

// GetScanStatus returns the current scan status
func (h *ScanHandler) GetScanStatus(c *gin.Context) {
	status := h.scanService.GetStatus()
	response.Success(c, status)
}

// StopScan stops the current scan
func (h *ScanHandler) StopScan(c *gin.Context) {
	h.scanService.StopScan()
	response.SuccessWithMessage(c, "扫描已停止", nil)
}

// GetDeviceDetails fetches detailed info for a specific device
func (h *ScanHandler) GetDeviceDetails(c *gin.Context) {
	ip := c.Param("ip")
	if ip == "" {
		response.BadRequest(c, "IP地址不能为空")
		return
	}

	fullData, err := h.scanService.FetchDeviceDetails(ip)
	if err != nil {
		response.InternalError(c, "获取设备详情失败")
		return
	}

	// Filter data
	filteredData := filterData(fullData)

	response.Success(c, gin.H{"data": filteredData})
}

// saveScanResult saves a scan result to the database
func (h *ScanHandler) saveScanResult(result map[string]interface{}) {
	merchantID, _ := result["merchantId"].(string)
	if merchantID == "" {
		// Handle device without merchant ID
		ip, _ := result["ip"].(string)
		existing, err := h.deviceRepo.GetScanResultByIPAndEmptyMerchant(ip)
		if err == nil && existing != nil {
			// Update existing
			h.updateScanResultFromMap(existing, result)
			h.deviceRepo.UpdateScanResult(existing)
		} else {
			// Create new
			scanResult := h.createScanResultFromMap(result)
			h.deviceRepo.CreateScanResult(scanResult)
		}
		return
	}

	// Check if device exists
	existing, err := h.deviceRepo.GetScanResultByMerchantID(merchantID)
	if err == nil && existing != nil {
		// Update existing
		h.updateScanResultFromMap(existing, result)
		h.deviceRepo.UpdateScanResult(existing)
	} else {
		// Create new
		scanResult := h.createScanResultFromMap(result)
		h.deviceRepo.CreateScanResult(scanResult)
	}
}

func (h *ScanHandler) createScanResultFromMap(result map[string]interface{}) *models.ScanResult {
	now := time.Now()
	scanResult := &models.ScanResult{
		IsOnline:       true,
		LastOnlineTime: now,
		ScannedAt:      now,
	}

	if ip, ok := result["ip"].(string); ok {
		scanResult.IP = ip
	}
	if merchantID, ok := result["merchantId"].(string); ok && merchantID != "" {
		scanResult.MerchantID = &merchantID
	}
	if name, ok := result["name"].(string); ok && name != "" {
		scanResult.Name = &name
	}
	if version, ok := result["version"].(string); ok && version != "" {
		scanResult.Version = &version
	}
	if deviceType, ok := result["type"].(string); ok && deviceType != "" {
		scanResult.Type = &deviceType
	}
	if fullData, ok := result["fullData"].(map[string]interface{}); ok {
		if jsonData, err := json.Marshal(fullData); err == nil {
			jsonStr := string(jsonData)
			scanResult.FullData = &jsonStr
		}
	}

	return scanResult
}

func (h *ScanHandler) updateScanResultFromMap(scanResult *models.ScanResult, result map[string]interface{}) {
	now := time.Now()
	scanResult.LastOnlineTime = now
	scanResult.ScannedAt = now
	scanResult.IsOnline = true

	if ip, ok := result["ip"].(string); ok {
		scanResult.IP = ip
	}
	if name, ok := result["name"].(string); ok {
		scanResult.Name = &name
	}
	if version, ok := result["version"].(string); ok {
		scanResult.Version = &version
	}
	if deviceType, ok := result["type"].(string); ok {
		scanResult.Type = &deviceType
	}
	if fullData, ok := result["fullData"].(map[string]interface{}); ok {
		if jsonData, err := json.Marshal(fullData); err == nil {
			jsonStr := string(jsonData)
			scanResult.FullData = &jsonStr
		}
	}
}

// filterData removes unwanted fields from device data
func filterData(data interface{}) interface{} {
	excludeKeys := map[string]bool{
		"appInstance": true,
		"images":      true,
		"result":      true,
		"printLogo":   true,
	}

	switch v := data.(type) {
	case map[string]interface{}:
		result := make(map[string]interface{})
		for key, value := range v {
			if value != nil && !excludeKeys[key] {
				result[key] = filterData(value)
			}
		}
		return result
	case []interface{}:
		result := make([]interface{}, 0)
		for _, item := range v {
			if item != nil {
				result = append(result, filterData(item))
			}
		}
		return result
	default:
		return data
	}
}
