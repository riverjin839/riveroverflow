---
name: backtest-validate
description: Use when the user wants to backtest a rule-based strategy (ma_cross, rsi, vsa) on a Korean ticker with win-rate, profit factor, MDD, Sharpe, plus walk-forward (3:1 in-sample / out-of-sample) validation to check overfitting.
license: MIT
---

# Backtest + Walk-Forward 검증

## When to use
- 새 전략 아이디어를 실제 데이터로 검증하고 싶을 때.
- 기존 파라미터가 과적합인지 확인하고 싶을 때.
- 단순 백테스트 결과만으론 부족하고 out-of-sample 검증까지 원할 때.

## Entry points
- `engine/app/hanriver/backtest.py::run(broker, symbol, strategy, params, start_date, end_date)`
- Supported strategies: `ma_cross`, `rsi`, `vsa`

## Walk-forward 래핑 절차
1. 기간을 in-sample 75% / out-of-sample 25% 로 분할.
2. in-sample 에서 `backtest.run(...)` 호출 → 지표 기록.
3. out-of-sample 에서 동일 params 로 재실행 → 지표 기록.
4. 격차 점검: `win_rate` 차이 10%p 초과 또는 `profit_factor` 반토막 → 과적합 경고.

## Inputs
| 이름 | 타입 | 예시 |
|------|------|------|
| symbol | str | "005930" |
| strategy | str | "ma_cross" |
| params | dict | `{"short": 5, "long": 20}` |
| start_date | str | "2024-01-01" |
| end_date | str | "2025-12-31" |

## Output
```python
{
  "in_sample":  { "win_rate": 0.58, "profit_factor": 1.72, "mdd": -0.14, "sharpe": 1.05, "trade_count": 34 },
  "out_sample": { "win_rate": 0.41, "profit_factor": 0.93, "mdd": -0.19, "sharpe": 0.12, "trade_count": 9 },
  "overfit_warning": true,
  "diagnosis": "win_rate 격차 17%p, profit_factor < 1.0 → 과적합 가능성 높음"
}
```

## Caveats
- 수수료+슬리피지 0.15% 가정.
- 일봉 기준. 분봉 백테스트는 향후 Phase 5.
- OHLCV 부족(30일 미만) 시 빈 결과 반환.

## Example invocation
> "삼성전자 MA 5/20 크로스 전략을 2024년부터 백테스트하고 out-of-sample 도 봐줘."
> "VSA 전략 과적합 검증 돌려줘. 종목은 KQ150."
