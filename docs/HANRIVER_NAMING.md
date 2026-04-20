# HANRIVER 네이밍 & 네임스페이스 확정

> 상위 문서: [HANRIVER_PLAN.md](./HANRIVER_PLAN.md) §11

## 결정

| 항목 | 값 |
|------|-----|
| 프로젝트명 | **HANRIVER** |
| 코드 네임스페이스 | `hanriver` (소문자 스네이크) |
| K8s 네임스페이스 | 기존 `riveroverflow` 공용 (ARCHITECTURE_DECISION §5 참조) |
| 레포 전략 | 현재 `riveroverflow` 모노레포 내부 하위 모듈로 시작 |
| 도메인 네이밍 | `hanriver.local` (개발) / 홈랩 서브도메인 TBD |
| Docker 이미지 prefix | `hanriver-` (예: `hanriver-dashboard`, `hanriver-ingestion`) |

## 이유

- **네임스페이스 일관성**: RIVERFLOW(매매 일지) ↔ HANRIVER(자비스) 쌍을 이루는
  강의 메타포. 한강은 여러 지류(RIVERFLOW 포함)가 모이는 개념으로 통합
  대시보드 포지셔닝과 맞는다.
- **모노레포 시작**: Phase 1-2 단계에서는 기존 `engine`/`gateway`/`frontend`와
  모델·인프라를 공유하는 편이 유리 (§ARCHITECTURE_DECISION 참조). 이후
  Phase 3 이후 독립성이 필요해지면 `hanriver/` 서브디렉터리를 별도 레포로
  분리할 수 있도록 경계를 명확히 유지한다.

## 디렉터리 규칙

새로 추가되는 HANRIVER 관련 자산은 원칙적으로 다음 위치에 둔다:

```
hanriver/
├── dashboard/         # Next.js 또는 기존 frontend 내 /views/hanriver/
├── ingestion/         # Airflow DAG + 크롤러
├── analysis/          # VSA, 수급 지표 엔진
├── signals/           # AI 시그널 생성 (Claude API + RAG)
└── replay/            # 복기 타임머신
```

단, 기존 `engine/app/strategies/` 및 `frontend/src/views/`를 확장하는 편이
더 자연스러운 경우에는 기존 경로를 재사용한다(예: VSA 전략을
`engine/app/strategies/rules/vsa.py`).

## 확정되지 않은 항목

- 공개 도메인 (개인 사용 전용이라 외부 노출 필요 없을 수 있음)
- 로고/브랜딩 자산 (MVP에서는 생략)
