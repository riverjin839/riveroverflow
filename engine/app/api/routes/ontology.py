"""
온톨로지 API — 객체·관계·규칙 조회/수정.

온톨로지 = 도메인의 논리 구조를 DB에 표현한 것.
클라이언트(프론트엔드)는 이 API로 도메인 모델을 탐색하고 규칙을 조정한다.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import AsyncSessionLocal
from ...models.ontology import OntologyLink, OntologyObject, OntologyRule

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ontology", tags=["ontology"])


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


# ── 스키마 ────────────────────────────────────────────

class OntologyObjectOut(BaseModel):
    id: str
    type: str
    key: str
    properties: dict

    class Config:
        from_attributes = True


class OntologyLinkOut(BaseModel):
    id: str
    subject_key: str
    subject_type: str
    predicate: str
    object_key: str
    object_type: str
    properties: dict


class OntologyRuleOut(BaseModel):
    id: str
    name: str
    description: str
    trigger_type: str
    condition: dict
    action_type: str
    action_params: dict
    enabled: bool
    priority: int

    class Config:
        from_attributes = True


class OntologyRulePatch(BaseModel):
    enabled: Optional[bool] = None
    condition: Optional[dict] = None
    action_params: Optional[dict] = None
    priority: Optional[int] = None


# ── 엔드포인트 ─────────────────────────────────────────

@router.get("/objects", response_model=list[OntologyObjectOut])
async def list_objects(
    type: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """온톨로지 객체 목록. type 파라미터로 필터링 가능."""
    stmt = select(OntologyObject).order_by(OntologyObject.type, OntologyObject.key)
    if type:
        stmt = stmt.where(OntologyObject.type == type)
    rows = (await session.execute(stmt)).scalars().all()
    return [OntologyObjectOut(id=str(r.id), type=r.type, key=r.key, properties=r.properties or {}) for r in rows]


@router.get("/links", response_model=list[OntologyLinkOut])
async def list_links(
    predicate: Optional[str] = None,
    subject_type: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """온톨로지 관계(링크) 목록."""
    stmt = (
        select(OntologyLink)
        .options(
            selectinload(OntologyLink.subject),
            selectinload(OntologyLink.object),
        )
        .order_by(OntologyLink.created_at.desc())
        .limit(200)
    )
    if predicate:
        stmt = stmt.where(OntologyLink.predicate == predicate)
    rows = (await session.execute(stmt)).scalars().all()

    result = []
    for r in rows:
        if subject_type and r.subject.type != subject_type:
            continue
        result.append(OntologyLinkOut(
            id=str(r.id),
            subject_key=r.subject.key,
            subject_type=r.subject.type,
            predicate=r.predicate,
            object_key=r.object.key,
            object_type=r.object.type,
            properties=r.properties or {},
        ))
    return result


@router.get("/rules", response_model=list[OntologyRuleOut])
async def list_rules(session: AsyncSession = Depends(get_session)):
    """온톨로지 규칙 목록 (우선순위 내림차순)."""
    rows = (
        await session.execute(select(OntologyRule).order_by(OntologyRule.priority.desc()))
    ).scalars().all()
    return [
        OntologyRuleOut(
            id=str(r.id),
            name=r.name,
            description=r.description or "",
            trigger_type=r.trigger_type,
            condition=r.condition or {},
            action_type=r.action_type,
            action_params=r.action_params or {},
            enabled=r.enabled,
            priority=r.priority,
        )
        for r in rows
    ]


@router.patch("/rules/{rule_id}", response_model=OntologyRuleOut)
async def patch_rule(
    rule_id: UUID,
    body: OntologyRulePatch,
    session: AsyncSession = Depends(get_session),
):
    """규칙 수정 — enabled 토글, condition/action_params, priority 변경 가능."""
    rule = (await session.execute(select(OntologyRule).where(OntologyRule.id == rule_id))).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다.")

    if body.enabled is not None:
        rule.enabled = body.enabled
    if body.condition is not None:
        rule.condition = body.condition
    if body.action_params is not None:
        rule.action_params = body.action_params
    if body.priority is not None:
        rule.priority = body.priority

    await session.commit()
    await session.refresh(rule)
    return OntologyRuleOut(
        id=str(rule.id),
        name=rule.name,
        description=rule.description or "",
        trigger_type=rule.trigger_type,
        condition=rule.condition or {},
        action_type=rule.action_type,
        action_params=rule.action_params or {},
        enabled=rule.enabled,
        priority=rule.priority,
    )


@router.get("/summary")
async def get_summary(session: AsyncSession = Depends(get_session)):
    """온톨로지 전체 요약 (타입별 객체 수, 관계 수, 규칙 수)."""
    from sqlalchemy import func

    obj_counts_rows = (
        await session.execute(
            select(OntologyObject.type, func.count().label("cnt"))
            .group_by(OntologyObject.type)
        )
    ).all()
    obj_counts = {r.type: r.cnt for r in obj_counts_rows}

    link_count = (await session.execute(select(func.count()).select_from(OntologyLink))).scalar()
    rule_count = (await session.execute(select(func.count()).select_from(OntologyRule))).scalar()
    rule_enabled = (
        await session.execute(select(func.count()).select_from(OntologyRule).where(OntologyRule.enabled == True))
    ).scalar()

    return {
        "objects": obj_counts,
        "total_links": link_count,
        "total_rules": rule_count,
        "enabled_rules": rule_enabled,
    }
