# Claude Agent Onboarding

이 문서는 Claude(또는 다른 AI 에이전트)가 이 저장소에 와서 **10분 안에 어디를
건드려야 할지** 알 수 있도록 설계되었다. README 는 사람 대상, 이 문서는 코딩
에이전트 대상.

---

## 1. 프로젝트 모델

두 개의 제품이 한 모노레포에 공존한다. 둘은 DB 와 인프라를 공유하지만 책임이
다르다.

```
┌──────────────── RIVERFLOW ─────────────────┐
│ 한국 주식 자동매매 플랫폼                      │
│ - 브로커: KIS(한국투자증권), Kiwoom           │
│ - 전략: AbstractStrategy 플러그인             │
│ - 실제 주문을 낸다                            │
└────────────────────────────────────────────┘
┌──────────────── HANRIVER  ─────────────────┐
│ 개인 트레이딩 AI 자비스                       │
│ - 제안만 한다 (주문 직접 X)                   │
│ - Claude · VSA · 수급 · 공시 · 뉴스 통합      │
│ - RIVERFLOW 일지와 양방향 연동                │
└────────────────────────────────────────────┘
```

---

## 2. "어디서 시작하나" 진입점

| 목적 | 파일 |
|---|---|
| 전체 라우팅 이해 | `frontend/src/App.tsx` · `frontend/src/components/layout/AppShell.tsx` |
| Engine 기동 · DI | `engine/app/main.py` (lifespan) |
| HANRIVER 라우터 | `engine/app/api/routes/hanriver.py` (모든 `/hanriver/*` 엔드포인트) |
| 자동매매 루프 | `engine/app/engine/runner.py` |
| 스케줄러 | `engine/app/engine/scheduler.py` + `engine/app/hanriver/scheduler.py` |
| Gateway | `gateway/cmd/server/main.go` |

---

## 3. 공통 도메인 용어 (약어 사전)

| 용어 | 의미 |
|---|---|
| KRX | 한국거래소 |
| KOSPI / KOSDAQ / KPI200 | 한국 대표 지수. 상승 한도 +30%. |
| KIS | 한국투자증권 OpenAPI. 실시간 시세·주문. |
| pykrx | KRX 공공 데이터 Python 래퍼. 일봉 종가(T-1) 위주. |
| DART | 전자공시. `DART_API_KEY` 필요. |
| VSA | Volume Spread Analysis. `SOS`(매집) / `SOW`(분배) / `Upthrust` / `Test`. |
| SOS | Sign of Strength. 큰 하락봉 + 거래량 급증 + 종가 중간 이상 → 세력 매집 추정. |
| SOW | Sign of Weakness. 큰 상승봉 + 거래량 급증 + 종가 중간 이하 → 분배 추정. |
| 눌림 스윙 | 추세 상승 중 20/60일선까지 되밀림 후 재상승 노리는 스윙 |
| 한국 컬러 컨벤션 | 상승 = 🔴, 하락 = 🔵 (반대 아님) |

---

## 4. 자주 쓰는 작업 패턴

### 새 API 엔드포인트 추가 (HANRIVER)

1. 서비스 로직: `engine/app/hanriver/<module>.py` 에 async 함수
2. 라우트: `engine/app/api/routes/hanriver.py` 에 `@router.get/post`
3. Pydantic 응답 모델은 같은 파일에 함께
4. 프론트 클라이언트: `frontend/src/presenters/useHanriverPhase2.ts` 에 메서드 추가
5. 페이지 컴포넌트: `frontend/src/views/hanriver/<Page>.tsx`
6. 라우트 등록: `frontend/src/App.tsx`
7. 사이드바: `frontend/src/components/layout/AppShell.tsx` `SECTIONS`

### 새 전략 추가 (RIVERFLOW)

1. `engine/app/strategies/rules/<name>.py` 에서 `AbstractStrategy` 상속
2. `engine/app/main.py` `strategy_classes` 딕셔너리에 등록
3. `engine/app/api/routes/strategies.py` `AVAILABLE_STRATEGIES` 에 추가
4. `make deploy`

### 새 DB 테이블

1. `engine/app/models/<도메인>.py` 에 SQLAlchemy 클래스
2. `engine/app/main.py` 상단에서 import (없으면 `create_all` 이 누락)
3. 재기동 시 자동 생성 (개발 환경). 운영은 Alembic.

