package ws

import (
	"context"
	"encoding/json"
	"log"
	"sync"

	"github.com/gofiber/contrib/websocket"
	"github.com/gofiber/fiber/v2"
	"github.com/redis/go-redis/v9"
)

// Redis channels
const (
	ChannelTrades    = "riveroverflow:trades"
	ChannelMarket    = "riveroverflow:market"
	ChannelPortfolio = "riveroverflow:portfolio"
)

// Client represents a connected WebSocket client.
type Client struct {
	conn   *websocket.Conn
	send   chan []byte
	userID string
}

// Hub manages all WebSocket connections and broadcasts Redis pub/sub messages.
type Hub struct {
	clients    map[*Client]bool
	broadcast  chan []byte
	register   chan *Client
	unregister chan *Client
	mu         sync.RWMutex
	rdb        *redis.Client
}

func NewHub(rdb *redis.Client) *Hub {
	return &Hub{
		clients:    make(map[*Client]bool),
		broadcast:  make(chan []byte, 256),
		register:   make(chan *Client),
		unregister: make(chan *Client),
		rdb:        rdb,
	}
}

// Run starts the hub's event loop and subscribes to Redis channels.
func (h *Hub) Run() {
	// Subscribe to all trading channels
	go h.subscribeRedis()

	for {
		select {
		case client := <-h.register:
			h.mu.Lock()
			h.clients[client] = true
			h.mu.Unlock()
			log.Printf("WS client connected: %s (total: %d)", client.userID, len(h.clients))

		case client := <-h.unregister:
			h.mu.Lock()
			if _, ok := h.clients[client]; ok {
				delete(h.clients, client)
				close(client.send)
			}
			h.mu.Unlock()
			log.Printf("WS client disconnected: %s (total: %d)", client.userID, len(h.clients))

		case msg := <-h.broadcast:
			h.mu.RLock()
			for client := range h.clients {
				select {
				case client.send <- msg:
				default:
					// Slow client: drop message
				}
			}
			h.mu.RUnlock()
		}
	}
}

// subscribeRedis listens to Redis pub/sub and forwards messages to all WS clients.
func (h *Hub) subscribeRedis() {
	ctx := context.Background()
	sub := h.rdb.Subscribe(ctx, ChannelTrades, ChannelMarket, ChannelPortfolio)
	defer sub.Close()

	ch := sub.Channel()
	for msg := range ch {
		event := map[string]interface{}{
			"channel": msg.Channel,
			"data":    json.RawMessage(msg.Payload),
		}
		b, err := json.Marshal(event)
		if err != nil {
			continue
		}
		h.broadcast <- b
	}
}

// Handler returns a Fiber handler for WebSocket upgrades.
func Handler(hub *Hub) fiber.Handler {
	return websocket.New(func(c *websocket.Conn) {
		userID := ""
		if uid := c.Locals("userID"); uid != nil {
			userID = uid.(string)
		}

		client := &Client{
			conn:   c,
			send:   make(chan []byte, 256),
			userID: userID,
		}
		hub.register <- client

		// Write pump
		go func() {
			for msg := range client.send {
				if err := c.WriteMessage(websocket.TextMessage, msg); err != nil {
					break
				}
			}
		}()

		// Read pump (keep connection alive, handle pings)
		for {
			_, _, err := c.ReadMessage()
			if err != nil {
				break
			}
		}
		hub.unregister <- client
	})
}
