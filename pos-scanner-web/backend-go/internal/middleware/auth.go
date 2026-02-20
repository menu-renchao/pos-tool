package middleware

import (
	"strings"

	"pos-scanner-backend/internal/models"
	"pos-scanner-backend/internal/repository"
	"pos-scanner-backend/pkg/jwt"
	"pos-scanner-backend/pkg/response"

	"github.com/gin-gonic/gin"
)

func Auth() gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			response.Unauthorized(c, "请提供认证令牌")
			c.Abort()
			return
		}

		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
			response.Unauthorized(c, "令牌格式无效")
			c.Abort()
			return
		}

		claims, err := jwt.ValidateToken(parts[1])
		if err != nil {
			response.Unauthorized(c, "令牌无效")
			c.Abort()
			return
		}

		// Store user ID in context
		c.Set("user_id", claims.UserID)
		c.Next()
	}
}

func AdminOnly(userRepo *repository.UserRepository) gin.HandlerFunc {
	return func(c *gin.Context) {
		userID, exists := c.Get("user_id")
		if !exists {
			response.Unauthorized(c, "未授权")
			c.Abort()
			return
		}

		user, err := userRepo.GetByID(userID.(uint))
		if err != nil || user == nil {
			response.Unauthorized(c, "用户不存在")
			c.Abort()
			return
		}

		if user.Role != "admin" {
			response.Forbidden(c, "需要管理员权限")
			c.Abort()
			return
		}

		c.Set("user", user)
		c.Next()
	}
}

func GetCurrentUser(c *gin.Context) *models.User {
	user, exists := c.Get("user")
	if !exists {
		return nil
	}
	return user.(*models.User)
}

func GetUserID(c *gin.Context) uint {
	userID, exists := c.Get("user_id")
	if !exists {
		return 0
	}
	return userID.(uint)
}
