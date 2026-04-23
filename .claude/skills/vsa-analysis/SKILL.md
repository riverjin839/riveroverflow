---
name: vsa-analysis
description: Use when the user asks to interpret a stock's VSA (Volume Spread Analysis) signals — Sign of Strength (세력 매집), Sign of Weakness (분배), Upthrust, Test. Calls indicators.vsa() on recent OHLCV and explains signals with supply/demand context.
license: MIT
---

# VSA Analysis — 세력주 판단

## When to use
- "VSA 봐줘", "세력 매집 흔적 있어?", "분배 나온 거 같은데?" 같은 질문.
- 특정 종목의 거래량·스프레드 관계로 세력 동향을 파악하고 싶을 때.

## Inputs
| 이름 | 타입 | 설명 |
|------|------|------|
| symbol | str | 6자리 종목코드 |
| lookback | int | VSA 비교 기준 기간 (default 30) |
| days | int | OHLCV 수집 기간 (default 120) |

## VSA 룰 (Tom Williams)
- **SOS (Sign of Strength)**: 거래량 급증 + 큰 하락봉 but 종가가 중간 이상 → 세력 매집
- **SOW (Sign of Weakness)**: 거래량 급증 + 큰 상승봉 but 종가가 중간 이하 → 분배
- **Upthrust**: 전고점 돌파 후 같은 봉에서 반락
- **Test**: 좁은 스프레드 + 거래량 축소 (매도 압력 소진 확인)

## Entry points
- `engine/app/hanriver/indicators.py::vsa(df, lookback)` — boolean Series 반환
- `engine/app/hanriver/indicators.py::latest_snapshot(df)` — 최근 봉 요약 dict
- `engine/app/hanriver/flow.py::fetch_flow(symbol, days=5)` — 수급으로 교차 검증
- `engine/app/hanriver/ai/claude_client.py::complete` — 자연어 해설 생성

## 권장 해석 워크플로
1. 최근 봉에서 `sos | sow | upthrust | test` 중 활성화된 시그널 확인.
2. 직전 5일 수급(`fetch_flow`)과 매칭 — SOS 인데 외국인 순매도면 신뢰도 낮음.
3. `close_pos` 와 `vol_ratio` 수치를 함께 보여줌.
4. Claude 에게 "다음 특징으로 2~3문장 해설" 프롬프트로 요청.

## Output (권장 형식)
```
[005930 삼성전자] VSA 진단
- SOS 감지 (vol_ratio=2.3, close_pos=0.62)
- 외국인 5일 순매수 ₩1,240억 → 시그널 보강
- 해설: 큰 하락봉이지만 종가 방어 + 거래량 급증. 세력 매집 초기 추정.
- 주의: 지지선 이탈 시 Test 로 전환 가능.
```

## Example invocation
> "005930 VSA 봐줘"
> "카카오 세력 매집 흔적 있어?"
