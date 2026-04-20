# ── Stage 1: Dev (Vite dev server with hot reload) ────────────────────────────
FROM node:20-alpine AS dev

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
EXPOSE 3000
# package.json 이 변경되면 컨테이너 기동 시 자동으로 npm install 하여
# 익명 node_modules 볼륨과 불일치 문제를 자동 해소한다.
CMD ["sh", "-c", "npm install --no-audit --no-fund && npm run dev"]

# ── Stage 2: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --quiet
COPY . .
RUN npm run build

# ── Stage 3: Production (nginx) ───────────────────────────────────────────────
FROM nginx:alpine AS production

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
