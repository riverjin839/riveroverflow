# add-strategy

새로운 트레이딩 전략을 RiverOverflow에 추가하는 단계별 가이드입니다.

## 사용법

```
/add-strategy 전략명: <이름>, 파라미터: <key=value, ...>
```

예시:
```
/add-strategy 전략명: 볼린저밴드, 파라미터: period=20, std=2
/add-strategy 전략명: MACD크로스, 파라미터: fast=12, slow=26, signal=9
```

## 구현 절차

전략을 추가할 때 아래 4단계를 순서대로 수행합니다.

### 1단계 — 전략 파일 생성

`engine/app/strategies/rules/<strategy_name>.py` 생성:

```python
from app.strategies.base import AbstractStrategy, MarketSnapshot, Signal, SignalType, StrategyConfig

class <ClassName>Strategy(AbstractStrategy):
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        # config.params에서 파라미터 로드 (기본값 필수)
        self.param = config.params.get("param", DEFAULT)

    def evaluate(self, snapshot: MarketSnapshot) -> Signal:
        # snapshot.ohlcv: pandas DataFrame (columns: time, open, high, low, close, volume)
        # snapshot.current_price: float
        # snapshot.symbol: str

        # 지표 계산 후 조건 판단
        ...

        return Signal(
            strategy_id=self.strategy_id,
            symbol=snapshot.symbol,
            signal_type=SignalType.BUY,  # BUY | SELL | HOLD
            confidence=0.75,             # 0.0~1.0, 0.6 이상일 때 주문 실행
            reason="조건 설명",
        )
```

### 2단계 — main.py에 등록

`engine/app/main.py`의 `strategy_classes` 딕셔너리에 추가:

```python
from app.strategies.rules.<strategy_name> import <ClassName>Strategy

strategy_classes = {
    ...
    "<strategy_key>": <ClassName>Strategy,
}
```

### 3단계 — 라우터 확인

`engine/app/api/routes/strategies.py`가 `strategy_classes`를 동적으로 참조하는 구조이므로
별도 수정 없이 자동 반영됩니다. 확인만 합니다.

### 4단계 — 검증

```bash
# Engine Swagger UI에서 전략 목록 확인
# http://localhost:9090/docs → GET /api/v1/strategies

# 로그로 전략 로드 확인
make logs-engine
```

## 사용 가능한 기술 지표 (pandas-ta)

```python
import pandas_ta as ta

ta.sma(df['close'], length=20)       # 단순이동평균
ta.ema(df['close'], length=12)       # 지수이동평균
ta.rsi(df['close'], length=14)       # RSI
ta.macd(df['close'], 12, 26, 9)      # MACD (반환: DataFrame)
ta.bbands(df['close'], length=20, std=2)  # 볼린저밴드
```

## 주의사항

- `confidence < 0.6`이면 주문이 실행되지 않음
- OHLCV 데이터가 부족할 때(초기 봉 수 미만)는 `SignalType.HOLD` 반환
- 리스크 파라미터는 `engine/app/engine/risk.py`에서 별도 관리
