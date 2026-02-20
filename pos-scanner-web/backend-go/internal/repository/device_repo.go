package repository

import (
	"pos-scanner-backend/internal/models"
	"time"

	"gorm.io/gorm"
)

type DeviceRepository struct {
	db *gorm.DB
}

func NewDeviceRepository(db *gorm.DB) *DeviceRepository {
	return &DeviceRepository{db: db}
}

// ScanResult operations
func (r *DeviceRepository) CreateScanResult(result *models.ScanResult) error {
	return r.db.Create(result).Error
}

func (r *DeviceRepository) GetScanResultByMerchantID(merchantID string) (*models.ScanResult, error) {
	var result models.ScanResult
	err := r.db.Where("merchant_id = ?", merchantID).First(&result).Error
	if err != nil {
		return nil, err
	}
	return &result, nil
}

func (r *DeviceRepository) GetScanResultByIPAndEmptyMerchant(ip string) (*models.ScanResult, error) {
	var result models.ScanResult
	err := r.db.Where("ip = ? AND (merchant_id = '' OR merchant_id IS NULL)", ip).First(&result).Error
	if err != nil {
		return nil, err
	}
	return &result, nil
}

func (r *DeviceRepository) UpdateScanResult(result *models.ScanResult) error {
	return r.db.Save(result).Error
}

func (r *DeviceRepository) DeleteScanResult(merchantID string) error {
	return r.db.Where("merchant_id = ?", merchantID).Delete(&models.ScanResult{}).Error
}

func (r *DeviceRepository) ListScanResults(page, pageSize int, search string) ([]models.ScanResult, int64, int64, error) {
	var results []models.ScanResult
	var total int64

	query := r.db.Model(&models.ScanResult{})
	if search != "" {
		searchPattern := "%" + search + "%"
		query = query.Where("ip LIKE ? OR merchant_id LIKE ? OR name LIKE ? OR version LIKE ?",
			searchPattern, searchPattern, searchPattern, searchPattern)
	}

	query.Count(&total)

	totalPages := int64(0)
	if pageSize > 0 {
		totalPages = (total + int64(pageSize) - 1) / int64(pageSize)
	}

	offset := (page - 1) * pageSize
	err := query.Order("last_online_time DESC").Offset(offset).Limit(pageSize).Find(&results).Error
	return results, total, totalPages, err
}

func (r *DeviceRepository) SetOfflineNotInMerchantIDs(merchantIDs []string) error {
	if len(merchantIDs) == 0 {
		return nil
	}
	return r.db.Model(&models.ScanResult{}).
		Where("merchant_id != '' AND merchant_id NOT IN ?", merchantIDs).
		Update("is_online", false).Error
}

func (r *DeviceRepository) CleanupOldResults(hours int) (int64, error) {
	result := r.db.Exec(`
		DELETE FROM scan_results
		WHERE datetime(scanned_at) < datetime('now', '-' || ? || ' hours')
	`, hours)
	return result.RowsAffected, result.Error
}

// DeviceOccupancy operations
func (r *DeviceRepository) CreateOccupancy(occupancy *models.DeviceOccupancy) error {
	return r.db.Create(occupancy).Error
}

func (r *DeviceRepository) GetOccupancyByMerchantID(merchantID string) (*models.DeviceOccupancy, error) {
	var occupancy models.DeviceOccupancy
	err := r.db.Preload("User").Where("merchant_id = ?", merchantID).First(&occupancy).Error
	if err != nil {
		return nil, err
	}
	return &occupancy, nil
}

func (r *DeviceRepository) UpdateOccupancy(occupancy *models.DeviceOccupancy) error {
	return r.db.Save(occupancy).Error
}

func (r *DeviceRepository) DeleteOccupancy(merchantID string) error {
	return r.db.Where("merchant_id = ?", merchantID).Delete(&models.DeviceOccupancy{}).Error
}

func (r *DeviceRepository) ListOccupancies() ([]models.DeviceOccupancy, error) {
	var occupancies []models.DeviceOccupancy
	err := r.db.Preload("User").Find(&occupancies).Error
	return occupancies, err
}

func (r *DeviceRepository) ListOccupanciesByMerchantIDs(merchantIDs []string) ([]models.DeviceOccupancy, error) {
	var occupancies []models.DeviceOccupancy
	if len(merchantIDs) == 0 {
		return occupancies, nil
	}
	err := r.db.Preload("User").Where("merchant_id IN ?", merchantIDs).Find(&occupancies).Error
	return occupancies, err
}

func (r *DeviceRepository) CleanupExpiredOccupancies() (int64, error) {
	result := r.db.Exec(`
		DELETE FROM device_occupancies
		WHERE datetime(end_time) < datetime('now')
	`)
	return result.RowsAffected, result.Error
}

