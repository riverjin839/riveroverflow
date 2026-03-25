##
## RiverOverflow Trading App
## Usage: make <target>
##
## 배포 방식: kind load docker-image (registry 없이 Mac 로컬에서 직접 inject)
## 속도: docker build → kind load → kubectl rollout (push/pull 왕복 없음)
##

CLUSTER  := riveroverflow
NS       := riveroverflow
VERSION  := $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)

GATEWAY_IMG  := riveroverflow/gateway:$(VERSION)
ENGINE_IMG   := riveroverflow/engine:$(VERSION)
FRONTEND_IMG := riveroverflow/frontend:$(VERSION)

BOLD  := \033[1m
GREEN := \033[0;32m
CYAN  := \033[0;36m
RESET := \033[0m

.PHONY: help setup dev dev-down build load deploy restart logs logs-gateway logs-engine status clean

help: ## 전체 명령어 목록
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BOLD)%-14s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "  $(CYAN)배포 흐름:$(RESET) make deploy = build → kind load → kubectl apply → rollout"

# ── Kind K8s 클러스터 초기화 (최초 1회) ────────────────────────────────────────

setup: ## Kind 클러스터 초기화 (최초 1회, ~2분)
	@echo -e "$(GREEN)Kind 클러스터 설정 중...$(RESET)"
	@bash scripts/kind-setup.sh $(CLUSTER)
	@kubectl apply -f k8s/namespace.yaml
	@kubectl apply -f k8s/postgres/
	@kubectl apply -f k8s/redis/
	@echo -e "$(GREEN)완료! 'make deploy'로 서비스를 배포하세요.$(RESET)"

# ── 로컬 개발 (K8s 없이, 가장 빠른 개발 사이클) ───────────────────────────────

dev: ## docker-compose 로컬 개발 (hot reload)
	docker compose up --build

dev-down: ## docker-compose 중지 및 볼륨 삭제
	docker compose down -v

# ── 이미지 빌드 ────────────────────────────────────────────────────────────────

build: build-gateway build-engine build-frontend ## 3개 이미지 순차 빌드

build-gateway: ## Go gateway 이미지 빌드
	@echo -e "$(GREEN)▶ gateway 빌드 ($(VERSION))...$(RESET)"
	docker build -t $(GATEWAY_IMG) --target production ./gateway

build-engine: ## Python engine 이미지 빌드
	@echo -e "$(GREEN)▶ engine 빌드 ($(VERSION))...$(RESET)"
	docker build -t $(ENGINE_IMG) --target production ./engine

build-frontend: ## React frontend 이미지 빌드
	@echo -e "$(GREEN)▶ frontend 빌드 ($(VERSION))...$(RESET)"
	docker build -t $(FRONTEND_IMG) --target production ./frontend

# ── Kind 노드에 직접 로드 (registry push 없음 - 핵심 최적화) ──────────────────

load: ## kind load docker-image로 직접 inject (push 불필요)
	@echo -e "$(GREEN)▶ Kind 노드에 이미지 로드 중...$(RESET)"
	kind load docker-image $(GATEWAY_IMG)  --name $(CLUSTER)
	kind load docker-image $(ENGINE_IMG)   --name $(CLUSTER)
	kind load docker-image $(FRONTEND_IMG) --name $(CLUSTER)
	@echo -e "$(GREEN)✓ 이미지 로드 완료$(RESET)"

# ── 원스텝 배포: build → load → apply → rollout ────────────────────────────────

deploy: build load _apply _rollout ## [메인] 빌드 + load + K8s 배포 (원스텝)

_apply:
	@echo -e "$(GREEN)▶ K8s 매니페스트 적용 중...$(RESET)"
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
	@echo -e "$(GREEN)▶ 롤아웃 대기 중...$(RESET)"
	@kubectl rollout status deployment/gateway  -n $(NS) --timeout=120s
	@kubectl rollout status deployment/engine   -n $(NS) --timeout=120s
	@kubectl rollout status deployment/frontend -n $(NS) --timeout=120s
	@echo -e "$(GREEN)✓ 배포 완료 → http://localhost$(RESET)"

# ── 빠른 재배포 (특정 서비스만) ───────────────────────────────────────────────

deploy-gateway: build-gateway ## gateway만 재배포
	kind load docker-image $(GATEWAY_IMG) --name $(CLUSTER)
	kubectl set image deployment/gateway gateway=$(GATEWAY_IMG) -n $(NS)
	kubectl rollout status deployment/gateway -n $(NS) --timeout=60s

deploy-engine: build-engine ## engine만 재배포
	kind load docker-image $(ENGINE_IMG) --name $(CLUSTER)
	kubectl set image deployment/engine engine=$(ENGINE_IMG) -n $(NS)
	kubectl rollout status deployment/engine -n $(NS) --timeout=60s

deploy-frontend: build-frontend ## frontend만 재배포
	kind load docker-image $(FRONTEND_IMG) --name $(CLUSTER)
	kubectl set image deployment/frontend frontend=$(FRONTEND_IMG) -n $(NS)
	kubectl rollout status deployment/frontend -n $(NS) --timeout=60s

restart: ## 모든 deployment 재시작 (이미지 변경 없이)
	kubectl rollout restart deployment -n $(NS)

# ── 로그 & 디버그 ────────────────────────────────────────────────────────────────

logs: ## 전체 pod 로그 follow
	@kubectl logs -f -l app=gateway  -n $(NS) --prefix &
	@kubectl logs -f -l app=engine   -n $(NS) --prefix &
	@kubectl logs -f -l app=frontend -n $(NS) --prefix
	@wait

logs-gateway: ## Gateway 로그
	kubectl logs -f -l app=gateway -n $(NS)

logs-engine: ## Engine 로그
	kubectl logs -f -l app=engine -n $(NS)

status: ## Pod 상태 확인
	kubectl get pods -n $(NS) -o wide

images: ## Kind 노드에 로드된 이미지 목록
	docker exec $(CLUSTER)-control-plane crictl images

# ── 정리 ──────────────────────────────────────────────────────────────────────

clean: ## Kind 클러스터 삭제 (주의: 데이터 전체 삭제)
	kind delete cluster --name $(CLUSTER)
	@echo -e "$(GREEN)✓ 클러스터 삭제 완료$(RESET)"
