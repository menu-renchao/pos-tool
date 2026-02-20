package repository

import (
	"pos-scanner-backend/internal/models"
	"time"

	"gorm.io/gorm"
)

type MobileRepository struct {
	db *gorm.DB
}

func NewMobileRepository(db *gorm.DB) *MobileRepository {
	return &MobileRepository{db: db}
}

func (r *MobileRepository) Create(device *models.MobileDevice) error {
	return r.db.Create(device).Error
}

func (r *MobileRepository) GetByID(id uint) (*models.MobileDevice, error) {
	var device models.MobileDevice
	err := r.db.Preload("Occupier").First(&device, id).Error
	if err != nil {
		return nil, err
	}
	return &device, nil
}

func (r *MobileRepository) Update(device *models.MobileDevice) error {
	return r.db.Save(device).Error
}

func (r *MobileRepository) Delete(id uint) error {
	return r.db.Delete(&models.MobileDevice{}, id).Error
}

func (r *MobileRepository) List() ([]models.MobileDevice, error) {
	var devices []models.MobileDevice
	err := r.db.Preload("Occupier").Order("created_at DESC").Find(&devices).Error
	return devices, err
}

func (r *MobileRepository) CleanupExpiredOccupancies() (int64, error) {
	now := LocalTime()
	result := r.db.Model(&models.MobileDevice{}).
		Where("end_time IS NOT NULL AND datetime(end_time) < datetime(?)", now).
		Updates(map[string]interface{}{
			"occupier_id": nil,
			"purpose":     nil,
			"start_time":  nil,
			"end_time":    nil,
		})
	return result.RowsAffected, result.Error
}

func LocalTime() time.Time {
	return time.Now()
}
