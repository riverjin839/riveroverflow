# write-tests

RiverOverflow 각 레이어에 맞는 테스트를 작성하는 가이드입니다.

## 사용법

```
/write-tests <대상>
```

예시:
```
/write-tests RSI 전략 evaluate() 메서드
/write-tests KIS 브로커 get_balance()
/write-tests Watchlist API 엔드포인트
/write-tests PortfolioStore Zustand 스토어
```

## Python 테스트 (pytest) — Engine

### 전략 유닛 테스트

`engine/tests/strategies/test_<strategy_name>.py`:

```python
import pytest
import pandas as pd
from app.strategies.rules.<strategy_name> import <ClassName>Strategy
from app.strategies.base import MarketSnapshot, SignalType, StrategyConfig

@pytest.fixture
def strategy():
    config = StrategyConfig(
        strategy_id="test-001",
        symbol="005930",
        params={"period": 14},  # 전략 파라미터
    )
    return <ClassName>Strategy(config)

@pytest.fixture
def ohlcv_df():
    """충분한 봉 수의 테스트 데이터 생성"""
    n = 50
    return pd.DataFrame({
        "time": pd.date_range("2024-01-01", periods=n, freq="1min"),
        "open":  [50000 + i * 10 for i in range(n)],
        "high":  [50500 + i * 10 for i in range(n)],
        "low":   [49500 + i * 10 for i in range(n)],
        "close": [50200 + i * 10 for i in range(n)],
        "volume":[1000] * n,
    })

def test_buy_signal(strategy, ohlcv_df):
    snapshot = MarketSnapshot(symbol="005930", ohlcv=ohlcv_df, current_price=50600.0)
    signal = strategy.evaluate(snapshot)
    assert signal.signal_type == SignalType.BUY
    assert signal.confidence >= 0.6

def test_insufficient_data_returns_hold(strategy):
    """데이터 부족 시 HOLD 반환 확인"""
    short_df = pd.DataFrame({
        "time": pd.date_range("2024-01-01", periods=3, freq="1min"),
        "open": [50000, 50100, 50200],
        "high": [50500, 50600, 50700],
        "low":  [49500, 49600, 49700],
        "close":[50200, 50300, 50400],
        "volume":[1000, 1000, 1000],
    })
    snapshot = MarketSnapshot(symbol="005930", ohlcv=short_df, current_price=50400.0)
    signal = strategy.evaluate(snapshot)
    assert signal.signal_type == SignalType.HOLD
```

### 브로커 유닛 테스트 (Mock)

`engine/tests/broker/test_<broker_name>.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from app.broker.<broker_name> import <BrokerName>Broker

@pytest.fixture
def broker():
    return <BrokerName>Broker(app_key="test_key", app_secret="test_secret", is_virtual=True)

@pytest.mark.asyncio
async def test_get_balance(broker):
    with patch.object(broker, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"cash": 1000000, "total": 1500000}
        balance = await broker.get_balance()
    assert balance.cash == 1000000

@pytest.mark.asyncio
async def test_authenticate_sets_token(broker):
    with patch.object(broker, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"access_token": "tok_abc123"}
        await broker.authenticate()
    assert broker._token == "tok_abc123"
```

### API 엔드포인트 테스트

`engine/tests/api/test_<route_name>.py`:

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_get_strategies():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/strategies")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### 테스트 실행

```bash
# engine/ 디렉토리에서
cd engine
pip install pytest pytest-asyncio httpx
pytest tests/ -v

# 특정 파일만
pytest tests/strategies/test_rsi.py -v
```

---

## TypeScript 테스트 (Vitest) — Frontend

### Zustand 스토어 테스트

`frontend/src/models/__tests__/<store_name>.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { use<StoreName>Store } from '../<store_name>'

describe('<StoreName>Store', () => {
  beforeEach(() => {
    use<StoreName>Store.setState(use<StoreName>Store.getInitialState())
  })

  it('초기 상태가 올바르게 설정된다', () => {
    const { result } = renderHook(() => use<StoreName>Store())
    expect(result.current.items).toEqual([])
  })

  it('아이템 추가가 동작한다', () => {
    const { result } = renderHook(() => use<StoreName>Store())
    act(() => { result.current.addItem({ id: '1', name: 'test' }) })
    expect(result.current.items).toHaveLength(1)
  })
})
```

### 컴포넌트 테스트

`frontend/src/views/__tests__/<Component>.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import <Component> from '../<Component>'

describe('<Component>', () => {
  it('렌더링이 정상 동작한다', () => {
    render(<<Component> />)
    expect(screen.getByText('예상 텍스트')).toBeInTheDocument()
  })

  it('버튼 클릭 시 콜백이 호출된다', async () => {
    const onAction = vi.fn()
    render(<<Component> onAction={onAction} />)
    await userEvent.click(screen.getByRole('button'))
    expect(onAction).toHaveBeenCalledOnce()
  })
})
```

### 테스트 실행

```bash
# frontend/ 디렉토리에서
cd frontend
npm install -D vitest @testing-library/react @testing-library/user-event jsdom
npx vitest run

# watch 모드
npx vitest
```

---

## 테스트 우선순위 (이 프로젝트)

1. **전략 `evaluate()` 메서드** — 매매 신호 정확성이 가장 중요
2. **리스크 관리 로직** (`engine/app/engine/risk.py`)
3. **브로커 Mock 테스트** — 실제 API 호출 없이 로직 검증
4. **API 엔드포인트** — 정상/오류 응답 코드 확인
5. **Zustand 스토어** — 상태 변환 로직