### 외부 API 실패 처리 원칙

- **절대 500 을 그대로 노출하지 마라.** 라우트 레벨에서 try/except → 400/502
- 서비스 레벨에서 결과 없으면 stub/빈 리스트 반환
- 예: `hanriver/market_snapshot.py` 의 `_merge_with_stub`

---

## 5. 시각 디자인

**테마: macOS Sonoma 라이트.**
- 배경: `bg-surface` (#ededed)
- 카드: `card` utility (`bg-surface-card` + `border` + `rounded-2xl` + `shadow-mac`)
- 중첩 카드: `card-inner`
- 카드 상단: traffic light 헤더(`traffic-lights`) + 중앙 `.eyebrow` 타이틀
- 공용 카드 컴포넌트: `frontend/src/components/MacWindow.tsx`
  - `<MacWindow title="...">`, `<MacMiniCard>`, `<MacProgressBar>`
- 텍스트 계층: `text-ink` / `text-ink-muted` / `text-ink-subtle`
- 한국 컨벤션 따라 상승=`text-up`(빨강), 하락=`text-down`(파랑)

새 페이지를 만들 때는 반드시 `MacWindow` 와 `.eyebrow` 타이틀을 써서 일관성 유지.

---

## 6. 외부 서비스 의존 & Graceful Degradation

```
ANTHROPIC_API_KEY   없음 → claude_client._stub_complete 가 대체 응답 생성
DART_API_KEY        없음 → 공시 섹션만 빈 리스트
TELEGRAM_BOT_TOKEN  없음 → 알림만 skip
KIS_APP_KEY         없음 → PublicBroker(pykrx, 읽기 전용) 자동 fallback
yfinance            장애 → stub 시세 + stale=true 플래그
pykrx               장애 → 네이버 스크랩 우선 경로로 회피
Naver               장애 → pykrx fallback
```

설정 없이도 전체 UI 가 깨지지 않고 동작하는 것이 설계 원칙.

---

## 7. 위험한 영역 (건드릴 때 주의)

| 파일 | 주의 |
|---|---|
| `engine/app/engine/runner.py` | 실주문 발생 가능. 건드릴 때 `KIS_IS_VIRTUAL=true` 확인 |
| `engine/app/engine/scheduler.py` | KRX 시간대(09:00~15:30 KST)로 엔진을 자동 기동/정지 |
| `k8s/secrets/secrets.yaml` | `.gitignore` 처리. 절대 커밋 금지 |
| `engine/app/hanriver/ai/claude_client.py` | 프롬프트 캐싱(`cache_control`) 구조 유지 — 비용 |
| `frontend/src/components/StockSearchInput.tsx` | 앱 전역 자동완성. 디바운스 180ms 기준으로 다른 컴포넌트가 의존 |

---

## 8. 체크리스트: PR 전에

- [ ] `make dev` 로컬에서 정상 기동 확인
- [ ] 새 의존성 추가 시 `make dev-down && make dev` 로 node_modules/pip 재설치
- [ ] 한국 컨벤션 색상(상승=빨강, 하락=파랑) 준수했는지
- [ ] 외부 API 장애 시 500 대신 빈 결과 반환하는지
- [ ] 새 HANRIVER 페이지는 `MacWindow` 사용했는지
- [ ] 종목 심볼 입력 자리에는 `StockSearchInput` 썼는지 (raw `<input>` 금지)
- [ ] `docs/HANRIVER_PLAN.md` Phase 번호/스펙과 정합하는지

---

## 9. 자주 나오는 에러 & 해결

| 에러 | 원인 | 해결 |
|---|---|---|
| `Failed to resolve import "react-force-graph-3d"` | 익명 `node_modules` 볼륨에 새 deps 미반영 | `make dev-down && make dev` |
| `TS6306 Referenced project must have "composite"` | `tsconfig.node.json` 구버전 | 본 레포는 `composite:true` 설정됨. TS 버전 롤백 금지 |
| pykrx `JSONDecodeError` | KRX 공공 API 일시 400 | 네이버 스크랩 경로가 primary — 자동 회피됨 |
| `/signals/generate` 500 | 한글명을 symbol 로 전송 | 라우트에서 6자리 숫자 검증 → 400 반환. 자동완성 사용 강제 |
