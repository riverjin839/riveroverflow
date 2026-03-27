"""
Market schedule management.
Automatically starts/stops the trading engine based on KRX trading hours.
KRX: 09:00 ~ 15:30 (Mon-Fri, KST)
"""
import logging
from datetime import time
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")
MARKET_OPEN = time(9, 0)
MARKET_CLOSE = time(15, 30)


class MarketScheduler:
    def __init__(self, engine, researcher=None):
        self._engine = engine
        self._researcher = researcher
        self._scheduler = AsyncIOScheduler(timezone=KST)
        self._setup_jobs()

    def _setup_jobs(self) -> None:
        # Start engine at 09:00 KST Mon-Fri
        self._scheduler.add_job(
            self._engine.start,
            CronTrigger(day_of_week="mon-fri", hour=9, minute=0, timezone=KST),
            id="market_open",
            name="Market Open - Start Engine",
        )
        # Stop engine at 15:35 KST Mon-Fri (5min after close)
        self._scheduler.add_job(
            self._engine.stop,
            CronTrigger(day_of_week="mon-fri", hour=15, minute=35, timezone=KST),
            id="market_close",
            name="Market Close - Stop Engine",
        )
        # Refresh OHLCV cache daily at 08:30 KST
        self._scheduler.add_job(
            self._engine._ohlcv_cache.clear,
            CronTrigger(day_of_week="mon-fri", hour=8, minute=30, timezone=KST),
            id="cache_clear",
            name="Clear OHLCV Cache",
        )
        # Auto Research: 장 종료 15분 후 (15:45 KST)
        if self._researcher is not None:
            self._scheduler.add_job(
                self._run_research,
                CronTrigger(day_of_week="mon-fri", hour=15, minute=45, timezone=KST),
                id="auto_research",
                name="Auto Research - 장마감 후 종목 분석",
            )

    async def _run_research(self) -> None:
        try:
            logger.info("Auto Research 스케줄 실행 시작")
            await self._researcher.run()
            logger.info("Auto Research 스케줄 완료")
        except Exception as e:
            logger.error("Auto Research 스케줄 실패: %s", e)

    def start(self) -> None:
        self._scheduler.start()
        logger.info("Market scheduler started (KRX: 09:00~15:30 KST)")

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)

    def is_market_open(self) -> bool:
        from datetime import datetime
        now = datetime.now(KST)
        if now.weekday() >= 5:  # Sat/Sun
            return False
        current_time = now.time().replace(tzinfo=None)
        return MARKET_OPEN <= current_time <= MARKET_CLOSE
