"""텔레그램 봇 알림.

TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 미설정 시 no-op.
"""
from __future__ import annotations

import logging

import httpx

from ...core.config import settings
from ...models.hanriver import AiSignal

logger = logging.getLogger(__name__)


async def send_text(text: str) -> bool:
    token = getattr(settings, "telegram_bot_token", "")
    chat_id = getattr(settings, "telegram_chat_id", "")
    if not token or not chat_id:
        logger.debug("Telegram 미설정 — 알림 건너뜀")
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            )
            r.raise_for_status()
            return True
    except Exception as e:
        logger.warning("Telegram 전송 실패: %s", e)
        return False


async def send_signal(sig: AiSignal) -> bool:
    mode_ko = "데이" if sig.mode == "day" else "스윙"
    arrow = {"buy": "🟢 매수", "sell": "🔴 매도", "hold": "⚪ 관망"}.get(sig.signal, sig.signal)
    parts = [
        f"*[HANRIVER] {arrow} 제안 · {mode_ko}*",
        f"종목: {sig.name} ({sig.symbol})",
    ]
    if sig.entry_price:
        parts.append(f"진입: {sig.entry_price}")
    if sig.stop_loss:
        parts.append(f"손절: {sig.stop_loss}")
    if sig.take_profit:
        parts.append(f"목표: {sig.take_profit}")
    parts.append(f"확신도: {float(sig.confidence):.0%}")
    return await send_text("\n".join(parts))
