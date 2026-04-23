---
name: trade-replay
description: Use when the user picks a past trade or date and wants to replay market conditions (chart + news + disclosures + indicators) alongside an AI coach critique. Produces a timewarp snapshot plus Claude-generated feedback on entry timing and stop-loss discipline.
license: MIT
---

# Trade Replay & AI Coach (타임머신 복기)

## When to use
- "그날 왜 샀는지 복기해줘", "진입 타이밍 평가해줘" 같은 요청.
- 특정 일자의 시황·뉴스·내 매매를 동시에 재현하고 싶을 때.

## Entry points
- `engine/app/hanriver/replay.py::snapshot(broker, session, symbol, target_date)`
- `engine/app/hanriver/ai/coach.py::critique(entry)` — AI 복기 코치

## Workflow
1. 대상 체결 선택: 매매일지 ID 또는 (symbol, date).
2. `replay.snapshot` 로 그날까지의 OHLCV 200봉, 기술적 지표, 전후 1일 뉴스, 같은 날 매매 기록을 한 번에 로드.
3. `coach.critique(entry)` 로 Claude 에 진입 타이밍·손절 준수·개선 제안 생성.
4. 마크다운 리포트로 반환.

## Output
```markdown
## [005930 삼성전자] 2025-12-05 매수 복기

### 진입 타이밍 평가
- MA20 터치 후 반등 초반 — 적절
- 다만 거래량 확인 전 진입 → 위험 감수

### 손절 준수 여부 추정
- 명시 손절가 -3% 대비 실제 -1.8% 에서 청산 → 규율 양호

### 개선 제안
- 거래량 ≥ 20ma * 1.3 확인 후 분할 진입 권장
- 뉴스 체크: 그날 오전 외국인 순매도 보도 있었음

### 셋업 판단
- "20일선 눌림 매수" 셋업으로 반복 기록 권장
```

## Caveats
- 뉴스는 DB 에 수집된 `NewsItem` 기준. 과거 데이터 누락 가능.
- `ANTHROPIC_API_KEY` 없으면 stub 응답.

## Example invocation
> "지난주 005930 매수 복기해줘"
> "2025-12-05 내 매매 AI 코칭 받아볼래"
