package repository

import (
	"pos-scanner-backend/internal/models"

	"gorm.io/gorm"
)

type UserRepository struct {
	db *gorm.DB
}

func NewUserRepository(db *gorm.DB) *UserRepository {
	return &UserRepository{db: db}
}

func (r *UserRepository) Create(user *models.User) error {
	return r.db.Create(user).Error
}

func (r *UserRepository) GetByID(id uint) (*models.User, error) {
	var user models.User
	err := r.db.First(&user, id).Error
	if err != nil {
		return nil, err
	}
	return &user, nil
}

func (r *UserRepository) GetByUsername(username string) (*models.User, error) {
	var user models.User
	err := r.db.Where("username = ?", username).First(&user).Error
	if err != nil {
		return nil, err
	}
	return &user, nil
}

func (r *UserRepository) GetByEmail(email string) (*models.User, error) {
	var user models.User
	err := r.db.Where("email = ?", email).First(&user).Error
	if err != nil {
		return nil, err
	}
	return &user, nil
}

func (r *UserRepository) Update(user *models.User) error {
	return r.db.Save(user).Error
}

func (r *UserRepository) Delete(id uint) error {
	return r.db.Delete(&models.User{}, id).Error
}

func (r *UserRepository) List(status string) ([]models.User, error) {
	var users []models.User
	query := r.db.Order("created_at DESC")
	if status != "" && status != "all" {
		query = query.Where("status = ?", status)
	}
	err := query.Find(&users).Error
	return users, err
}

func (r *UserRepository) ExistsByUsername(username string) bool {
	var count int64
	r.db.Model(&models.User{}).Where("username = ?", username).Count(&count)
	return count > 0
}

func (r *UserRepository) ExistsByEmail(email string) bool {
	var count int64
	r.db.Model(&models.User{}).Where("email = ?", email).Count(&count)
	return count > 0
}

func (r *UserRepository) ExistsByUsernameExcludeID(username string, excludeID uint) bool {
	var count int64
	r.db.Model(&models.User{}).Where("username = ? AND id != ?", username, excludeID).Count(&count)
	return count > 0
}

func (r *UserRepository) ExistsByEmailExcludeID(email string, excludeID uint) bool {
	var count int64
	r.db.Model(&models.User{}).Where("email = ? AND id != ?", email, excludeID).Count(&count)
	return count > 0
}
