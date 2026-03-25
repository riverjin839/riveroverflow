package middleware

import (
	"strings"

	"github.com/gofiber/fiber/v2"
	"github.com/golang-jwt/jwt/v5"
)

// JWTGuard validates Bearer tokens for REST endpoints.
func JWTGuard(secret string) fiber.Handler {
	return func(c *fiber.Ctx) error {
		authHeader := c.Get("Authorization")
		if authHeader == "" {
			return fiber.ErrUnauthorized
		}
		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || parts[0] != "Bearer" {
			return fiber.ErrUnauthorized
		}
		claims, err := parseToken(parts[1], secret)
		if err != nil {
			return fiber.ErrUnauthorized
		}
		c.Locals("userID", claims["sub"])
		c.Locals("username", claims["username"])
		return c.Next()
	}
}

// WSGuard validates JWT for WebSocket upgrade via query param ?token=...
func WSGuard(secret string) fiber.Handler {
	return func(c *fiber.Ctx) error {
		token := c.Query("token")
		if token == "" {
			// Also accept header for non-browser clients
			authHeader := c.Get("Authorization")
			parts := strings.SplitN(authHeader, " ", 2)
			if len(parts) == 2 && parts[0] == "Bearer" {
				token = parts[1]
			}
		}
		if token == "" {
			return fiber.ErrUnauthorized
		}
		claims, err := parseToken(token, secret)
		if err != nil {
			return fiber.ErrUnauthorized
		}
		c.Locals("userID", claims["sub"])
		return c.Next()
	}
}

func parseToken(tokenStr, secret string) (jwt.MapClaims, error) {
	token, err := jwt.Parse(tokenStr, func(t *jwt.Token) (interface{}, error) {
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fiber.ErrUnauthorized
		}
		return []byte(secret), nil
	})
	if err != nil || !token.Valid {
		return nil, fiber.ErrUnauthorized
	}
	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return nil, fiber.ErrUnauthorized
	}
	return claims, nil
}
