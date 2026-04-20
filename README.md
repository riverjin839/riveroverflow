# RiverOverflow · HANRIVER

개인용 한국 주식 자동매매 플랫폼(**RIVERFLOW**) + AI 트레이딩 자비스(**HANRIVER**).
macOS Sonoma 테마의 단일 React 앱으로 통합 운영.

```
┌─ RIVERFLOW ─────────────── 자동 매매 엔진
│   KIS / Kiwoom 브로커, 전략 플러그인, 주문 실행
└─ HANRIVER  ─────────────── AI 트레이딩 자비스
    실시간 시황 · 상한가 분석 · VSA/수급 · AI 시그널 · 복기 · 백테스트
```

---

## 1. 한눈에 보기

| 레이어 | 기술 | 경로 |
|---|---|---|
| Frontend | React 18 · Vite · Tailwind · three.js | `frontend/` |
| Gateway | Go 1.22 · Fiber v2 | `gateway/` |
| Engine | Python 3.12 · FastAPI · SQLAlchemy 2.x | `engine/` |
| DB · Cache | PostgreSQL 16 · Redis 7 | `k8s/postgres`, `k8s/redis` |
| LLM | Anthropic Claude (`claude-sonnet-4-6` / `claude-opus-4-7`) | `engine/app/hanriver/ai/claude_client.py` |
| 배포 | Docker + Kind K8s + ArgoCD 호환 | `k8s/`, `Makefile` |

---

## 2. 빠른 시작

```bash
# 로컬 개발 (Docker Compose — hot reload)
make dev
# → http://localhost:3000 (UI) · :8080 (Gateway) · :9090 (Engine)

# Kind K8s 최초 설치
make setup
cp k8s/secrets/secrets.yaml.example k8s/secrets/secrets.yaml   # 값 입력
kubectl apply -f k8s/secrets/secrets.yaml

# 빌드·로드·배포 원스텝
make deploy
```

---

## 3. 디렉터리 지도

```
riveroverflow/
├── frontend/                          # React 18 + Vite + Tailwind
│   └── src/
│       ├── components/                # 공용 UI (MacWindow, StockSearchInput...)
│       ├── views/
│       │   ├── hanriver/              # ★ HANRIVER 자비스 페이지 전체
│       │   │   ├── HanriverDashboardPage.tsx   # 시황 대시보드 (Hero + Details)
│       │   │   ├── LimitUpPage.tsx             # 오늘의 상한가 · AI 상승 이유
│       │   │   ├── StockDetailPage.tsx         # 종목 심층 (VSA · 수급 · 공시)
│       │   │   ├── SignalsPage.tsx             # AI 매매 시그널
│       │   │   ├── HanriverReportsPage.tsx     # AI 리포트 (Daily/Weekly/Stock)
│       │   │   ├── JournalPage.tsx             # 매매 일지 + AI 복기 코치
│       │   │   ├── ReplayPage.tsx              # 타임머신 복기
│       │   │   ├── BacktestPage.tsx            # 백테스트
│       │   │   └── WatchlistPage.tsx           # 관심 종목 · 알림
│       │   ├── ontology/              # 도메인 온톨로지 + 3D 시각화
│       │   ├── dashboard/             # RIVERFLOW 자동매매 대시보드
│       │   ├── portfolio/ · strategies/ · screener/ · research/ · reports/ · analytics/
│       │   └── auth/ · settings/
│       ├── presenters/                # Axios 클라이언트 · 폴링 훅
│       └── models/                    # Zustand 스토어
│
├── gateway/                           # Go Fiber API Gateway
│   └── internal/
│       ├── handlers/                  # auth, health
│       ├── middleware/                # JWT (REST + WS)
│       ├── proxy/engine.go            # → Engine 리버스 프록시
│       └── ws/hub.go                  # Redis pub/sub → WebSocket broadcast
│
├── engine/                            # Python FastAPI 트레이딩 엔진
│   └── app/
│       ├── broker/                    # KIS · Kiwoom · PublicBroker(pykrx)
│       ├── strategies/                # AbstractStrategy 플러그인 (rules/ml)
│       ├── engine/                    # 매매 루프 · 리스크 · KRX 스케줄러
│       ├── models/                    # SQLAlchemy 모델 (trade, ontology, hanriver)
│       ├── api/routes/                # FastAPI 라우터
│       └── hanriver/                  # ★ HANRIVER 서비스 레이어
│           ├── market_snapshot.py     # 시황 집계 + TTL 캐시
│           ├── fetchers.py            # yfinance (해외/환율/원자재)
│           ├── naver.py               # 네이버 실시간 지수 + 검색
│           ├── naver_ranking.py       # 상한가·급등 순위 스크랩
│           ├── stock_master.py        # 로컬 종목 마스터 (자동완성)
│           ├── indicators.py          # MA/RSI/MACD/Bollinger + VSA
│           ├── flow.py                # 수급 (외국인·기관·개인·공매도)
│           ├── disclosures.py         # DART OpenAPI
│           ├── limit_up.py            # 상한가 리포트 + AI 상승이유
│           ├── journal.py             # trades → 일지 자동 초안
│           ├── replay.py              # 타임머신 스냅샷
│           ├── backtest.py            # 벡터화 백테스트 (ma_cross/rsi/vsa)
│           ├── scheduler.py           # Daily/Weekly 리포트 크론
│           ├── notify/telegram.py     # 시그널·리포트 알림
│           └── ai/
│               ├── claude_client.py   # Anthropic SDK + 프롬프트 캐싱
│               ├── signal_generator.py # 룰 + LLM 하이브리드
│               ├── news_scoring.py    # 뉴스 importance 스코어링
│               ├── report_builder.py  # Daily/Weekly/Stock 리포트
│               └── coach.py           # 매매 일지 AI 코치
│
├── k8s/                               # Kubernetes manifest
├── kiwoom-bridge/                     # Windows COM 브릿지 (선택)
├── scripts/                           # kind-setup.sh 등
├── docs/                              # 기획·설계 문서
│   ├── HANRIVER_PLAN.md               # 전체 기획서
│   ├── HANRIVER_NAMING.md             # 네이밍 규약
│   ├── HANRIVER_PHASE1_SPEC.md        # Phase 1 MVP 스펙
│   └── HANRIVER_ARCHITECTURE_DECISION.md
├── Makefile                           # setup/dev/build/deploy 원스톱
├── docker-compose.yml                 # 로컬 개발 (K8s 없이)
├── CLAUDE.md                          # AI 에이전트 온보딩
└── README.md                          # 이 문서
```

