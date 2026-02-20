package services

import (
	"errors"

	"pos-scanner-backend/internal/models"
	"pos-scanner-backend/internal/repository"
	"pos-scanner-backend/pkg/jwt"
)

var (
	ErrUserNotFound      = errors.New("user not found")
	ErrInvalidPassword   = errors.New("invalid password")
	ErrUserNotApproved   = errors.New("account not approved")
	ErrUsernameExists    = errors.New("username already exists")
	ErrEmailExists       = errors.New("email already registered")
)

type AuthService struct {
	userRepo *repository.UserRepository
}

func NewAuthService(userRepo *repository.UserRepository) *AuthService {
	return &AuthService{userRepo: userRepo}
}

type RegisterInput struct {
	Username string
	Password string
	Email    string
	Name     string
}

type LoginResult struct {
	AccessToken  string      `json:"access_token"`
	RefreshToken string      `json:"refresh_token"`
	User         interface{} `json:"user"`
}

func (s *AuthService) Register(input RegisterInput) error {
	// Validate input
	if len(input.Username) < 3 {
		return errors.New("username must be at least 3 characters")
	}
	if len(input.Password) < 6 {
		return errors.New("password must be at least 6 characters")
	}
	if input.Name == "" {
		return errors.New("name is required")
	}

	// Check username exists
	if s.userRepo.ExistsByUsername(input.Username) {
		return ErrUsernameExists
	}

	// Check email exists if provided
	if input.Email != "" && s.userRepo.ExistsByEmail(input.Email) {
		return ErrEmailExists
	}

	// Create user
	user := &models.User{
		Username: input.Username,
		Email:    stringPtr(input.Email),
		Name:     stringPtr(input.Name),
		Role:     "user",
		Status:   "pending",
	}

	if err := user.SetPassword(input.Password); err != nil {
		return err
	}

	return s.userRepo.Create(user)
}

func (s *AuthService) Login(username, password string) (*LoginResult, error) {
	user, err := s.userRepo.GetByUsername(username)
	if err != nil {
		return nil, ErrUserNotFound
	}

	if !user.CheckPassword(password) {
		return nil, ErrInvalidPassword
	}

	if user.Status != "approved" {
		return nil, ErrUserNotApproved
	}

	// Generate tokens
	tokenPair, err := jwt.GenerateTokenPair(user.ID)
	if err != nil {
		return nil, err
	}

	return &LoginResult{
		AccessToken:  tokenPair.AccessToken,
		RefreshToken: tokenPair.RefreshToken,
		User:         user.ToDict(),
	}, nil
}

func (s *AuthService) GetProfile(userID uint) (*models.User, error) {
	return s.userRepo.GetByID(userID)
}

func (s *AuthService) ChangePassword(userID uint, oldPassword, newPassword string) error {
	user, err := s.userRepo.GetByID(userID)
	if err != nil {
		return ErrUserNotFound
	}

	if !user.CheckPassword(oldPassword) {
		return ErrInvalidPassword
	}

	if len(newPassword) < 6 {
		return errors.New("new password must be at least 6 characters")
	}

	return user.SetPassword(newPassword)
}

func stringPtr(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}
