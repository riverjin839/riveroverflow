# HANRIVER Phase 1 MVP 상세 스펙

> 상위 문서: [HANRIVER_PLAN.md](./HANRIVER_PLAN.md) §8 Phase 1
> 기간: 4주 | 목표: **시황을 한 화면에서 보는 대시보드**

---

## 1. 스코프

### In Scope (Phase 1)

- 실시간 시황 대시보드 단일 페이지 (`/hanriver/dashboard`)
- 국내/해외 지수, 환율/원자재, 시장 심리 위젯
- 시장 히트맵 (업종별)
- 뉴스 피드 단순 버전 (소스 2개: 한경 + DART 공시)
- 기본 종목 검색 + 차트 뷰 (기존 `StockChart` 재사용)
- K8s 매니페스트 (`hanriver` 네임스페이스)
- CI/CD: 기존 `make deploy` 파이프라인에 hanriver 컴포넌트 합류

### Out of Scope (Phase 2+)

- 수급 데이터 상세, VSA, 세력주 분석
- AI 시그널 생성, Claude 리포트
- 매매 일지 연동, 복기 타임머신
- 키움 조건검색 연동
- 포트폴리오/리스크 관리

---

## 2. 화면 와이어프레임 (텍스트)

```
┌─────────────────────────────────────────────────────────────────────┐
│  HANRIVER  │ 검색 [__________]       한강 흐름을 읽다     [설정][⚙]│
├─────────────────────────────────────────────────────────────────────┤
│ ▼ 국내 지수                                                          │
│ ┌─────────┬─────────┬─────────┬─────────┐                            │
│ │ KOSPI   │ KOSDAQ  │ KOSPI200│ 야간선물 │                            │
│ │ 2,612.1 │ 844.3   │ 347.8   │ 341.2   │  ← 숫자 + 전일대비 색상    │
│ │ +0.42%  │ -1.12%  │ +0.38%  │ +0.05%  │  (녹색 상승/빨강 하락)     │
│ └─────────┴─────────┴─────────┴─────────┘                            │
│                                                                       │
│ ▼ 해외 지수                                                          │
│ ┌────┬─────┬──────┬────────┬──────┬──────┬────┬────┐                 │
│ │ DJ │NSDQ │ SPX  │ RUSSELL│ NKY  │ SSE  │HSI │TWSE│                 │
│ └────┴─────┴──────┴────────┴──────┴──────┴────┴────┘                 │
│                                                                       │
│ ▼ 환율/원자재         │ ▼ 시장 심리                                   │
│ USD/KRW  1,362.5 +0.3 │ VIX        13.8  ▂▃▅                         │
│ DXY      104.3  -0.1 │ F&G Index  52     (Neutral)                   │
│ WTI      82.1  +1.2 │ EWY        61.2  +0.8%                         │
│ 금        2,345 +0.4 │ NDF 1M     1,365.2                             │
│ BTC       67.8k +2.1│                                                 │
│ US10Y     4.28%     │                                                 │
│                                                                       │
│ ▼ 업종 히트맵 (트리맵)                                               │
│ ┌────────────────────────────────────────────┐                        │
│ │ 반도체 +2.1% │ 2차전지 -0.8% │ 바이오 +0.4 │                        │
│ │ ──────────  │ ─────────── │ ────────── │                        │
│ │ 금융 +0.3%  │ 건설 -1.5%  │ 조선 +3.2% │                        │
│ └────────────────────────────────────────────┘                        │
│                                                                       │
│ ▼ 뉴스 & 공시 (최신 20건)                                            │
│ [10:42] 한경  삼성전자 HBM 공급 확대...           [상]               │
│ [10:38] DART  SK하이닉스 / 주요사항보고서...       [중]               │
│ [10:33] 한경  연준, 9월 금리 동결 가능성...        [중]               │
│ ...                                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### 반응형 브레이크포인트

- `≥1440px`: 지수·심리·환율을 한 행에 배치
- `1024–1440px`: 2열 그리드
- `<1024px` (태블릿): 수직 스택, 히트맵 축소
- 모바일 스코프 아님 (Phase 5)

---

## 3. 컴포넌트 분해

| 컴포넌트 | 담당 | 데이터 소스 |
|---------|------|------------|
| `<IndexCardGrid />` | 국내/해외 지수 카드 | KIS API + yfinance |
| `<FxCommodityPanel />` | 환율/원자재 | yfinance + BOK ECOS |
| `<SentimentPanel />` | VIX, F&G, EWY, NDF | yfinance + CNN F&G 스크래핑 |
| `<SectorHeatmap />` | 업종별 트리맵 | KRX 업종 지수 API |
| `<NewsFeed />` | 뉴스/공시 스트림 | RSS(한경) + DART OpenAPI |
| `<SearchBar />` | 종목 검색 | 기존 `stock_master` 테이블 |

---

## 4. 백엔드 엔드포인트

신규 FastAPI 라우터 `engine/app/api/routes/hanriver.py`:

| 메서드 | 경로 | 응답 |
|-------|------|------|
| GET | `/hanriver/indices` | 국내/해외 지수 스냅샷 (5초 캐시) |
| GET | `/hanriver/fx` | 환율/원자재 (30초 캐시) |
| GET | `/hanriver/sentiment` | VIX, F&G, EWY, NDF (60초 캐시) |
| GET | `/hanriver/heatmap/sectors` | 업종 등락률 (30초 캐시) |
| GET | `/hanriver/news?limit=20` | 통합 뉴스/공시 피드 |
| WS | `/hanriver/ws/market` | 지수 틱 스트림 (Redis pub/sub) |

Gateway(`/api/hanriver/*`)로 리버스 프록시. 기존 `proxy/engine.go` 패턴
재사용.

---

## 5. 데이터 수집 파이프라인

```
Airflow DAG                  수집 주기
───────────────────────      ─────────
ingest_kis_indices           실시간 (WS)
ingest_yfinance_global       5분
ingest_fx_commodities        5분
ingest_krx_sector_snapshot   30초 (장중)
ingest_news_rss_hankyung     2분
ingest_dart_disclosures      1분
```

MVP 단계에서는 Airflow 없이 FastAPI 백그라운드 태스크(asyncio)로 시작하고,
Phase 2에서 Airflow로 이관. 이유: 4주 내 인프라 복잡도 절감.

---

## 6. 데이터 모델 (Phase 1 한정)

```sql
-- TimescaleDB hypertable
CREATE TABLE market_indices (
    ts         TIMESTAMPTZ NOT NULL,
    code       TEXT        NOT NULL,  -- KOSPI, KOSDAQ, DJI, ...
    price      NUMERIC(12,4),
    change_pct NUMERIC(6,3),
    PRIMARY KEY (ts, code)
);
SELECT create_hypertable('market_indices', 'ts');

CREATE TABLE news_items (
    id          BIGSERIAL PRIMARY KEY,
    source      TEXT,           -- hankyung, dart
    published_at TIMESTAMPTZ,
    title       TEXT,
    url         TEXT UNIQUE,
    importance  TEXT,           -- Phase 1: 'unknown' 고정, Phase 3에서 LLM 스코어링
    raw_payload JSONB
);
CREATE INDEX ON news_items (published_at DESC);
```

기존 `stock_master`는 재사용.

---

## 7. 주간 마일스톤

| 주차 | 목표 |
|------|------|
| **Week 1** | K8s 네임스페이스, DB 스키마, KIS 인덱스 수집 + `/indices` API, 스켈레톤 페이지 |
| **Week 2** | yfinance/환율/원자재/심리 위젯, 업종 히트맵 수집 및 렌더 |
| **Week 3** | 뉴스 RSS + DART 수집, `<NewsFeed />`, 종목 검색 바 |
| **Week 4** | WebSocket 실시간 틱, 반응형 스타일링, E2E smoke test, 홈랩 배포 |

---

## 8. 성공 기준 (Phase 1 Gate)

- 대시보드 초기 렌더 **< 1초** (서버 측 캐시 히트 기준)
- 지수 WebSocket 레이턴시 **< 500ms**
- 홈랩 24시간 가동 중 패닉/크래시 0건
- 모든 위젯이 빈 상태(empty state) UI를 가짐
- 뉴스 수집 장애 시 차트 패널은 독립적으로 동작 (fault isolation)

---

## 9. 미결정 (Phase 1 킥오프 전 확정 필요)

- [ ] KIS 실계좌 vs 모의투자 중 수집에 사용할 계정 (모의투자는 일부 지수 제한)
- [ ] CNN F&G 스크래핑 법적 이슈 검토 → 대체로 alternative.me 크립토 F&G 고려
- [ ] 업종 분류 기준: KRX 업종 vs WICS
- [x] ~~프론트엔드: 기존 React(Vite)에 통합 vs 신규 Next.js 라우트~~
  → **기존 React(Vite)에 통합** 확정 (ARCHITECTURE_DECISION §2)
