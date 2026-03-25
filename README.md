# RiverOverflow 자동매매 플랫폼

한국 주식 자동매매 웹 애플리케이션.
Mac + Kind K8s 위에서 동작하며 한국투자증권 / Kiwoom 계정을 연결해 전략 기반 자동매매와 결과 분석을 제공합니다.

---

## 기술 스택

| 계층 | 기술 |
|------|------|
| API Gateway | Go 1.22 + Fiber v2 |
| Trading Engine | Python 3.12 + FastAPI |
| 브로커 라이브러리 | python-kis (한국투자증권) |
| Frontend | React 18 + Vite + Tailwind CSS 3 |
| 차트 | TradingView Lightweight Charts 4 |
| DB | PostgreSQL 16 + Redis 7 |
| 컨테이너 | Docker multi-stage |
| K8s | Kind (Mac 로컬) + nginx-ingress |

---

## 빠른 시작

### 사전 요구사항

```bash
# Mac 기준
brew install kind kubectl docker
# Docker Desktop 실행 필요
```

### 1. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일에서 아래 값을 입력합니다:

```env
# 한국투자증권 API (https://apiportal.koreainvestment.com 에서 발급)
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
KIS_ACCOUNT_NO=12345678-01      # 계좌번호
KIS_IS_VIRTUAL=true             # true=모의투자 (처음엔 반드시 true로 시작)

JWT_SECRET=your_random_secret   # 랜덤 문자열 (32자 이상 권장)
```

### 2. 로컬 개발 (Kind 없이 - 가장 빠름)

```bash
make dev
# → http://localhost:3000  (Frontend)
# → http://localhost:8080  (Gateway API)
# → http://localhost:9090  (Trading Engine)
```

### 3. Kind K8s 배포

```bash
# Kind 클러스터 + 로컬 레지스트리 초기화 (최초 1회, 약 3분)
make setup

# K8s secrets 설정 (최초 1회)
cp k8s/secrets/secrets.yaml.example k8s/secrets/secrets.yaml
# secrets.yaml 에서 base64 인코딩된 값 입력
kubectl apply -f k8s/secrets/secrets.yaml

# 빌드 + 배포 (이후에는 이것만 실행)
make deploy
# → http://localhost
```

---

## 프로젝트 구조

```
riveroverflow/
├── Makefile                      # make setup / dev / build / deploy / clean
├── docker-compose.yml            # 로컬 개발용 (K8s 없이)
├── .env.example                  # 환경변수 템플릿
│
├── gateway/                      # Go Fiber - API Gateway
│   ├── cmd/server/main.go        # 진입점
│   └── internal/
│       ├── middleware/jwt.go     # JWT 인증 (REST + WebSocket)
│       ├── handlers/             # auth, health 핸들러
│       ├── proxy/engine.go       # Python engine 리버스 프록시
│       └── ws/hub.go             # WebSocket 허브 (Redis pub/sub)
│
├── engine/                       # Python FastAPI - Trading Engine
│   └── app/
│       ├── broker/
│       │   ├── base.py           # AbstractBroker 인터페이스
│       │   ├── kis.py            # 한국투자증권 구현체
│       │   └── kiwoom.py         # Kiwoom bridge 클라이언트
│       ├── strategies/
│       │   ├── rules/            # MA Cross, RSI, MACD
│       │   └── ml/               # ML 전략 기반 클래스
│       ├── engine/
│       │   ├── runner.py         # 핵심 트레이딩 루프
│       │   ├── risk.py           # 리스크 관리
│       │   └── scheduler.py      # KRX 시장 시간 스케줄러
│       └── api/routes/           # FastAPI 라우터
│
├── frontend/                     # React + Vite
│   └── src/
│       ├── models/               # Zustand 스토어 (MVP Model)
│       ├── presenters/           # API hooks (MVP Presenter)
│       └── views/                # React 페이지 (MVP View)
│           ├── dashboard/        # 대시보드 + 실시간 차트
│           ├── portfolio/        # 포트폴리오 현황
│           ├── strategies/       # 전략 관리 + 엔진 제어
│           └── analytics/        # 거래 이력 분석
│
├── kiwoom-bridge/                # Kiwoom COM → REST 브릿지 (Windows)
│   └── bridge_server.py
│
├── k8s/                          # Kubernetes 매니페스트
│   ├── ingress.yaml              # nginx-ingress 라우팅
│   ├── gateway/ engine/ frontend/ postgres/ redis/
│   └── secrets/secrets.yaml.example
│
└── scripts/
    └── kind-setup.sh             # Kind 클러스터 + 로컬 레지스트리 초기화
```

---

## Makefile 명령어

