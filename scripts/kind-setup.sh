#!/usr/bin/env bash
set -euo pipefail

# ── Kind 클러스터 초기화 스크립트 ─────────────────────────────────────────────
# registry 없음 - kind load docker-image 방식 사용 (더 빠름)
# ─────────────────────────────────────────────────────────────────────────────

CLUSTER_NAME="${1:-riveroverflow}"
K8S_VERSION="v1.29.2"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[kind-setup]${NC} $*"; }
warn() { echo -e "${YELLOW}[kind-setup]${NC} $*"; }

# 의존성 확인
for cmd in kind docker kubectl; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: '$cmd' not installed." >&2
    exit 1
  fi
done

# Kind 클러스터 생성
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
  warn "클러스터 '${CLUSTER_NAME}' 이미 존재합니다. 건너뜁니다."
else
  log "Kind 클러스터 '${CLUSTER_NAME}' 생성 중..."
  cat <<EOF | kind create cluster \
    --name "${CLUSTER_NAME}" \
    --image "kindest/node:${K8S_VERSION}" \
    --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    kubeadmConfigPatches:
      - |
        kind: InitConfiguration
        nodeRegistration:
          kubeletExtraArgs:
            node-labels: "ingress-ready=true"
    extraPortMappings:
      - containerPort: 80
        hostPort: 80
        protocol: TCP
      - containerPort: 443
        hostPort: 443
        protocol: TCP
EOF
fi

# nginx ingress controller 설치
log "nginx ingress controller 설치 중..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

log "ingress controller 준비 대기 중..."
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s

log ""
log "✓ 클러스터 준비 완료!"
log "  클러스터: ${CLUSTER_NAME}"
log "  접속 주소: http://localhost"
log ""
log "이미지 배포 방식: kind load docker-image (registry 불필요)"
log ""
log "다음 단계:"
log "  make deploy        # 전체 빌드 + 배포"
log "  make dev           # 로컬 개발 (docker-compose)"
log "  make deploy-engine # engine만 빠르게 재배포"
