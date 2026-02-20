package config

import (
	"strings"
	"time"

	"github.com/spf13/viper"
)

type Config struct {
	Server   ServerConfig
	JWT      JWTConfig
	Database DatabaseConfig
	CORS     CORSConfig
	Upload   UploadConfig
}

type ServerConfig struct {
	Port    string
	Mode    string
	RunMode string
}

type JWTConfig struct {
	SecretKey             string
	AccessTokenExpires    time.Duration
	RefreshTokenExpires   time.Duration
}

type DatabaseConfig struct {
	Path string
}

type CORSConfig struct {
	Origins []string
}

type UploadConfig struct {
	Path string
}

var AppConfig *Config

func Init() error {
	viper.SetConfigFile(".env")
	viper.AutomaticEnv()

	// Set defaults
	viper.SetDefault("PORT", "5000")
	viper.SetDefault("GIN_MODE", "debug")
	viper.SetDefault("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
	viper.SetDefault("JWT_ACCESS_TOKEN_EXPIRES", "24")
	viper.SetDefault("JWT_REFRESH_TOKEN_EXPIRES", "720")
	viper.SetDefault("DATABASE_PATH", "data.db")
	viper.SetDefault("CORS_ORIGINS", "*")
	viper.SetDefault("UPLOAD_PATH", "uploads")

	if err := viper.ReadInConfig(); err != nil {
		// If .env doesn't exist, use defaults
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			return err
		}
	}

	// Parse CORS origins
	corsOriginsStr := viper.GetString("CORS_ORIGINS")
	var corsOrigins []string
	if corsOriginsStr == "*" {
		corsOrigins = []string{"*"}
	} else {
		corsOrigins = strings.Split(corsOriginsStr, ",")
		for i, origin := range corsOrigins {
			corsOrigins[i] = strings.TrimSpace(origin)
		}
	}

	accessHours := viper.GetInt("JWT_ACCESS_TOKEN_EXPIRES")
	refreshHours := viper.GetInt("JWT_REFRESH_TOKEN_EXPIRES")

	AppConfig = &Config{
		Server: ServerConfig{
			Port:    viper.GetString("PORT"),
			Mode:    viper.GetString("GIN_MODE"),
			RunMode: viper.GetString("GIN_MODE"),
		},
		JWT: JWTConfig{
			SecretKey:           viper.GetString("JWT_SECRET_KEY"),
			AccessTokenExpires:  time.Duration(accessHours) * time.Hour,
			RefreshTokenExpires: time.Duration(refreshHours) * time.Hour,
		},
		Database: DatabaseConfig{
			Path: viper.GetString("DATABASE_PATH"),
		},
		CORS: CORSConfig{
			Origins: corsOrigins,
		},
		Upload: UploadConfig{
			Path: viper.GetString("UPLOAD_PATH"),
		},
	}

	return nil
}
