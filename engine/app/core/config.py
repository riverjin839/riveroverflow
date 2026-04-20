from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    environment: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    port: int = 9090

    # Database
    database_url: str = "postgresql+asyncpg://trader:password@postgres:5432/riveroverflow"

    # Redis
    redis_url: str = "redis://redis:6379"

    # JWT (for internal service verification)
    jwt_secret: str = "dev-secret"

    # 한국투자증권 (KIS)
    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_account_no: str = ""
    kis_is_virtual: bool = True  # True=모의투자, False=실전

    # Kiwoom bridge
    kiwoom_bridge_url: str = "http://kiwoom-bridge:9091"

    # Trading engine
    engine_poll_interval_sec: float = 1.0  # 시세 조회 주기 (초)
    max_position_ratio: float = 0.1        # 종목당 최대 포트폴리오 비율 (10%)
    default_stop_loss_pct: float = 0.03    # 기본 손절 비율 (3%)

    # HANRIVER 외부 연동 (비어 있으면 해당 기능 비활성화)
    dart_api_key: str = ""                 # DART OpenAPI
    anthropic_api_key: str = ""            # Claude
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # HANRIVER 자동 리포트
    hanriver_daily_report_enabled: bool = False
    hanriver_weekly_report_enabled: bool = False
    hanriver_daily_report_hour: int = 16   # 장 마감 후 (KST)
    hanriver_weekly_report_weekday: int = 5  # 금요일
    # 일일 최대 손실 한도 (Phase 5 리스크 가드)
    hanriver_daily_loss_limit_pct: float = 0.05

    @field_validator("database_url")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError("Only PostgreSQL is supported")
        return v


# Singleton
settings = Settings()
