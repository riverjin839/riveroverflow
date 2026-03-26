# deploy

RiverOverflow의 Kind Kubernetes 배포 가이드입니다.

## 사용법

```
/deploy
/deploy <서비스명>
```

예시:
```
/deploy
/deploy engine
/deploy frontend
/deploy gateway
```

## 전체 배포 흐름 (`make deploy`)

```
코드 변경
  → Docker 이미지 빌드 (multi-stage)
  → kind load (레지스트리 push 없이 Kind 노드에 직접 주입)
  → kubectl apply (매니페스트 적용)
  → rollout restart (파드 재시작)
  → rollout status (배포 완료 대기)
```

## 서비스별 수동 배포

### Gateway (Go Fiber)

```bash
docker build -t localhost:5001/gateway:$(git rev-parse --short HEAD) ./gateway
kind load docker-image localhost:5001/gateway:$(git rev-parse --short HEAD) --name riveroverflow
kubectl rollout restart deployment/gateway -n riveroverflow
kubectl rollout status deployment/gateway -n riveroverflow
```

### Engine (Python FastAPI)

```bash
docker build -t localhost:5001/engine:$(git rev-parse --short HEAD) ./engine
kind load docker-image localhost:5001/engine:$(git rev-parse --short HEAD) --name riveroverflow
kubectl rollout restart deployment/engine -n riveroverflow
kubectl rollout status deployment/engine -n riveroverflow
```

### Frontend (React + Nginx)

```bash
docker build -t localhost:5001/frontend:$(git rev-parse --short HEAD) ./frontend
kind load docker-image localhost:5001/frontend:$(git rev-parse --short HEAD) --name riveroverflow
kubectl rollout restart deployment/frontend -n riveroverflow
kubectl rollout status deployment/frontend -n riveroverflow
```

## 빠른 Makefile 타겟

| 명령어 | 동작 |
|-------|------|
| `make deploy` | 전체 재배포 |
| `make deploy-gateway` | Gateway만 |
| `make deploy-engine` | Engine만 |
| `make deploy-frontend` | Frontend만 |
| `make dev` | Docker Compose 로컬 개발 (K8s 불필요) |
| `make status` | 파드 상태 확인 |
| `make logs` | 전체 로그 |
| `make logs-gateway` | Gateway 로그 |
| `make logs-engine` | Engine 로그 |

## 상태 확인

```bash
# 파드 전체 상태
kubectl get pods -n riveroverflow

# 파드 상세 (오류 확인)
kubectl describe pod -l app=engine -n riveroverflow

# 실시간 로그
kubectl logs -f -l app=engine -n riveroverflow --tail=100
```

## DB 마이그레이션 배포 후 실행

```bash
kubectl exec -it deployment/engine -n riveroverflow -- alembic upgrade head
```

## 문제 해결

| 증상 | 원인 | 해결 |
|-----|------|------|
| `ImagePullBackOff` | kind load 안 됨 | `kind load docker-image` 재실행 |
| `CrashLoopBackOff` | 앱 시작 오류 | `make logs-engine` 로그 확인 |
| `Pending` | 리소스 부족 | `kubectl describe pod` 확인 |
| 페이지 안 뜸 | ingress 오류 | `kubectl get ingress -n riveroverflow` |

## 환경별 URL

| 환경 | URL |
|-----|-----|
| K8s (make deploy) | `http://localhost` |
| 로컬 개발 (make dev) | `http://localhost:3000` |
| Engine Swagger | `http://localhost:9090/docs` (개발 시) |
