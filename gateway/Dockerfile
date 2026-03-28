# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM golang:1.22-alpine AS builder

WORKDIR /build
RUN apk add --no-cache git

COPY . .
RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o gateway ./cmd/server

# ── Stage 2: Dev (with hot reload) ───────────────────────────────────────────
FROM golang:1.22-alpine AS dev

WORKDIR /app
RUN apk add --no-cache curl && go install github.com/air-verse/air@v1.52.3

COPY . .
RUN go mod tidy

CMD ["sh", "-c", "[ ! -f go.sum ] && go mod tidy; exec air -c .air.toml"]

# ── Stage 3: Production ───────────────────────────────────────────────────────
FROM gcr.io/distroless/static-debian12 AS production

WORKDIR /app
COPY --from=builder /build/gateway .

EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/app/gateway"]
