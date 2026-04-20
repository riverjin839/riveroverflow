"""Claude API wrapper (prompt caching 포함).

- ANTHROPIC_API_KEY 미설정 시 _stub_complete 가 룰 기반 dummy 응답을 돌려주어
  시스템이 동작은 하도록 유지한다 (E2E 테스트·데모용).
- 모델: 기본 Claude Sonnet 4.6, 리포트/복기 등 깊이 필요한 곳은 Opus 4.7 권장.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from ...core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-6"
DEEP_MODEL = "claude-opus-4-7"

_SYSTEM_CACHEABLE = """너는 HANRIVER — 개인 트레이더의 AI 자비스다.
한국 주식 시장(KRX)에 특화되어 있으며, VSA(Volume Spread Analysis), 수급 분석,
뉴스/공시 해석에 강점이 있다. 모든 응답은 한국어로 간결하게 작성하고,
추천은 반드시 '제안(suggestion)'이라는 표현을 쓴다. 최종 결정은 사용자가 한다.
"""


async def complete(
    prompt: str,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
    temperature: float = 0.4,
) -> str:
    api_key = getattr(settings, "anthropic_api_key", "")
    if not api_key:
        return _stub_complete(prompt)

    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        logger.warning("anthropic SDK 미설치 — stub 응답 반환")
        return _stub_complete(prompt)

    client = AsyncAnthropic(api_key=api_key)
    try:
        resp = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=[
                {
                    "type": "text",
                    "text": system or _SYSTEM_CACHEABLE,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [b.text for b in resp.content if hasattr(b, "text")]
        return "".join(parts).strip()
    except Exception as e:
        logger.warning("Claude API 실패: %s — stub fallback", e)
        return _stub_complete(prompt)


def _stub_complete(prompt: str) -> str:
    """API 미설정/장애 시 확정적 응답. 키워드 기반 간단 룰.

    Phase 1-2 스모크 테스트가 이 경로로 돌아가도 프론트가 무너지지 않게 한다.
    """
    p = prompt.lower()
    if "시그널" in prompt or "signal" in p:
        return (
            "## 제안 요약\n"
            "- 현재 구간은 지지선 근접으로 관망 또는 분할 매수 제안.\n"
            "- VSA sign of strength 미확인 → 거래량 동반 확인 후 대응 권장.\n"
            "- 손절선은 직전 저점 아래로 설정.\n"
            "(※ ANTHROPIC_API_KEY 미설정 — 스텁 응답)"
        )
    if "리포트" in prompt or "report" in p:
        return (
            "## 시장 요약 (스텁)\n"
            "- KOSPI 는 전일 대비 혼조. 반도체·금융 순환매 관찰.\n"
            "- 환율은 달러 인덱스 흐름에 연동.\n"
            "- 다음 세션 관전 포인트: 외국인 수급 지속성.\n"
            "(※ ANTHROPIC_API_KEY 미설정 — 스텁 응답)"
        )
    if "복기" in prompt or "coach" in p:
        return (
            "## 복기 코멘트 (스텁)\n"
            "- 진입 시점은 적절했으나 손절선 준수 여부를 점검하세요.\n"
            "- 성공 셋업 패턴을 3회 이상 반복 기록하면 자동으로 선호 셋업으로 분류됩니다.\n"
            "(※ ANTHROPIC_API_KEY 미설정 — 스텁 응답)"
        )
    return "(※ ANTHROPIC_API_KEY 미설정 — 스텁 응답)"
