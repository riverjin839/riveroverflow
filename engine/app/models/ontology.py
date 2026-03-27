"""
온톨로지 도메인 모델.

도메인의 논리 구조(객체·관계·규칙)를 DB에 표현한다.
  ontology_objects  — 도메인 인스턴스 (Stock, Strategy, Trade, Research …)
  ontology_links    — 객체 간 관계 (monitors, generated, executed, researched)
  ontology_rules    — 실행 가능한 비즈니스 규칙 (하드코딩 → DB)
  research_results  — AutoResearcher 분석 결과
"""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float,
    ForeignKey, Index, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..core.database import Base


# ──────────────────────────────────────────────
# 온톨로지 객체
# ──────────────────────────────────────────────
class OntologyObject(Base):
    __tablename__ = "ontology_objects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(50), nullable=False)          # stock | strategy | trade | research
    key = Column(String(200), nullable=False, unique=True)  # natural key
    properties = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relations
    subject_links = relationship(
        "OntologyLink", foreign_keys="OntologyLink.subject_id", back_populates="subject", cascade="all, delete-orphan"
    )
    object_links = relationship(
        "OntologyLink", foreign_keys="OntologyLink.object_id", back_populates="object", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_onto_obj_type", "type"),
    )


# ──────────────────────────────────────────────
# 온톨로지 관계 (링크)
# ──────────────────────────────────────────────
class OntologyLink(Base):
    __tablename__ = "ontology_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("ontology_objects.id", ondelete="CASCADE"), nullable=False)
    predicate = Column(String(100), nullable=False)    # monitors | generated | executed | researched
    object_id = Column(UUID(as_uuid=True), ForeignKey("ontology_objects.id", ondelete="CASCADE"), nullable=False)
    properties = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    subject = relationship("OntologyObject", foreign_keys=[subject_id], back_populates="subject_links")
    object = relationship("OntologyObject", foreign_keys=[object_id], back_populates="object_links")

    __table_args__ = (
        Index("ix_onto_link_subject", "subject_id"),
        Index("ix_onto_link_predicate", "predicate"),
    )


# ──────────────────────────────────────────────
# 온톨로지 규칙 (비즈니스 로직 DB화)
# ──────────────────────────────────────────────
class OntologyRule(Base):
    __tablename__ = "ontology_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, default="")
    trigger_type = Column(String(50), nullable=False)  # signal | schedule | manual
    condition = Column(JSONB, default=dict)
    action_type = Column(String(100), nullable=False)  # place_order | research | notify | block
    action_params = Column(JSONB, default=dict)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────
# 오토리서치 결과
# ──────────────────────────────────────────────
class ResearchResult(Base):
    __tablename__ = "research_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False)
    name = Column(String(100), default="")
    research_date = Column(Date, nullable=False)
    period_days = Column(Integer, default=60)

    # 지표값
    rsi = Column(Float, nullable=True)
    ma5 = Column(Float, nullable=True)
    ma20 = Column(Float, nullable=True)
    ma60 = Column(Float, nullable=True)
    macd_val = Column(Float, nullable=True)
    macd_signal_val = Column(Float, nullable=True)
    high_period = Column(Float, nullable=True)   # 기간 내 최고가
    high_pct = Column(Float, nullable=True)      # 현재가/기간최고가 × 100
    volume_ratio = Column(Float, nullable=True)  # 현재거래량 / 20일평균거래량

    # 종합
    signals = Column(JSONB, default=dict)        # {"rsi": "oversold", "ma": "golden_cross", …}
    composite_score = Column(Float, default=0.0) # 0~100
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_research_symbol_date", "symbol", "research_date"),
        Index("ix_research_date", "research_date"),
    )


# ──────────────────────────────────────────────
# 시드 데이터: 기존 하드코딩 규칙 → ontology_rules
# ──────────────────────────────────────────────
SEED_RULES = [
    {
        "name": "min_confidence_filter",
        "description": "신뢰도 0.6 미만 시그널 차단",
        "trigger_type": "signal",
        "condition": {"confidence": {"lt": 0.6}},
        "action_type": "block",
        "action_params": {},
        "priority": 100,
    },
    {
        "name": "position_size_limit",
        "description": "종목당 포트폴리오 대비 최대 비중 (기본 10%)",
        "trigger_type": "signal",
        "condition": {"side": "buy"},
        "action_type": "check_position_ratio",
        "action_params": {"max_ratio": 0.10},
        "priority": 90,
    },
    {
        "name": "trade_size_pct",
        "description": "1회 주문 포트폴리오 비율 (기본 5%)",
        "trigger_type": "signal",
        "condition": {"side": "buy"},
        "action_type": "set_order_size",
        "action_params": {"portfolio_pct": 0.05},
        "priority": 80,
    },
    {
        "name": "stop_loss_3pct",
        "description": "손실 -3% 도달 시 자동 손절",
        "trigger_type": "schedule",
        "condition": {"profit_loss_pct": {"lte": -3.0}},
        "action_type": "place_order",
        "action_params": {"side": "sell", "order_type": "market"},
        "priority": 95,
    },
    {
        "name": "auto_research_daily",
        "description": "장 종료 후 KOSPI 주요 종목 자동 리서치 (15:45 KST)",
        "trigger_type": "schedule",
        "condition": {"cron": "45 15 * * mon-fri"},
        "action_type": "research",
        "action_params": {"period_days": 60},
        "priority": 10,
    },
]


async def seed_ontology(session) -> None:
    """최초 1회 기본 규칙을 DB에 등록한다. 이미 존재하면 건너뛴다."""
    from sqlalchemy import select

    for rule_data in SEED_RULES:
        exists = await session.execute(
            select(OntologyRule).where(OntologyRule.name == rule_data["name"])
        )
        if exists.scalar_one_or_none() is None:
            session.add(OntologyRule(**rule_data))

    await session.commit()
