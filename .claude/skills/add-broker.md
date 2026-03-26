# add-broker

새로운 브로커를 RiverOverflow에 통합하는 단계별 가이드입니다.

## 사용법

```
/add-broker 브로커명: <이름>
```

예시:
```
/add-broker 브로커명: 키움증권
/add-broker 브로커명: 나스닥브릿지
```

## AbstractBroker 인터페이스 (전체 구현 필수)

`engine/app/broker/<broker_name>.py` 생성:

```python
from app.broker.base import (
    AbstractBroker, Balance, Position,
    MarketPrice, OrderRequest, OrderResult
)

class <BrokerName>Broker(AbstractBroker):

    @property
    def name(self) -> str:
        return "<broker_display_name>"

    async def authenticate(self) -> None:
        """토큰 발급 / 세션 초기화"""
        ...

    async def get_balance(self) -> Balance:
        """계좌 잔고 조회 (현금 + 총평가금액)"""
        ...

    async def get_positions(self) -> list[Position]:
        """보유 종목 목록 조회"""
        ...

    async def get_market_price(self, symbol: str) -> MarketPrice:
        """현재가 조회"""
        ...

    async def get_ohlcv(self, symbol: str, period: str, count: int) -> list[dict]:
        """OHLCV 캔들 데이터 조회
        period: '1m' | '5m' | '1d' 등
        반환: [{'time': ..., 'open': ..., 'high': ..., 'low': ..., 'close': ..., 'volume': ...}]
        """
        ...

    async def place_order(self, order: OrderRequest) -> OrderResult:
        """주문 실행 (시장가/지정가)"""
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        ...

    async def subscribe_realtime(self, symbols: list[str], callback) -> None:
        """실시간 시세 WebSocket 구독"""
        ...

    async def unsubscribe_realtime(self, symbols: list[str]) -> None:
        """실시간 시세 구독 해제"""
        ...
```

## 등록 절차

### 1단계 — 브로커 파일 생성

위 인터페이스를 구현하여 `engine/app/broker/<broker_name>.py` 작성.

### 2단계 — 환경변수 추가

`.env.example`과 `k8s/engine/deployment.yaml`에 필요한 인증 정보 키 추가:

```bash
# .env.example 예시
NEW_BROKER_APP_KEY=your_app_key_here
NEW_BROKER_APP_SECRET=your_app_secret_here
```

### 3단계 — main.py에 브로커 등록

`engine/app/main.py`에서 브로커 초기화 로직에 추가:

```python
from app.broker.<broker_name> import <BrokerName>Broker

# 브로커 선택 로직에 추가
if settings.BROKER_TYPE == "<broker_key>":
    broker = <BrokerName>Broker(...)
```

### 4단계 — 모의투자 우선 검증

```bash
# .env에서 가상 모드 설정 후 테스트
KIS_IS_VIRTUAL=true

make dev
# Swagger UI: http://localhost:9090/docs
# GET /api/v1/broker/balance 등으로 응답 확인
```

## 참고 — 기존 브로커 구현체

| 브로커 | 파일 | 특이사항 |
|-------|------|---------|
| 한국투자증권(KIS) | `engine/app/broker/kis.py` | REST + WebSocket, 모의/실전 URL 분리 |
| 키움증권 | `engine/app/broker/kiwoom.py` | Windows COM → REST 브릿지 방식 |

## 주의사항

- **반드시 모의투자로 충분히 검증 후 실전 전환**
- `authenticate()`는 엔진 시작 시 자동 호출됨
- 실시간 시세 구독은 `subscribe_realtime()` → 콜백으로 Redis pub/sub에 발행