// DeviceProperty operations
func (r *DeviceRepository) GetPropertyByMerchantID(merchantID string) (*models.DeviceProperty, error) {
	var prop models.DeviceProperty
	err := r.db.Where("merchant_id = ?", merchantID).First(&prop).Error
	if err != nil {
		return nil, err
	}
	return &prop, nil
}

func (r *DeviceRepository) CreateOrUpdateProperty(prop *models.DeviceProperty) error {
	var existing models.DeviceProperty
	err := r.db.Where("merchant_id = ?", prop.MerchantID).First(&existing).Error
	if err == gorm.ErrRecordNotFound {
		return r.db.Create(prop).Error
	}
	if err != nil {
		return err
	}
	existing.Property = prop.Property
	return r.db.Save(&existing).Error
}

func (r *DeviceRepository) DeleteProperty(merchantID string) error {
	return r.db.Where("merchant_id = ?", merchantID).Delete(&models.DeviceProperty{}).Error
}

func (r *DeviceRepository) ListProperties() ([]models.DeviceProperty, error) {
	var properties []models.DeviceProperty
	err := r.db.Find(&properties).Error
	return properties, err
}

func (r *DeviceRepository) ListPropertiesByMerchantIDs(merchantIDs []string) ([]models.DeviceProperty, error) {
	var properties []models.DeviceProperty
	if len(merchantIDs) == 0 {
		return properties, nil
	}
	err := r.db.Where("merchant_id IN ?", merchantIDs).Find(&properties).Error
	return properties, err
}

// DeviceClaim operations
func (r *DeviceRepository) CreateClaim(claim *models.DeviceClaim) error {
	return r.db.Create(claim).Error
}

func (r *DeviceRepository) GetClaimByID(id uint) (*models.DeviceClaim, error) {
	var claim models.DeviceClaim
	err := r.db.First(&claim, id).Error
	if err != nil {
		return nil, err
	}
	return &claim, nil
}

func (r *DeviceRepository) UpdateClaim(claim *models.DeviceClaim) error {
	return r.db.Save(claim).Error
}

func (r *DeviceRepository) ListClaims(status string) ([]models.DeviceClaim, error) {
	var claims []models.DeviceClaim
	query := r.db.Order("created_at DESC")
	if status != "" {
		query = query.Where("status = ?", status)
	}
	err := query.Find(&claims).Error
	return claims, err
}

func (r *DeviceRepository) GetPendingClaimByMerchantID(merchantID string) (*models.DeviceClaim, error) {
	var claim models.DeviceClaim
	err := r.db.Where("merchant_id = ? AND status = ?", merchantID, "pending").First(&claim).Error
	if err != nil {
		return nil, err
	}
	return &claim, nil
}

func (r *DeviceRepository) GetPendingClaimByUserAndMerchant(userID uint, merchantID string) (*models.DeviceClaim, error) {
	var claim models.DeviceClaim
	err := r.db.Where("user_id = ? AND merchant_id = ? AND status = ?", userID, merchantID, "pending").First(&claim).Error
	if err != nil {
		return nil, err
	}
	return &claim, nil
}

func (r *DeviceRepository) RejectOtherPendingClaims(merchantID string, excludeClaimID uint, processedBy uint) error {
	now := time.Now()
	return r.db.Model(&models.DeviceClaim{}).
		Where("merchant_id = ? AND id != ? AND status = ?", merchantID, excludeClaimID, "pending").
		Updates(map[string]interface{}{
			"status":       "rejected",
			"processed_at": now,
			"processed_by": processedBy,
		}).Error
}

func (r *DeviceRepository) DeleteClaimsByMerchantID(merchantID string) error {
	return r.db.Where("merchant_id = ?", merchantID).Delete(&models.DeviceClaim{}).Error
}

// ScanSession operations
func (r *DeviceRepository) GetScanSession() (*models.ScanSession, error) {
	var session models.ScanSession
	err := r.db.First(&session, 1).Error
	if err == gorm.ErrRecordNotFound {
		session = models.ScanSession{ID: 1}
		if err := r.db.Create(&session).Error; err != nil {
			return nil, err
		}
		return &session, nil
	}
	if err != nil {
		return nil, err
	}
	return &session, nil
}

func (r *DeviceRepository) UpdateScanSession(session *models.ScanSession) error {
	return r.db.Save(session).Error
}

// Helper to get users by IDs
func (r *DeviceRepository) GetUsersByIDs(ids []uint) ([]models.User, error) {
	var users []models.User
	if len(ids) == 0 {
		return users, nil
	}
	err := r.db.Where("id IN ?", ids).Find(&users).Error
	return users, err
}
