package models

import (
	"time"

	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

type User struct {
	ID           uint           `gorm:"primaryKey" json:"id"`
	Username     string         `gorm:"size:50;uniqueIndex;not null" json:"username"`
	PasswordHash string         `gorm:"size:256;not null" json:"-"`
	Email        *string        `gorm:"size:100;uniqueIndex" json:"email"`
	Name         *string        `gorm:"size:50" json:"name"`
	Role         string         `gorm:"size:20;default:user" json:"role"`
	Status       string         `gorm:"size:20;default:pending" json:"status"`
	CreatedAt    time.Time      `json:"created_at"`
	UpdatedAt    time.Time      `json:"updated_at"`
	DeletedAt    gorm.DeletedAt `gorm:"index" json:"-"`
}

func (User) TableName() string {
	return "users"
}

func (u *User) SetPassword(password string) error {
	bytes, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return err
	}
	u.PasswordHash = string(bytes)
	return nil
}

func (u *User) CheckPassword(password string) bool {
	err := bcrypt.CompareHashAndPassword([]byte(u.PasswordHash), []byte(password))
	return err == nil
}

func (u *User) ToDict() map[string]interface{} {
	result := map[string]interface{}{
		"id":         u.ID,
		"username":   u.Username,
		"email":      u.Email,
		"name":       u.Name,
		"role":       u.Role,
		"status":     u.Status,
		"created_at": u.CreatedAt.Format(time.RFC3339),
		"updated_at": u.UpdatedAt.Format(time.RFC3339),
	}
	return result
}