```bash
make help       # 전체 명령어 목록

make setup      # Kind 클러스터 초기화 (최초 1회)
make dev        # docker-compose 로컬 개발
make build      # Docker 이미지 빌드 (3개)
make push       # 로컬 레지스트리에 push
make deploy     # 빌드 + push + K8s 롤아웃 (원스텝)
make logs       # 전체 pod 로그 follow
make status     # pod 상태 확인
make clean      # Kind 클러스터 삭제
```

---

## 아키텍처

```
브라우저 (PC / 모바일)
      │  HTTP / WebSocket
      ▼
nginx-ingress (localhost:80)
  ├── /api/*  → Go Gateway (8080)
  ├── /ws/*   → Go Gateway WebSocket
  └── /*      → Frontend nginx (80)
                    │
             Go Gateway
          ┌──────┴──────┐
          │             │
    REST proxy    WebSocket Hub
          │        (Redis sub)
          ▼             │
   Python Engine  ←─────┘
    (FastAPI 9090)      Redis PUBLISH
          │
    ┌─────┴──────┐
    │            │
  KIS API    Kiwoom Bridge
 (REST/WS)   (Windows COM)
```

### 실시간 데이터 흐름

```
한국투자증권 WebSocket
    │ 시세 데이터
    ▼
Python Engine runner.py
    └─ Strategy.evaluate() → Signal
    └─ RiskManager.check() → 승인/거부
    └─ Broker.place_order() → 주문 실행
    └─ Redis PUBLISH (trade / market / portfolio 채널)
          │
    Go WebSocket Hub
    └─ Redis SUBSCRIBE
    └─ broadcast → 모든 WebSocket 클라이언트
          │
    Frontend (Zustand)
    └─ 실시간 차트 / 포트폴리오 갱신
```

---

## 자동매매 전략

모든 전략은 `AbstractStrategy`를 구현하는 플러그인 구조입니다.

| 전략 | 설명 | 주요 파라미터 |
|------|------|--------------|
| `ma_cross` | 이동평균 교차 (골든/데드크로스) | `short_period`, `long_period` |
| `rsi` | RSI 과매수/과매도 | `period`, `oversold`, `overbought` |
| `macd` | MACD 교차 | `fast`, `slow`, `signal` |
| `ml_base` | ML 모델 기반 (확장 가능) | `model_path`, `buy_threshold` |

전략 추가 방법:

```python
# engine/app/strategies/rules/my_strategy.py
from ..base import AbstractStrategy, MarketSnapshot, Signal, SignalType

class MyStrategy(AbstractStrategy):
    def evaluate(self, snapshot: MarketSnapshot) -> Signal:
        # 매매 로직 구현
        return Signal(
            strategy_id=self.strategy_id,
            symbol=snapshot.symbol,
            signal_type=SignalType.BUY,
            confidence=0.8,
            reason="내 조건 충족",
        )
```

---

## 브로커 설정

### 한국투자증권 (기본)

1. [apiportal.koreainvestment.com](https://apiportal.koreainvestment.com) 에서 앱 등록
2. App Key / Secret 발급
3. `.env`에 입력
4. `KIS_IS_VIRTUAL=true`로 모의투자 먼저 테스트

### Kiwoom (선택 - Windows 필요)

Kiwoom OpenAPI+는 Windows COM 기반이라 Mac에서 직접 실행 불가.
`kiwoom-bridge/bridge_server.py`를 Windows 머신/VM에서 실행한 후:

```env
KIWOOM_BRIDGE_URL=http://your-windows-ip:9091
```

---

## 리스크 관리

`engine/app/engine/risk.py`에서 설정:

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `max_position_ratio` | 10% | 종목당 최대 포트폴리오 비율 |
| `default_stop_loss_pct` | 3% | 자동 손절 기준 |
| 거래당 비중 | 5% | `runner.py`의 `trade_value` 비율 |

---

## 개발 가이드

### 브랜치 전략

- `main` - 안정 버전
- `claude/trading-app-improvement-*` - 개발 브랜치

### 새 전략 추가 흐름

1. `engine/app/strategies/rules/` 또는 `ml/` 에 전략 파일 추가
2. `engine/app/main.py`의 `strategy_classes` 딕셔너리에 등록
3. UI 전략 선택 목록에 `engine/app/api/routes/strategies.py`의 `AVAILABLE_STRATEGIES`에 추가
4. `make deploy`

### 로컬 엔진 직접 테스트

```bash
cd engine
pip install -r requirements.txt
uvicorn app.main:app --reload --port 9090
# → http://localhost:9090/docs  (Swagger UI)
```

---

## 주의사항

- **실전투자 전 반드시 모의투자(`KIS_IS_VIRTUAL=true`)로 충분히 검증**
- `k8s/secrets/secrets.yaml`은 절대 git에 커밋하지 않을 것 (`.gitignore` 처리됨)
- KRX 운영 시간(09:00~15:30 KST 평일)에만 자동 실행됨
- 전략 활성화 시 자동으로 실주문이 발생할 수 있음
