---
name: stair-step-pattern
description: Use when the user asks to find Korean stocks forming an early-stage stair-step uptrend (계단식 상승) for pre-emptive buying (선취매). Screens KOSPI/KOSDAQ for stage-1 or stage-2 base-and-breakout patterns using moving-average alignment, volume expansion, and pullback depth.
license: MIT
---

# Stair-Step Pattern Screener (S급 계단식 상승)

## When to use
- 사용자가 "S급 차트", "계단식 상승", "선취매 대상", "계단 1~2번째" 같은 표현으로 초기 단계 추세 상승 종목을 찾을 때.
- 이미 급등한 종목을 걸러내고 눌림/재돌파 직전 종목만 보고 싶을 때.
- 한국 시장(KOSPI/KOSDAQ)에 한정.

## Inputs
| 이름 | 타입 | 기본 | 설명 |
|------|------|------|------|
| max_stage | int | 2 | 허용 최대 계단 수 (>2 면 이미 늦었다고 판단) |
| limit | int | 20 | 반환 종목 수 상한 |
| markets | list[str] | ["KOSPI","KOSDAQ"] | 대상 시장 |

## Algorithm
1. `stock_master.ensure_loaded()` 로 전종목 리스트 확보.
2. 각 종목 일봉 200봉 (`broker.get_ohlcv(symbol, 'D', 200)`).
3. 계단 카운트 (최근 120봉):
   - 횡보 구간: `rolling(20).std() < close.mean() * 0.04`
   - 돌파봉: `close > prior_20_high * 1.05` AND `volume > volume_20ma * 1.8`
4. 현재 stage = 돌파봉 누적. `stage <= max_stage` 만 통과.
5. 정배열: MA5 > MA20 > MA60.
6. 눌림 적정: 현재가가 MA20 의 ±3% 이내.
7. `change_pct_30d` 오름차순 정렬 → 상위 `limit`.

## Entry point
- `engine/app/hanriver/screener.py::screen_stair_step(max_stage, limit, markets)` (이 skill 과 함께 추가됨)
- 의존: `indicators.sma`, `stock_master.ensure_loaded`, `broker.get_ohlcv`.

## Output
```python
[
  {
    "symbol": "005930",
    "name": "삼성전자",
    "market": "KOSPI",
    "stage": 2,
    "close": 72000.0,
    "ma20": 71200.0,
    "ma60": 68500.0,
    "pullback_pct": 1.12,
    "volume_ratio": 1.34,
    "change_pct_30d": 12.4,
    "reason": "20일선 지지 + MA 정배열 + 계단 2번째"
  }
]
```

## Caveats
- 장 마감 후 T-1 일봉 기준. 장중엔 마지막 봉 불완전.
- pykrx 장애 시 네이버 스크랩 fallback. 전종목 스캔 ~30초.
- **제안만 생성** — 자동 주문과 무관.

## Example invocation
> "지금 계단식 상승 초기(1~2단계) 종목 추천해줘. 선취매 목적이야."
> "S급 차트 되기 전에 진입할 수 있는 KOSDAQ 종목 스크리닝해."
