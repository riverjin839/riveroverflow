# RiverOverflow - 개발 Skills 가이드

Claude Code를 활용한 개발 작업 가이드입니다.
자주 쓰는 작업 패턴과 명령어를 정리합니다.

---

## 주요 개발 작업

### 새 전략 추가

```
새 이동평균 전략을 engine/app/strategies/rules/에 추가하고
strategies.py 라우터와 main.py strategy_classes에 등록해줘
전략명:볼린저밴드, 파라미터: period=20, std=2
```

### 전략 파라미터 변경

```
RSI 전략의 기본 oversold를 30에서 25로, overbought를 70에서 75로 변경해줘
```

### 새 API 엔드포인트 추가

```
engine/app/api/routes/에 watchlist 라우터를 추가해줘
GET /api/v1/watchlist, POST /api/v1/watchlist, DELETE /api/v1/watchlist/{symbol}
DB 모델도 함께 생성해줘
```

### Frontend 페이지 추가

```
frontend/src/views/에 Watchlist 페이지를 추가하고
AppShell 네비게이션에도 등록해줘
```

### 리스크 파라미터 변경

```
engine/app/engine/risk.py에서
max_position_ratio를 10%에서 15%로
stop_loss_pct를 3%에서 5%로 변경해줘
```

---

## 배포 관련

### 전체 재배포

```
make deploy 명령어 흐름을 설명해줘
```

### 특정 서비스만 재배포

```bash
# Gateway만
docker build -t localhost:5001/gateway:$(git rev-parse --short HEAD) ./gateway
docker push localhost:5001/gateway:$(git rev-parse --short HEAD)
kubectl rollout restart deployment/gateway -n riveroverflow

# Engine만
docker build -t localhost:5001/engine:$(git rev-parse --short HEAD) ./engine
docker push localhost:5001/engine:$(git rev-parse --short HEAD)
kubectl rollout restart deployment/engine -n riveroverflow
```

### 로그 확인

```bash
make logs              # 전체
make logs-gateway      # Gateway만
make logs-engine       # Engine만
kubectl logs -f -l app=engine -n riveroverflow --tail=100
```

---

## 디버깅

### Engine Swagger UI (로컬 개발 시)

```
http://localhost:9090/docs
```

### DB 직접 접속

```bash
kubectl exec -it statefulset/postgres -n riveroverflow -- psql -U trader -d riveroverflow
```

### Redis 모니터링

```bash
kubectl exec -it deployment/redis -n riveroverflow -- redis-cli monitor
```

### Pod 상태 확인

```bash
make status
kubectl describe pod -l app=engine -n riveroverflow
```

---

## 전략 플러그인 인터페이스

새 전략을 만들 때 반드시 구현해야 하는 인터페이스:

```python
from app.strategies.base import AbstractStrategy, MarketSnapshot, Signal, SignalType, StrategyConfig

class MyStrategy(AbstractStrategy):
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        # config.params에서 파라미터 로드
        self.my_param = config.params.get("my_param", 10)

    def evaluate(self, snapshot: MarketSnapshot) -> Signal:
        # snapshot.ohlcv: pandas DataFrame (columns: time, open, high, low, close, volume)
        # snapshot.current_price: float
        # snapshot.symbol: str

        # 반드시 Signal을 반환
        return Signal(
            strategy_id=self.strategy_id,
            symbol=snapshot.symbol,
            signal_type=SignalType.BUY,  # BUY | SELL | HOLD
            confidence=0.75,             # 0.0 ~ 1.0 (0.6 이상일 때 주문 실행)
            reason="조건 설명",
        )
```

---

## AbstractBroker 인터페이스

새 브로커를 추가할 때 구현해야 하는 메서드:

```python
from app.broker.base import AbstractBroker, Balance, Position, MarketPrice, OrderRequest, OrderResult

class MyBroker(AbstractBroker):
    @property
    def name(self) -> str: ...

    async def authenticate(self) -> None: ...
    async def get_balance(self) -> Balance: ...
    async def get_positions(self) -> list[Position]: ...
    async def get_market_price(self, symbol: str) -> MarketPrice: ...
    async def get_ohlcv(self, symbol, period, count) -> list[dict]: ...
    async def place_order(self, order: OrderRequest) -> OrderResult: ...
    async def cancel_order(self, order_id: str) -> bool: ...
    async def subscribe_realtime(self, symbols, callback) -> None: ...
    async def unsubscribe_realtime(self, symbols) -> None: ...
```

---

## 환경별 설정 차이

| 항목 | 개발 (`make dev`) | K8s (`make deploy`) |
|------|-------------------|----------------------|
| URL | `localhost:3000` | `localhost` |
| DB | docker-compose postgres | K8s StatefulSet |
| 빌드 | hot reload | production 빌드 |
| 이미지 | 로컬 빌드 | `localhost:5001` 레지스트리 |

---

## 자주 하는 질문

**Q: 전략이 실행되지 않아요**
- 엔진이 실행 중인지 확인: `GET /api/v1/engine/status`
- 전략이 `enabled=true`인지 확인
- KRX 운영 시간(09:00~15:30 평일)인지 확인
- 로그에서 에러 확인: `make logs-engine`

**Q: WebSocket 연결이 끊겨요**
- Gateway와 Redis가 실행 중인지 확인
- JWT 토큰이 만료되지 않았는지 확인 (기본 24시간)
- 프론트엔드는 3초 후 자동 재연결

**Q: 모의투자에서 실전투자로 전환하려면?**
- `.env`에서 `KIS_IS_VIRTUAL=false` 변경
- K8s 배포 시 `k8s/engine/deployment.yaml`의 `KIS_IS_VIRTUAL` 값 변경
- `make deploy`로 재배포
- **반드시 충분한 모의투자 검증 후 전환**

**Q: Kiwoom을 Mac에서 사용할 수 있나요?**
- Kiwoom OpenAPI+는 Windows COM 기반이라 Mac 직접 실행 불가
- Windows VM/머신에서 `kiwoom-bridge/bridge_server.py` 실행 후 `.env`의 `KIWOOM_BRIDGE_URL` 설정
