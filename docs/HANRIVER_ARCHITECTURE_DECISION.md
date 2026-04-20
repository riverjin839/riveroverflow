# 기존 인프라 재사용 여부 결정

> 상위 문서: [HANRIVER_PLAN.md](./HANRIVER_PLAN.md)
> 결정일: 2026-04-20

## 질문

HANRIVER를 구축할 때 기존 `riveroverflow` 자동매매 플랫폼의
`engine/`·`gateway/`·`frontend/` 스택을 **재사용**할 것인가, **새로
분리**할 것인가?

## 현재 스택 현황

| 레이어 | 기존 | HANRIVER 기획 (§6) |
|--------|------|---------------------|
| Frontend | React 18 + Vite + Tailwind | Next.js + Tailwind |
| Backend API | Python FastAPI | Python FastAPI |
| Gateway | Go Fiber | (명시 없음, 재사용 가능) |
| DB | PostgreSQL + Redis | PostgreSQL + TimescaleDB + Redis + pgvector |
| 브로커 | python-kis / Kiwoom bridge | KIS API + Kiwoom proxy |
| 배포 | Kind K8s + `make deploy` | Docker + K8s (홈랩) |

## 옵션 비교

| 항목 | A. 완전 재사용 | B. 모노레포 내 분리 (추천) | C. 별도 레포 |
|------|---------------|--------------------------|--------------|
| 초기 속도 | ★★★ | ★★ | ★ |
| 관심사 분리 | ★ | ★★ | ★★★ |
| 코드 공유 (브로커, DB 모델) | ★★★ | ★★★ | ★ |
| 장기 독립성 | ★ | ★★ | ★★★ |
| CI/CD 부담 | 낮음 | 낮음 | 높음 |

## 결정: **B. 모노레포 내 분리**

### 구체 방침

1. **Backend**: 기존 `engine/app/api/routes/hanriver.py` 라우터를 추가.
   브로커 레이어(`engine/app/broker/`), DB 세션(`engine/app/core/`)을
   그대로 공유. 향후 규모가 커지면 `engine/hanriver/`로 모듈 승격하고,
   최종 단계에서 독립 서비스(`hanriver-api`)로 분리 가능하도록 의존성을
   한 방향으로만 유지한다(`hanriver → shared`, 역방향 금지).

2. **Frontend**: 기존 React + Vite를 유지하되 `/views/hanriver/`
   라우트 트리를 추가. **Next.js 전환은 Phase 5로 보류**.
   이유:
   - Phase 1 MVP는 SSR 요구가 낮음 (실시간 시세는 WebSocket)
   - 기존 Vite 빌드·배포 파이프라인·`lightweight-charts` 통합이 이미 완성
   - Next.js 전환의 개발 비용(라우팅 재작성, Vite 툴체인 제거)이 당장의
     가치보다 크다
   - 기획서 §6의 Next.js는 추천이며 강제 요건이 아님

3. **Gateway**: 기존 Go Fiber에 `/api/hanriver/*` 경로만 추가. WebSocket
   허브도 동일한 Redis pub/sub에 hanriver 채널(`market`, `news`) 붙여
   재사용.

4. **DB**: 기존 PostgreSQL 인스턴스에 **TimescaleDB 확장**과 **pgvector
   확장**을 `CREATE EXTENSION`으로 추가. 별도 DB 인스턴스를 띄우지 않는다.
   HANRIVER 전용 테이블은 `hanriver_` prefix를 붙이는 대신 논리적으로
   분리된 이름(`market_indices`, `news_items` 등)을 사용하고, 필요 시
   스키마(schema)로 분리 가능성을 열어둔다.

5. **K8s**: 별도 네임스페이스 `hanriver`를 만들지 않고 기존
   네임스페이스에 함께 배포한다. Ingestion DAG만 CronJob으로 분리.
   → §NAMING에서 정했던 `hanriver` 네임스페이스는 **이 문서에서 철회**하고
   공용 네임스페이스로 수정한다. 운영 부담 최소화 우선.

### 재사용하지 않는 것

- **전략 엔진 자동 연동**: HANRIVER는 매매 *제안*만 하고 자동 주문은
  내지 않는다. `engine/app/engine/runner.py`의 자동매매 루프와는
  **독립적으로** 동작. AI 시그널이 생성되면 `ai_signals` 테이블에
  기록만 하고, 사용자가 명시적으로 RIVERFLOW 자동매매 전략으로
  승격할 때만 연결한다. (§10 리스크 — "최종 판단은 내가 한다")

- **Kiwoom bridge 직접 호출**: Phase 1-2에서는 KIS만 사용. 키움은
  Phase 3 조건검색 연동 시점에 추가.

## 후속 수정사항

- [HANRIVER_NAMING.md](./HANRIVER_NAMING.md)의 K8s 네임스페이스 항목
  업데이트 필요 (전용 `hanriver` → 기존 네임스페이스 공용).
- [HANRIVER_PHASE1_SPEC.md](./HANRIVER_PHASE1_SPEC.md) §9의 프론트엔드
  미결정 항목은 **기존 React(Vite)에 통합**으로 확정.