---

## 4. HANRIVER 데이터 소스

| 용도 | 소스 | 접근 방식 | 인증 |
|---|---|---|---|
| 국내 지수 (실시간) | `m.stock.naver.com` | REST JSON | 불필요 |
| 상한가·급등 순위 | `finance.naver.com/sise/sise_upper.naver` | HTML 스크랩 | 불필요 |
| 종목 자동완성 | 로컬 마스터 (Naver 시총 페이지 수집) | HTML 스크랩 + 인메모리 인덱스 | 불필요 |
| 종목 뉴스 | `m.stock.naver.com/api/news/stock/{code}` | REST JSON | 불필요 |
| 수급·OHLCV | pykrx | KRX 공공 API | 불필요 |
| 공시 | DART OpenAPI | REST JSON | `DART_API_KEY` |
| 해외 지수·환율·원자재·VIX | yfinance | Python lib | 불필요 |
| 실시간 시세·주문 | 한국투자증권(KIS) | REST + WS | `KIS_*` |
| 조건검색 (선택) | Kiwoom OpenAPI+ | Windows bridge | 별도 VM |

---

## 5. 환경 변수

```env
# ── 필수 (자동매매만) ──────────────────────────
KIS_APP_KEY=
KIS_APP_SECRET=
KIS_ACCOUNT_NO=12345678-01
KIS_IS_VIRTUAL=true                # true=모의투자부터 시작

JWT_SECRET=dev-secret-change       # 32자+ 권장

# ── 선택 (HANRIVER 고도화) ────────────────────
DART_API_KEY=                      # 공시 실시간
ANTHROPIC_API_KEY=                 # AI 시그널/리포트/코치 (없으면 stub)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

HANRIVER_DAILY_REPORT_ENABLED=false     # 장 마감 후 자동 리포트
HANRIVER_WEEKLY_REPORT_ENABLED=false
```

---

## 6. 핵심 명령

```bash
make help               # 전체 명령
make dev                # docker-compose (hot reload)
make dev-down           # 볼륨 포함 종료 (의존성 변경 후 필수)
make setup              # Kind 클러스터 초기화
make deploy             # 빌드 + kind load + 배포
make deploy-engine      # Engine만 재배포
make deploy-frontend    # Frontend만 재배포
make logs-engine        # Engine 로그 follow
make status             # Pod 상태
make clean              # Kind 클러스터 삭제
```

---

## 7. 설계 원칙

- **개인 사용 전용.** 타인 대상 종목 추천은 유사투자자문업 이슈. 외부 공유·SaaS화 금지.
- **HANRIVER는 "제안"만.** 자동매매 루프(`runner.py`)와 분리되어 주문을 직접 내지 않음.
  사용자가 명시적으로 승격할 때만 RIVERFLOW 자동매매 전략으로 등록.
- **외부 API 실패 시 stub fallback.** 네이버·DART·Claude·yfinance 어느 하나가 죽어도
  다른 섹션은 계속 동작한다.
- **비용 관리.** Claude 호출은 상한가·리포트·복기 등 고가치 지점에만. 뉴스 스코어링은
  배치. 시스템 프롬프트는 캐시 제어(`cache_control: ephemeral`) 사용.
- **한국 시장 컨벤션.** 상승=빨강(`up`), 하락=파랑(`down`). VSA 용어는 원저자(Tom
  Williams) 표기 유지.

---

## 8. 추가 문서

- [docs/HANRIVER_PLAN.md](./docs/HANRIVER_PLAN.md) — 전체 기획서 (Phase 1-5)
- [docs/HANRIVER_PHASE1_SPEC.md](./docs/HANRIVER_PHASE1_SPEC.md) — MVP 스펙
- [docs/HANRIVER_ARCHITECTURE_DECISION.md](./docs/HANRIVER_ARCHITECTURE_DECISION.md)
- [CLAUDE.md](./CLAUDE.md) — AI 에이전트(Claude)를 위한 온보딩
