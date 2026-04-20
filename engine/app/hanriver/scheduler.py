"""Phase 5 — HANRIVER 자동 리포트 스케줄러.

APScheduler 기반. 설정이 활성일 때만 크론 등록.
"""
from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..core.config import settings
from ..core.database import AsyncSessionLocal
from ..models.hanriver import AiReport
from .ai import report_builder
from .notify import telegram

logger = logging.getLogger(__name__)


def install(app_scheduler: AsyncIOScheduler) -> None:
    """기존 MarketScheduler 에 HANRIVER 잡을 추가 설치."""
    if settings.hanriver_daily_report_enabled:
        app_scheduler.add_job(
            _generate_daily,
            CronTrigger(
                hour=settings.hanriver_daily_report_hour,
                minute=0,
                timezone="Asia/Seoul",
            ),
            id="hanriver_daily_report",
            replace_existing=True,
        )
        logger.info("HANRIVER daily report cron 등록: %02d:00 KST", settings.hanriver_daily_report_hour)

    if settings.hanriver_weekly_report_enabled:
        app_scheduler.add_job(
            _generate_weekly,
            CronTrigger(
                day_of_week=settings.hanriver_weekly_report_weekday,
                hour=17, minute=0,
                timezone="Asia/Seoul",
            ),
            id="hanriver_weekly_report",
            replace_existing=True,
        )
        logger.info("HANRIVER weekly report cron 등록")


async def _generate_daily() -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    async with AsyncSessionLocal() as session:
        md = await report_builder.build("daily", today, session=session)
        rep = AiReport(report_type="daily", subject=today, content_md=md)
        session.add(rep)
        await session.commit()
    await telegram.send_text(f"*[HANRIVER] Daily 리포트 발행*\n{today}")


async def _generate_weekly() -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    async with AsyncSessionLocal() as session:
        md = await report_builder.build("weekly", today, session=session)
        rep = AiReport(report_type="weekly", subject=today, content_md=md)
        session.add(rep)
        await session.commit()
    await telegram.send_text(f"*[HANRIVER] Weekly 리포트 발행*\n{today}")
