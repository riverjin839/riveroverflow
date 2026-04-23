---
name: limit-up-screen
description: Use when the user asks about today's limit-up (상한가) or top rising (급등) Korean stocks and wants AI-generated reasons for each rise. Scrapes Naver rankings and enriches each candidate with DART disclosures and recent news.
license: MIT
---

# Today's Limit-Up + AI Reason

## When to use
- "오늘 상한가 종목 뭐 있어?", "급등주 이유 알려줘" 같은 질문.
- 장중/장 마감 직후 뉴스·공시와 결합한 상승 원인 요약이 필요할 때.

## Entry point
- `engine/app/hanriver/limit_up.py::get_limit_up_report(target=None, force=False, enable_llm=True)`
- 내부 호출: `naver_ranking.fetch_upper_limit()`, `fetch_top_risers(min=10%)`, `disclosures.list_symbol_disclosures`, `naver.fetch_naver_stock`, Claude.

## Inputs
| 이름 | 타입 | 기본 | 설명 |
|------|------|------|------|
| target | date \| None | 오늘 | 과거 날짜면 pykrx fallback |
| force | bool | False | True 면 캐시 무시하고 재생성 |
| enable_llm | bool | True | False 면 reason 필드 None |

## Output schema
```python
{
  "date": "2026-04-23",
  "source": "naver",
  "limit_up_count": 4,
  "surge_count": 17,
  "total_trading_value": 1_240_000_000_000,
  "items": [
    {
      "symbol": "...", "name": "...", "market": "KOSDAQ",
      "close": 22000.0, "change_pct": 29.9, "trading_value": 31_000_000_000,
      "category": "limit_up",
      "reason": "2024 1Q 깜짝 흑자전환 공시 + HBM 관련 수주 추정",
      "news": [...], "disclosures": [...]
    }
  ]
}
```

## Caveats
- 캐시 TTL: 당일 30초 / 과거 1시간.
- LLM 호출은 `limit_up` 카테고리만 — 비용 관리.
- `DART_API_KEY` 없으면 공시 필드 비어 있음.

## Example invocation
> "오늘 상한가 종목이랑 AI 이유 정리해줘"
> "어제 상한가 몇 개였어?" (과거 날짜 지정)
