# db-migration

Alembic을 사용한 PostgreSQL 스키마 마이그레이션 가이드입니다.

## 사용법

```
/db-migration <작업 설명>
```

예시:
```
/db-migration watchlist 테이블 추가 (symbol, user_id, created_at)
/db-migration trades 테이블에 strategy_version 컬럼 추가
/db-migration positions 테이블 인덱스 추가
```

## 마이그레이션 생성 절차

### 1단계 — SQLAlchemy 모델 작성/수정

`engine/app/models/<model_name>.py`:

```python
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.database import Base
import datetime

class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    user_id = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        {"schema": None},  # 필요 시 스키마 지정
    )
```

### 2단계 — Alembic 마이그레이션 자동 생성

```bash
cd engine
alembic revision --autogenerate -m "add_watchlist_table"
```

생성된 파일: `engine/alembic/versions/<hash>_add_watchlist_table.py`

### 3단계 — 마이그레이션 파일 검토

자동 생성된 `upgrade()` / `downgrade()` 함수를 반드시 확인:

```python
def upgrade() -> None:
    op.create_table(
        'watchlist',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('user_id', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('watchlist')
```

### 4단계 — 마이그레이션 실행

```bash
# 로컬 개발 (make dev 실행 중)
cd engine
alembic upgrade head

# K8s 배포 후
kubectl exec -it deployment/engine -n riveroverflow -- alembic upgrade head
```

## 자주 쓰는 Alembic 명령어

```bash
# 현재 마이그레이션 상태 확인
alembic current

# 마이그레이션 히스토리
alembic history --verbose

# 특정 버전으로 롤백
alembic downgrade -1        # 한 단계 롤백
alembic downgrade base      # 초기 상태로 롤백

# 마이그레이션 없이 DB 상태 동기화 (초기 설정 시)
alembic stamp head
```

## DB 직접 접속

```bash
# K8s
kubectl exec -it statefulset/postgres -n riveroverflow -- psql -U trader -d riveroverflow

# 로컬 개발 (Docker Compose)
docker compose exec postgres psql -U trader -d riveroverflow
```

## 자주 쓰는 SQL

```sql
-- 테이블 목록
\dt

-- 컬럼 확인
\d watchlist

-- 마이그레이션 버전 확인
SELECT * FROM alembic_version;

-- 트레이딩 성과 요약
SELECT
    strategy_id,
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    SUM(pnl) as total_pnl
FROM trades
GROUP BY strategy_id
ORDER BY total_pnl DESC;
```

## 주의사항

- `--autogenerate`는 모델 변경을 100% 감지하지 못할 수 있음 → 생성 후 반드시 검토
- 프로덕션 적용 전 `downgrade()` 함수도 정상 동작하는지 테스트
- 컬럼 삭제·이름 변경은 데이터 손실 위험 → 배포 전 백업 권장
