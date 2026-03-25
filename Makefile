##
## RiverOverflow Trading App
## Usage: make <target>
##

CLUSTER   := riveroverflow
REGISTRY  := localhost:5001
NS        := riveroverflow
VERSION   := $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)

GATEWAY_IMG  := $(REGISTRY)/gateway:$(VERSION)
ENGINE_IMG   := $(REGISTRY)/engine:$(VERSION)
FRONTEND_IMG := $(REGISTRY)/frontend:$(VERSION)

BOLD  := \033[1m
GREEN := \033[0;32m
RESET := \033[0m

.PHONY: help setup dev build push deploy restart logs clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BOLD)%-12s$(RESET) %s\n", $$1, $$2}'

# ── Local K8s setup ────────────────────────────────────────────────────────────

setup: ## Initialize Kind cluster + local registry (run once)
	@echo -e "$(GREEN)Setting up Kind cluster...$(RESET)"
	@bash scripts/kind-setup.sh $(CLUSTER)
	@kubectl apply -f k8s/namespace.yaml
	@kubectl apply -f k8s/postgres/
	@kubectl apply -f k8s/redis/
	@echo -e "$(GREEN)Cluster ready. Run 'make deploy' to deploy services.$(RESET)"

# ── Local development (no K8s) ──────────────────────────────────────────────────

dev: ## Start all services with docker-compose (fastest for development)
	docker compose up --build

dev-down: ## Stop docker-compose services
	docker compose down -v

# ── Build images ───────────────────────────────────────────────────────────────

build: build-gateway build-engine build-frontend ## Build all Docker images

build-gateway: ## Build Go gateway image
	@echo -e "$(GREEN)Building gateway...$(RESET)"
	docker build -t $(GATEWAY_IMG) ./gateway

build-engine: ## Build Python engine image
	@echo -e "$(GREEN)Building engine...$(RESET)"
	docker build -t $(ENGINE_IMG) ./engine

build-frontend: ## Build React frontend image
	@echo -e "$(GREEN)Building frontend...$(RESET)"
	docker build -t $(FRONTEND_IMG) ./frontend

# ── Push to local registry ─────────────────────────────────────────────────────

push: ## Push all images to local Kind registry
	docker push $(GATEWAY_IMG)
	docker push $(ENGINE_IMG)
	docker push $(FRONTEND_IMG)

# ── Deploy to Kind cluster ──────────────────────────────────────────────────────

deploy: build push _apply _rollout ## Build + push + deploy to Kind cluster (full cycle)

_apply:
	@echo -e "$(GREEN)Applying K8s manifests...$(RESET)"
	@kubectl apply -f k8s/namespace.yaml
	@kubectl apply -f k8s/secrets/ 2>/dev/null || true
	@kubectl apply -f k8s/postgres/
	@kubectl apply -f k8s/redis/
	@sed "s|IMAGE_GATEWAY|$(GATEWAY_IMG)|g;s|IMAGE_ENGINE|$(ENGINE_IMG)|g;s|IMAGE_FRONTEND|$(FRONTEND_IMG)|g" \
		k8s/gateway/deployment.yaml | kubectl apply -f -
	@sed "s|IMAGE_GATEWAY|$(GATEWAY_IMG)|g;s|IMAGE_ENGINE|$(ENGINE_IMG)|g;s|IMAGE_FRONTEND|$(FRONTEND_IMG)|g" \
		k8s/engine/deployment.yaml | kubectl apply -f -
	@sed "s|IMAGE_GATEWAY|$(GATEWAY_IMG)|g;s|IMAGE_ENGINE|$(ENGINE_IMG)|g;s|IMAGE_FRONTEND|$(FRONTEND_IMG)|g" \
		k8s/frontend/deployment.yaml | kubectl apply -f -
	@kubectl apply -f k8s/gateway/service.yaml
	@kubectl apply -f k8s/engine/service.yaml
	@kubectl apply -f k8s/frontend/service.yaml
	@kubectl apply -f k8s/ingress.yaml

_rollout:
	@echo -e "$(GREEN)Waiting for rollout...$(RESET)"
	@kubectl rollout status deployment/gateway -n $(NS) --timeout=120s
	@kubectl rollout status deployment/engine  -n $(NS) --timeout=120s
	@kubectl rollout status deployment/frontend -n $(NS) --timeout=120s
	@echo -e "$(GREEN)Deployed successfully! http://localhost$(RESET)"

restart: ## Restart all deployments (force re-pull)
	kubectl rollout restart deployment -n $(NS)

# ── Logs & debug ───────────────────────────────────────────────────────────────

logs: ## Follow logs for all pods
	kubectl logs -f -l app=gateway -n $(NS) --prefix &
	kubectl logs -f -l app=engine  -n $(NS) --prefix &
	kubectl logs -f -l app=frontend -n $(NS) --prefix
	wait

logs-gateway: ## Follow gateway logs
	kubectl logs -f -l app=gateway -n $(NS)

logs-engine: ## Follow engine logs
	kubectl logs -f -l app=engine -n $(NS)

status: ## Show pod status
	kubectl get pods -n $(NS) -o wide

# ── Cleanup ─────────────────────────────────────────────────────────────────────

clean: ## Delete Kind cluster (WARNING: destroys all data)
	kind delete cluster --name $(CLUSTER)
	docker stop kind-registry 2>/dev/null || true
	docker rm kind-registry 2>/dev/null || true
