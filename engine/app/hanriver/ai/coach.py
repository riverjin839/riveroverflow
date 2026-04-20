"""AI 복기 코치. 매매 일지 항목을 읽고 비평/피드백 생성."""
from __future__ import annotations

from ...models.hanriver import TradingJournalEntry
from . import claude_client


async def critique(entry: TradingJournalEntry) -> dict:
    prompt = f"""다음 매매 체결을 복기 코칭해 줘 (한국어, 마크다운).

- 일자: {entry.trade_date}
- 종목: {entry.name} ({entry.symbol})
- 사이드: {entry.side}
- 수량: {entry.quantity}
- 체결가: {entry.price}
- 손익: {entry.pnl}
- 셋업 태그: {entry.setup or '미지정'}
- 사용자 메모: {entry.user_note or '(없음)'}

요청 섹션:
1. **진입 타이밍 평가**
2. **손절/익절 준수 여부 추정**
3. **개선 제안** (2~3가지 bullet)
4. **셋업이 성공 패턴인지 / 반복되는 실패 패턴인지 의견**
"""
    md = await claude_client.complete(prompt, max_tokens=800, temperature=0.4)
    return {"entry_id": entry.id, "critique_md": md}
