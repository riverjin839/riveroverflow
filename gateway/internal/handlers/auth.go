package handlers

import (
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/golang-jwt/jwt/v5"
)

type AuthHandler struct {
	jwtSecret      string
	expireMinutes  int
}

func NewAuthHandler(secret string, expireMinutes int) *AuthHandler {
	return &AuthHandler{jwtSecret: secret, expireMinutes: expireMinutes}
}

type loginRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

type loginResponse struct {
	Token     string `json:"token"`
	ExpiresAt int64  `json:"expires_at"`
}

// Login issues a JWT token.
// In production, validate against DB; here we use env-configured admin creds.
func (h *AuthHandler) Login(c *fiber.Ctx) error {
	var req loginRequest
	if err := c.BodyParser(&req); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "invalid request body")
	}
	if req.Username == "" || req.Password == "" {
		return fiber.NewError(fiber.StatusBadRequest, "username and password required")
	}

	// TODO: validate against DB user table
	// For now, this is a placeholder – real validation happens in the engine
	expiresAt := time.Now().Add(time.Duration(h.expireMinutes) * time.Minute)
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sub":      req.Username,
		"username": req.Username,
		"exp":      expiresAt.Unix(),
		"iat":      time.Now().Unix(),
	})
	signed, err := token.SignedString([]byte(h.jwtSecret))
	if err != nil {
		return fiber.ErrInternalServerError
	}

	return c.JSON(loginResponse{
		Token:     signed,
		ExpiresAt: expiresAt.Unix(),
	})
}
