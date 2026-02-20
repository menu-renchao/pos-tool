package handlers

import (
	"pos-scanner-backend/internal/middleware"
	"pos-scanner-backend/internal/models"
	"pos-scanner-backend/internal/repository"
	"pos-scanner-backend/pkg/response"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
)

type AdminHandler struct {
	userRepo   *repository.UserRepository
	deviceRepo *repository.DeviceRepository
}

func NewAdminHandler(userRepo *repository.UserRepository, deviceRepo *repository.DeviceRepository) *AdminHandler {
	return &AdminHandler{
		userRepo:   userRepo,
		deviceRepo: deviceRepo,
	}
}

type CreateUserRequest struct {
	Username string `json:"username" binding:"required"`
	Password string `json:"password" binding:"required"`
	Email    string `json:"email"`
	Name     string `json:"name" binding:"required"`
	Role     string `json:"role"`
	Status   string `json:"status"`
}

type UpdateUserRequest struct {
	Username string `json:"username"`
	Email    string `json:"email"`
	Name     string `json:"name"`
	Role     string `json:"role"`
	Status   string `json:"status"`
}

type ResetPasswordRequest struct {
	NewPassword string `json:"new_password" binding:"required"`
}

type SetDevicePropertyRequest struct {
	MerchantID string `json:"merchant_id" binding:"required"`
	Property   string `json:"property" binding:"required"`
}

// GetUsers returns all users
func (h *AdminHandler) GetUsers(c *gin.Context) {
	status := c.Query("status")

	users, err := h.userRepo.List(status)
	if err != nil {
		response.InternalError(c, "Failed to get users")
		return
	}

	userDicts := make([]map[string]interface{}, len(users))
	for i, u := range users {
		userDicts[i] = u.ToDict()
	}

	response.Success(c, gin.H{"users": userDicts})
}

// CreateUser creates a new user
func (h *AdminHandler) CreateUser(c *gin.Context) {
	var req CreateUserRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, "Invalid request")
		return
	}

	req.Username = strings.TrimSpace(req.Username)
	req.Email = strings.TrimSpace(req.Email)
	req.Name = strings.TrimSpace(req.Name)

	if req.Username == "" || req.Password == "" || req.Name == "" {
		response.BadRequest(c, "Username, password, and name are required")
		return
	}

	if len(req.Username) < 3 {
		response.BadRequest(c, "Username must be at least 3 characters")
		return
	}

	if len(req.Password) < 6 {
		response.BadRequest(c, "Password must be at least 6 characters")
		return
	}

	if req.Role != "" && req.Role != "user" && req.Role != "admin" {
		response.BadRequest(c, "Role must be 'user' or 'admin'")
		return
	}

	// Check username exists
	if h.userRepo.ExistsByUsername(req.Username) {
		response.BadRequest(c, "Username already exists")
		return
	}

	// Check email exists if provided
	if req.Email != "" && h.userRepo.ExistsByEmail(req.Email) {
		response.BadRequest(c, "Email already in use")
		return
	}

	// Set defaults
	role := req.Role
	if role == "" {
		role = "user"
	}
	status := req.Status
	if status == "" {
		status = "approved"
	}

	var email *string
	if req.Email != "" {
		email = &req.Email
	}

	user := &models.User{
		Username: req.Username,
		Email:    email,
		Name:     &req.Name,
		Role:     role,
		Status:   status,
	}

	if err := user.SetPassword(req.Password); err != nil {
		response.InternalError(c, "Failed to set password")
		return
	}

	if err := h.userRepo.Create(user); err != nil {
		response.InternalError(c, "Failed to create user")
		return
	}

	response.CreatedWithMessage(c, "User created successfully", gin.H{"user": user.ToDict()})
}

// UpdateUser updates a user
func (h *AdminHandler) UpdateUser(c *gin.Context) {
	currentUserID := middleware.GetUserID(c)
	userID, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		response.BadRequest(c, "Invalid user ID")
		return
	}

	user, err := h.userRepo.GetByID(uint(userID))
	if err != nil {
		response.NotFound(c, "User not found")
		return
	}

	var req UpdateUserRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, "Invalid request")
		return
	}

	// Update username
	if req.Username != "" {
		newUsername := strings.TrimSpace(req.Username)
		if newUsername != user.Username {
			if h.userRepo.ExistsByUsernameExcludeID(newUsername, uint(userID)) {
				response.BadRequest(c, "Username already exists")
				return
			}
			user.Username = newUsername
		}
	}

	// Update email
	if req.Email != "" {
		newEmail := strings.TrimSpace(req.Email)
		if newEmail != "" {
			if h.userRepo.ExistsByEmailExcludeID(newEmail, uint(userID)) {
				response.BadRequest(c, "Email already in use")
				return
			}
			user.Email = &newEmail
		} else {
			user.Email = nil
		}
	}

	// Update name
	if req.Name != "" {
		newName := strings.TrimSpace(req.Name)
		user.Name = &newName
	}

	// Update role
	if req.Role != "" {
		if req.Role != "user" && req.Role != "admin" {
			response.BadRequest(c, "Role must be 'user' or 'admin'")
			return
		}
		// Prevent admin from removing their own admin role
		if uint(userID) == currentUserID && req.Role != "admin" {
			response.BadRequest(c, "Cannot remove your own admin privileges")
			return
		}
		user.Role = req.Role
	}

	// Update status
	if req.Status != "" {
		if req.Status != "pending" && req.Status != "approved" && req.Status != "rejected" {
			response.BadRequest(c, "Invalid status")
			return
		}
		user.Status = req.Status
	}

	if err := h.userRepo.Update(user); err != nil {
		response.InternalError(c, "Failed to update user")
		return
	}

	response.SuccessWithMessage(c, "User updated successfully", gin.H{"user": user.ToDict()})
}

