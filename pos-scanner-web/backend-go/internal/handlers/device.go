package handlers

import (
	"strconv"
	"strings"
	"time"

	"pos-scanner-backend/internal/middleware"
	"pos-scanner-backend/internal/models"
	"pos-scanner-backend/internal/repository"
	"pos-scanner-backend/pkg/response"

	"github.com/gin-gonic/gin"
)

type DeviceHandler struct {
	deviceRepo *repository.DeviceRepository
	userRepo   *repository.UserRepository
}

func NewDeviceHandler(deviceRepo *repository.DeviceRepository, userRepo *repository.UserRepository) *DeviceHandler {
	return &DeviceHandler{
		deviceRepo: deviceRepo,
		userRepo:   userRepo,
	}
}

type SetOccupancyRequest struct {
	MerchantID string `json:"merchant_id" binding:"required"`
	Purpose    string `json:"purpose"`
	StartTime  string `json:"start_time"`
	EndTime    string `json:"end_time" binding:"required"`
}

type SubmitClaimRequest struct {
	MerchantID string `json:"merchant_id" binding:"required"`
}

// GetDevices returns paginated device list
func (h *DeviceHandler) GetDevices(c *gin.Context) {
	// Cleanup expired occupancies first
	h.deviceRepo.CleanupExpiredOccupancies()

	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "50"))
	search := c.Query("search")

	if pageSize > 200 {
		pageSize = 200
	}

	results, total, totalPages, err := h.deviceRepo.ListScanResults(page, pageSize, search)
	if err != nil {
		response.InternalError(c, "获取设备列表失败")
		return
	}

	// Get scan session
	session, _ := h.deviceRepo.GetScanSession()

	// Get merchant IDs and owner IDs
	merchantIDs := make([]string, 0)
	ownerIDs := make([]uint, 0)
	for _, r := range results {
		if r.MerchantID != nil && *r.MerchantID != "" {
			merchantIDs = append(merchantIDs, *r.MerchantID)
		}
		if r.OwnerID != nil {
			ownerIDs = append(ownerIDs, *r.OwnerID)
		}
	}

	// Get properties
	properties, _ := h.deviceRepo.ListPropertiesByMerchantIDs(merchantIDs)
	propertyMap := make(map[string]string)
	for _, p := range properties {
		propertyMap[p.MerchantID] = p.Property
	}

	// Get occupancies
	occupancies, _ := h.deviceRepo.ListOccupanciesByMerchantIDs(merchantIDs)
	occupancyMap := make(map[string]*models.DeviceOccupancy)
	for i := range occupancies {
		occupancyMap[occupancies[i].MerchantID] = &occupancies[i]
	}

	// Get users
	users, _ := h.deviceRepo.GetUsersByIDs(ownerIDs)
	userMap := make(map[uint]*models.User)
	for i := range users {
		userMap[users[i].ID] = &users[i]
	}

	// Build device list
	devices := make([]map[string]interface{}, 0)
	now := time.Now()
	for _, r := range results {
		device := r.ToDict()

		merchantID := ""
		if r.MerchantID != nil {
			merchantID = *r.MerchantID
		}

		// Add property
		if prop, ok := propertyMap[merchantID]; ok {
			device["property"] = prop
		} else {
			device["property"] = "PC"
		}

		// Add occupancy
		if occupancy, ok := occupancyMap[merchantID]; ok {
			if occupancy.EndTime.After(now) {
				device["occupancy"] = occupancy.ToDict()
				device["isOccupied"] = true
			} else {
				device["occupancy"] = nil
				device["isOccupied"] = false
			}
		} else {
			device["occupancy"] = nil
			device["isOccupied"] = false
		}

		// Add owner
		if r.OwnerID != nil {
			if owner, ok := userMap[*r.OwnerID]; ok {
				username := owner.Username
				if owner.Name != nil && *owner.Name != "" {
					username = *owner.Name
				}
				device["owner"] = map[string]interface{}{
					"id":       owner.ID,
					"username": username,
				}
			} else {
				device["owner"] = nil
			}
		} else {
			device["owner"] = nil
		}

		devices = append(devices, device)
	}

	lastScanAt := ""
	if session != nil {
		lastScanAt = session.LastScanAt.Format(time.RFC3339)
	}

	response.Success(c, gin.H{
		"devices":    devices,
		"total":      total,
		"page":       page,
		"pageSize":   pageSize,
		"totalPages": totalPages,
		"lastScanAt": lastScanAt,
	})
}

// GetOccupancies returns all device occupancies
func (h *DeviceHandler) GetOccupancies(c *gin.Context) {
	occupancies, err := h.deviceRepo.ListOccupancies()
	if err != nil {
		response.InternalError(c, "获取借用信息失败")
		return
	}

	occDicts := make([]map[string]interface{}, len(occupancies))
	for i, o := range occupancies {
		occDicts[i] = o.ToDict()
	}

	response.Success(c, gin.H{"occupancies": occDicts})
}

