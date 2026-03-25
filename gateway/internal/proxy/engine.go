package proxy

import (
	"fmt"

	"github.com/gofiber/fiber/v2"
	"github.com/valyala/fasthttp"
)

// EngineProxy forwards requests from the gateway to the Python trading engine.
type EngineProxy struct {
	engineURL string
	client    *fasthttp.Client
}

func NewEngineProxy(engineURL string) *EngineProxy {
	return &EngineProxy{
		engineURL: engineURL,
		client:    &fasthttp.Client{},
	}
}

// Forward proxies the incoming request to the engine, rewriting the path.
// /api/v1/foo → http://engine:9090/api/v1/foo
func (p *EngineProxy) Forward(c *fiber.Ctx) error {
	req := fasthttp.AcquireRequest()
	resp := fasthttp.AcquireResponse()
	defer fasthttp.ReleaseRequest(req)
	defer fasthttp.ReleaseResponse(resp)

	// Build target URL
	target := fmt.Sprintf("%s%s", p.engineURL, c.OriginalURL())
	req.SetRequestURI(target)
	req.Header.SetMethodBytes(c.Request().Header.Method())

	// Forward request body
	req.SetBody(c.Body())

	// Forward headers (excluding hop-by-hop)
	c.Request().Header.VisitAll(func(key, val []byte) {
		k := string(key)
		if k != "Connection" && k != "Transfer-Encoding" {
			req.Header.SetBytesKV(key, val)
		}
	})

	// Forward authenticated user info
	if userID := c.Locals("userID"); userID != nil {
		req.Header.Set("X-User-ID", fmt.Sprintf("%v", userID))
	}

	if err := p.client.Do(req, resp); err != nil {
		return fiber.NewError(fiber.StatusBadGateway, "engine unavailable")
	}

	// Write response back
	c.Status(resp.StatusCode())
	resp.Header.VisitAll(func(key, val []byte) {
		c.Response().Header.SetBytesKV(key, val)
	})
	c.Response().SetBody(resp.Body())
	return nil
}
