#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${1:-riveroverflow}"
REGISTRY_NAME="kind-registry"
REGISTRY_PORT="5001"
K8S_VERSION="v1.29.2"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[kind-setup]${NC} $*"; }
warn() { echo -e "${YELLOW}[kind-setup]${NC} $*"; }

# Check dependencies
for cmd in kind docker kubectl; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: '$cmd' is not installed." >&2
    exit 1
  fi
done

# Start local registry if not running
if ! docker ps --format '{{.Names}}' | grep -q "^${REGISTRY_NAME}$"; then
  log "Starting local Docker registry on port ${REGISTRY_PORT}..."
  docker run -d \
    --restart=always \
    --name "${REGISTRY_NAME}" \
    -p "127.0.0.1:${REGISTRY_PORT}:5000" \
    registry:2
else
  warn "Registry '${REGISTRY_NAME}' already running."
fi

# Create Kind cluster if not exists
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
  warn "Cluster '${CLUSTER_NAME}' already exists. Skipping creation."
else
  log "Creating Kind cluster '${CLUSTER_NAME}'..."
  cat <<EOF | kind create cluster --name "${CLUSTER_NAME}" --image "kindest/node:${K8S_VERSION}" --config=-
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
containerdConfigPatches:
  - |-
    [plugins."io.containerd.grpc.v1.cri".registry]
      [plugins."io.containerd.grpc.v1.cri".registry.mirrors]
        [plugins."io.containerd.grpc.v1.cri".registry.mirrors."localhost:${REGISTRY_PORT}"]
          endpoint = ["http://${REGISTRY_NAME}:5000"]
EOF
fi

# Connect registry to cluster network
if ! docker network inspect kind 2>/dev/null | grep -q "${REGISTRY_NAME}"; then
  log "Connecting registry to Kind network..."
  docker network connect kind "${REGISTRY_NAME}" 2>/dev/null || true
fi

# Configure registry in cluster
log "Configuring local registry in cluster..."
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: local-registry-hosting
  namespace: kube-public
data:
  localRegistryHosting.v1: |
    host: "localhost:${REGISTRY_PORT}"
    help: "https://kind.sigs.k8s.io/docs/user/local-registry/"
EOF

# Install nginx ingress controller
log "Installing nginx ingress controller..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

log "Waiting for ingress controller to be ready..."
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s

log ""
log "Setup complete!"
log "  Cluster:  ${CLUSTER_NAME}"
log "  Registry: localhost:${REGISTRY_PORT}"
log "  Ingress:  http://localhost"
log ""
log "Next steps:"
log "  make deploy    # Build and deploy all services"
log "  make dev       # Local development with docker-compose"
