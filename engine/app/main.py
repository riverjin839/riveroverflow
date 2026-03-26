import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.database import engine, Base
from .broker.kis import KISBroker
from .engine.runner import TradingEngine
from .engine.scheduler import MarketScheduler
from .api.routes import trades, strategies, portfolio, screener

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Engine service starting up...")

    # Create DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize broker and trading engine
    broker = KISBroker()
    app.state.broker = broker

    engine_runner = TradingEngine(broker=broker)
    app.state.trading_engine = engine_runner

    # Start market scheduler (auto start/stop based on KRX hours)
    scheduler = MarketScheduler(engine_runner)
    scheduler.start()
    app.state.scheduler = scheduler

    # If market is currently open, start immediately
    if scheduler.is_market_open():
        logger.info("Market is currently open, starting engine...")
        # Load strategies from DB and add to engine
        await _load_strategies_from_db(app, engine_runner)
        await engine_runner.start()

    logger.info("Engine service ready on port %d", settings.port)
    yield

    # Shutdown
    logger.info("Engine service shutting down...")
    if app.state.trading_engine._running:
        await app.state.trading_engine.stop()
    app.state.scheduler.stop()
    await engine.dispose()


async def _load_strategies_from_db(app, engine_runner: TradingEngine):
    """Load enabled strategies from DB and register with engine."""
    import json
    from sqlalchemy import select
    from .core.database import AsyncSessionLocal
    from .models.trade import StrategyConfig as StrategyConfigModel
    from .strategies.base import StrategyConfig
    from .strategies.rules.ma_cross import MACrossStrategy
    from .strategies.rules.rsi import RSIStrategy
    from .strategies.rules.macd import MACDStrategy

    strategy_classes = {
        "ma_cross": MACrossStrategy,
        "rsi": RSIStrategy,
        "macd": MACDStrategy,
    }

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StrategyConfigModel).where(StrategyConfigModel.enabled == True)
        )
        configs = result.scalars().all()
        for c in configs:
            cls = strategy_classes.get(c.strategy_type)
            if cls:
                cfg = StrategyConfig(
                    strategy_id=c.id,
                    strategy_type=c.strategy_type,
                    symbols=json.loads(c.symbols),
                    params=json.loads(c.params),
                    enabled=True,
                    broker=c.broker,
                )
                engine_runner.add_strategy(cls(cfg))
    logger.info("Loaded %d enabled strategies from DB", len(list(engine_runner._strategies.keys())))


app = FastAPI(
    title="RiverOverflow Trading Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "engine_running": getattr(
            getattr(app.state, "trading_engine", None), "_running", False
        ),
        "market_open": getattr(
            getattr(app.state, "scheduler", None), "is_market_open", lambda: None
        )(),
    }

# Engine control
@app.post("/api/v1/engine/start")
async def start_engine():
    engine_runner: TradingEngine = app.state.trading_engine
    await _load_strategies_from_db(app, engine_runner)
    await engine_runner.start()
    return {"status": "started"}

@app.post("/api/v1/engine/stop")
async def stop_engine():
    await app.state.trading_engine.stop()
    return {"status": "stopped"}

@app.get("/api/v1/engine/status")
async def engine_status():
    runner: TradingEngine = app.state.trading_engine
    return {
        "running": runner._running,
        "strategies": list(runner._strategies.keys()),
        "market_open": app.state.scheduler.is_market_open(),
    }

# Include routers
app.include_router(trades.router, prefix="/api/v1")
app.include_router(strategies.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(screener.router, prefix="/api/v1")