// SetOccupancy sets device occupancy
func (h *DeviceHandler) SetOccupancy(c *gin.Context) {
	userID := middleware.GetUserID(c)

	var req SetOccupancyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, "请求格式无效")
		return
	}

	if req.MerchantID == "" {
		response.BadRequest(c, "商家ID不能为空")
		return
	}

	if req.EndTime == "" {
		response.BadRequest(c, "归还时间不能为空")
		return
	}

	// Parse times
	startTime := time.Now()
	if req.StartTime != "" {
		if t, err := parseDateTime(req.StartTime); err == nil {
			startTime = t
		}
	}

	endTime, err := parseDateTime(req.EndTime)
	if err != nil {
		response.BadRequest(c, "归还时间格式无效")
		return
	}

	if endTime.Before(startTime) || endTime.Equal(startTime) {
		response.BadRequest(c, "归还时间必须大于当前时间")
		return
	}

	// Check for existing occupancy
	occupancy, _ := h.deviceRepo.GetOccupancyByMerchantID(req.MerchantID)
	if occupancy != nil {
		occupancy.UserID = userID
		occupancy.Purpose = &req.Purpose
		occupancy.StartTime = startTime
		occupancy.EndTime = endTime
		if err := h.deviceRepo.UpdateOccupancy(occupancy); err != nil {
			response.InternalError(c, "更新借用信息失败")
			return
		}
	} else {
		occupancy = &models.DeviceOccupancy{
			MerchantID: req.MerchantID,
			UserID:     userID,
			Purpose:    &req.Purpose,
			StartTime:  startTime,
			EndTime:    endTime,
		}
		if err := h.deviceRepo.CreateOccupancy(occupancy); err != nil {
			response.InternalError(c, "创建借用信息失败")
			return
		}
	}

	// Reload with user
	occupancy, _ = h.deviceRepo.GetOccupancyByMerchantID(req.MerchantID)

	response.SuccessWithMessage(c, "借用信息已更新", gin.H{"occupancy": occupancy.ToDict()})
}

// ReleaseOccupancy releases device occupancy
func (h *DeviceHandler) ReleaseOccupancy(c *gin.Context) {
	userID := middleware.GetUserID(c)
	merchantID := c.Param("merchant_id")

	occupancy, err := h.deviceRepo.GetOccupancyByMerchantID(merchantID)
	if err != nil {
		response.NotFound(c, "借用记录不存在")
		return
	}

	// Check permission
	user, _ := h.userRepo.GetByID(userID)
	if occupancy.UserID != userID && (user == nil || user.Role != "admin") {
		response.Forbidden(c, "无权释放此设备")
		return
	}

	if err := h.deviceRepo.DeleteOccupancy(merchantID); err != nil {
		response.InternalError(c, "释放设备失败")
		return
	}

	response.SuccessWithMessage(c, "设备已释放", nil)
}

// DeleteDevice deletes a device (admin only)
func (h *DeviceHandler) DeleteDevice(c *gin.Context) {
	merchantID := c.Param("merchant_id")

	// Check device exists
	device, err := h.deviceRepo.GetScanResultByMerchantID(merchantID)
	if err != nil {
		response.NotFound(c, "设备不存在")
		return
	}

	// Delete related records
	h.deviceRepo.DeleteOccupancy(merchantID)
	h.deviceRepo.DeleteClaimsByMerchantID(merchantID)

	// Delete device
	if err := h.deviceRepo.DeleteScanResult(*device.MerchantID); err != nil {
		response.InternalError(c, "删除设备失败")
		return
	}

	response.SuccessWithMessage(c, "设备已删除", nil)
}

// SubmitClaim submits a device claim
func (h *DeviceHandler) SubmitClaim(c *gin.Context) {
	userID := middleware.GetUserID(c)

	var req SubmitClaimRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, "请求格式无效")
		return
	}

	if req.MerchantID == "" {
		response.BadRequest(c, "商家ID不能为空")
		return
	}

	// Check device exists
	device, err := h.deviceRepo.GetScanResultByMerchantID(req.MerchantID)
	if err != nil {
		response.NotFound(c, "设备不存在")
		return
	}

	// Check if already claimed
	if device.OwnerID != nil {
		response.BadRequest(c, "设备已被认领")
		return
	}

	// Check for pending claim
	if _, err := h.deviceRepo.GetPendingClaimByMerchantID(req.MerchantID); err == nil {
		response.BadRequest(c, "该设备已有待审核的认领申请")
		return
	}

	// Check if user already claimed
	if _, err := h.deviceRepo.GetPendingClaimByUserAndMerchant(userID, req.MerchantID); err == nil {
		response.BadRequest(c, "您已提交过该设备的认领申请")
		return
	}

	// Create claim
	claim := &models.DeviceClaim{
		MerchantID: req.MerchantID,
		UserID:     userID,
		Status:     "pending",
	}

	if err := h.deviceRepo.CreateClaim(claim); err != nil {
		response.InternalError(c, "提交认领申请失败")
		return
	}

	response.SuccessWithMessage(c, "认领申请已提交，请等待管理员审核", nil)
}