// ApproveUser approves a user
func (h *AdminHandler) ApproveUser(c *gin.Context) {
	userID, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		response.BadRequest(c, "Invalid user ID")
		return
	}

	user, err := h.userRepo.GetByID(uint(userID))
	if err != nil {
		response.NotFound(c, "User not found")
		return
	}

	if user.Status == "approved" {
		response.BadRequest(c, "User already approved")
		return
	}

	user.Status = "approved"
	if err := h.userRepo.Update(user); err != nil {
		response.InternalError(c, "Failed to approve user")
		return
	}

	response.SuccessWithMessage(c, "User approved", nil)
}

// RejectUser rejects a user
func (h *AdminHandler) RejectUser(c *gin.Context) {
	userID, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		response.BadRequest(c, "Invalid user ID")
		return
	}

	user, err := h.userRepo.GetByID(uint(userID))
	if err != nil {
		response.NotFound(c, "User not found")
		return
	}

	if user.Status == "rejected" {
		response.BadRequest(c, "User already rejected")
		return
	}

	user.Status = "rejected"
	if err := h.userRepo.Update(user); err != nil {
		response.InternalError(c, "Failed to reject user")
		return
	}

	response.SuccessWithMessage(c, "User rejected", nil)
}

// ResetUserPassword resets a user's password
func (h *AdminHandler) ResetUserPassword(c *gin.Context) {
	userID, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		response.BadRequest(c, "Invalid user ID")
		return
	}

	user, err := h.userRepo.GetByID(uint(userID))
	if err != nil {
		response.NotFound(c, "User not found")
		return
	}

	var req ResetPasswordRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, "Invalid request")
		return
	}

	if len(req.NewPassword) < 6 {
		response.BadRequest(c, "Password must be at least 6 characters")
		return
	}

	if err := user.SetPassword(req.NewPassword); err != nil {
		response.InternalError(c, "Failed to set password")
		return
	}

	if err := h.userRepo.Update(user); err != nil {
		response.InternalError(c, "Failed to reset password")
		return
	}

	response.SuccessWithMessage(c, "Password reset successfully", nil)
}

// DeleteUser deletes a user
func (h *AdminHandler) DeleteUser(c *gin.Context) {
	currentUserID := middleware.GetUserID(c)
	userID, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		response.BadRequest(c, "Invalid user ID")
		return
	}

	if uint(userID) == currentUserID {
		response.BadRequest(c, "Cannot delete your own account")
		return
	}

	if err := h.userRepo.Delete(uint(userID)); err != nil {
		response.InternalError(c, "Failed to delete user")
		return
	}

	response.SuccessWithMessage(c, "User deleted", nil)
}

// GetDeviceProperties returns all device properties
func (h *AdminHandler) GetDeviceProperties(c *gin.Context) {
	properties, err := h.deviceRepo.ListProperties()
	if err != nil {
		response.InternalError(c, "Failed to get device properties")
		return
	}

	propDicts := make([]map[string]interface{}, len(properties))
	for i, p := range properties {
		propDicts[i] = p.ToDict()
	}

	response.Success(c, gin.H{"properties": propDicts})
}

// SetDeviceProperty sets a device property
func (h *AdminHandler) SetDeviceProperty(c *gin.Context) {
	var req SetDevicePropertyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, "Invalid request")
		return
	}

	if req.MerchantID == "" {
		response.BadRequest(c, "Merchant ID cannot be empty")
		return
	}

	if req.Property == "" {
		response.BadRequest(c, "Property cannot be empty")
		return
	}

	prop := &models.DeviceProperty{
		MerchantID: req.MerchantID,
		Property:   req.Property,
	}

	if err := h.deviceRepo.CreateOrUpdateProperty(prop); err != nil {
		response.InternalError(c, "Failed to set device property")
		return
	}

	response.SuccessWithMessage(c, "Device property updated", gin.H{"property": prop.ToDict()})
}

// DeleteDeviceProperty deletes a device property
func (h *AdminHandler) DeleteDeviceProperty(c *gin.Context) {
	merchantID := c.Param("merchant_id")
	if merchantID == "" {
		response.BadRequest(c, "Merchant ID required")
		return
	}

	// Check if exists
	_, err := h.deviceRepo.GetPropertyByMerchantID(merchantID)
	if err != nil {
		response.NotFound(c, "Device property not found")
		return
	}

	if err := h.deviceRepo.DeleteProperty(merchantID); err != nil {
		response.InternalError(c, "Failed to delete device property")
		return
	}

	response.SuccessWithMessage(c, "Device property deleted", nil)
}
