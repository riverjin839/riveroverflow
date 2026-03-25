package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"github.com/redis/go-redis/v9"

	"github.com/riverjin839/riveroverflow/gateway/internal/handlers"
	"github.com/riverjin839/riveroverflow/gateway/internal/middleware"
	"github.com/riverjin839/riveroverflow/gateway/internal/proxy"
	"github.com/riverjin839/riveroverflow/gateway/internal/ws"
)

func main() {
	cfg := loadConfig()

	// Redis client
	rdb := redis.NewClient(&redis.Options{Addr: cfg.RedisAddr})
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := rdb.Ping(ctx).Err(); err != nil {
		log.Fatalf("redis connect failed: %v", err)
	}

	// WebSocket hub (broadcasts realtime events to connected clients)
	hub := ws.NewHub(rdb)
	go hub.Run()

	// Proxy to Python engine
	engineProxy := proxy.NewEngineProxy(cfg.EngineURL)

	app := fiber.New(fiber.Config{
		AppName:      "RiverOverflow Gateway v1",
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		ErrorHandler: handlers.ErrorHandler,
	})

	// Global middleware
	app.Use(recover.New())
	app.Use(logger.New(logger.Config{
		Format: "[${time}] ${status} ${method} ${path} ${latency}\n",
	}))
	app.Use(cors.New(cors.Config{
		AllowOrigins: cfg.CORSOrigins,
		AllowHeaders: "Origin, Content-Type, Accept, Authorization",
		AllowMethods: "GET,POST,PUT,DELETE,OPTIONS",
	}))

	// Health check (no auth)
	app.Get("/health", handlers.Health)

	// Auth routes (no auth required)
	auth := app.Group("/api/auth")
	auth.Post("/login", handlers.NewAuthHandler(cfg.JWTSecret, cfg.JWTExpireMinutes).Login)

	// Protected API routes
	api := app.Group("/api", middleware.JWTGuard(cfg.JWTSecret))

	// Proxy all /api/v1/* to Python engine
	api.All("/v1/*", engineProxy.Forward)

	// WebSocket (real-time market data + trade events)
	app.Get("/ws", middleware.WSGuard(cfg.JWTSecret), ws.Handler(hub))

	// Start server
	port := fmt.Sprintf(":%s", cfg.Port)
	log.Printf("Gateway listening on %s", port)

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGTERM)

	go func() {
		if err := app.Listen(port); err != nil {
			log.Fatalf("listen error: %v", err)
		}
	}()

	<-quit
	log.Println("Shutting down gateway...")
	_ = app.Shutdown()
}

type config struct {
	Port             string
	RedisAddr        string
	EngineURL        string
	JWTSecret        string
	JWTExpireMinutes int
	CORSOrigins      string
}

func loadConfig() config {
	return config{
		Port:             getEnv("PORT", "8080"),
		RedisAddr:        getEnv("REDIS_ADDR", "redis:6379"),
		EngineURL:        getEnv("ENGINE_URL", "http://engine:9090"),
		JWTSecret:        getEnv("JWT_SECRET", "dev-secret"),
		JWTExpireMinutes: 1440,
		CORSOrigins:      getEnv("CORS_ORIGINS", "*"),
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