// GetClaims returns device claims
func (h *DeviceHandler) GetClaims(c *gin.Context) {
	status := c.DefaultQuery("status", "pending")

	claims, err := h.deviceRepo.ListClaims(status)
	if err != nil {
		response.InternalError(c, "获取认领申请列表失败")
		return
	}

	// Build result with user and device info
	result := make([]map[string]interface{}, 0)
	for _, claim := range claims {
		user, _ := h.userRepo.GetByID(claim.UserID)
		device, _ := h.deviceRepo.GetScanResultByMerchantID(claim.MerchantID)

		username := "未知用户"
		if user != nil {
			if user.Name != nil && *user.Name != "" {
				username = *user.Name
			} else {
				username = user.Username
			}
		}

		deviceName := "未知设备"
		if device != nil && device.Name != nil {
			deviceName = *device.Name
		}

		claimDict := map[string]interface{}{
			"id":          claim.ID,
			"merchantId":  claim.MerchantID,
			"deviceName":  deviceName,
			"userId":      claim.UserID,
			"username":    username,
			"status":      claim.Status,
			"createdAt":   claim.CreatedAt.Format(time.RFC3339),
			"processedAt": nil,
		}
		if claim.ProcessedAt != nil {
			claimDict["processedAt"] = claim.ProcessedAt.Format(time.RFC3339)
		}

		result = append(result, claimDict)
	}

	response.Success(c, gin.H{"claims": result})
}

// ApproveClaim approves a device claim
func (h *DeviceHandler) ApproveClaim(c *gin.Context) {
	userID := middleware.GetUserID(c)
	claimID, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		response.BadRequest(c, "认领申请ID无效")
		return
	}

	claim, err := h.deviceRepo.GetClaimByID(uint(claimID))
	if err != nil {
		response.NotFound(c, "认领申请不存在")
		return
	}

	if claim.Status != "pending" {
		response.BadRequest(c, "该认领申请已处理")
		return
	}

	// Check device exists and not claimed
	device, err := h.deviceRepo.GetScanResultByMerchantID(claim.MerchantID)
	if err != nil {
		response.NotFound(c, "设备不存在")
		return
	}

	if device.OwnerID != nil {
		response.BadRequest(c, "设备已被认领")
		return
	}

	// Update claim
	now := time.Now()
	claim.Status = "approved"
	claim.ProcessedAt = &now
	claim.ProcessedBy = &userID

	// Set device owner
	device.OwnerID = &claim.UserID

	// Update in transaction
	if err := h.deviceRepo.UpdateClaim(claim); err != nil {
		response.InternalError(c, "审批认领申请失败")
		return
	}
	if err := h.deviceRepo.UpdateScanResult(device); err != nil {
		response.InternalError(c, "更新设备信息失败")
		return
	}

	// Reject other pending claims
	h.deviceRepo.RejectOtherPendingClaims(claim.MerchantID, uint(claimID), userID)

	response.SuccessWithMessage(c, "认领申请已通过", nil)
}

// RejectClaim rejects a device claim
func (h *DeviceHandler) RejectClaim(c *gin.Context) {
	userID := middleware.GetUserID(c)
	claimID, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		response.BadRequest(c, "认领申请ID无效")
		return
	}

	claim, err := h.deviceRepo.GetClaimByID(uint(claimID))
	if err != nil {
		response.NotFound(c, "认领申请不存在")
		return
	}

	if claim.Status != "pending" {
		response.BadRequest(c, "该认领申请已处理")
		return
	}

	now := time.Now()
	claim.Status = "rejected"
	claim.ProcessedAt = &now
	claim.ProcessedBy = &userID

	if err := h.deviceRepo.UpdateClaim(claim); err != nil {
		response.InternalError(c, "拒绝认领申请失败")
		return
	}

	response.SuccessWithMessage(c, "认领申请已拒绝", nil)
}

// ResetOwner resets device owner (admin only)
func (h *DeviceHandler) ResetOwner(c *gin.Context) {
	merchantID := c.Param("merchant_id")

	device, err := h.deviceRepo.GetScanResultByMerchantID(merchantID)
	if err != nil {
		response.NotFound(c, "设备不存在")
		return
	}

	device.OwnerID = nil
	if err := h.deviceRepo.UpdateScanResult(device); err != nil {
		response.InternalError(c, "重置负责人失败")
		return
	}

	response.SuccessWithMessage(c, "负责人已重置", nil)
}

// parseDateTime parses various datetime formats
func parseDateTime(s string) (time.Time, error) {
	// Try RFC3339
	if t, err := time.Parse(time.RFC3339, s); err == nil {
		return t.Local(), nil
	}

	// Try ISO format without timezone
	if t, err := time.Parse("2006-01-02T15:04:05", s); err == nil {
		return t.Local(), nil
	}

	// Try ISO format with Z
	s = strings.Replace(s, "Z", "", 1)
	if t, err := time.Parse("2006-01-02T15:04:05.000", s); err == nil {
		return t.Local(), nil
	}

	return time.Parse(time.RFC3339, s)
}
