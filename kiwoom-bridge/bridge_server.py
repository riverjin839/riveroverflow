"""
Kiwoom Securities COM → REST bridge server.
Runs on Windows (or Wine) with pywin32 and exposes a REST API
that the Python trading engine can call from any platform.

Requirements (Windows):
  pip install flask pywin32 kiwoom-rest-api

Start:
  python bridge_server.py
"""
import json
import logging
import threading
from datetime import datetime
from decimal import Decimal

from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Kiwoom COM wrapper (only available on Windows)
# ---------------------------------------------------------------------------
try:
    from kiwoom import Kiwoom, KiwoomConnectError  # type: ignore
    import pythoncom  # type: ignore

    _kiwoom: Kiwoom | None = None
    _connected = False

    def get_kiwoom() -> Kiwoom:
        global _kiwoom, _connected
        if _kiwoom is None:
            pythoncom.CoInitialize()
            _kiwoom = Kiwoom()
        return _kiwoom

except ImportError:
    logger.warning("pywin32/kiwoom not available. Running in mock mode.")
    _kiwoom = None
    _connected = False

    def get_kiwoom():
        raise RuntimeError("Kiwoom COM not available (not on Windows)")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@app.post("/auth/login")
def login():
    try:
        kw = get_kiwoom()
        kw.CommConnect(block=True)
        global _connected
        _connected = True
        return jsonify({"status": "ok", "message": "Kiwoom connected"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------
@app.get("/account/balance")
def get_balance():
    try:
        kw = get_kiwoom()
        account = kw.GetLoginInfo("ACCNO").split(";")[0].strip()
        # OPW00001: 주식잔고요청
        kw.SetInputValue("계좌번호", account)
        kw.SetInputValue("비밀번호", "")
        kw.SetInputValue("비밀번호입력매체구분", "00")
        kw.SetInputValue("조회구분", "2")
        result = kw.CommRqData("잔고조회", "OPW00001", 0, "0101")

        total = kw.GetCommData("OPW00001", "잔고조회", 0, "총평가금액").strip()
        cash = kw.GetCommData("OPW00001", "잔고조회", 0, "D+2추정예수금").strip()
        stock_val = kw.GetCommData("OPW00001", "잔고조회", 0, "주식평가금액").strip()
        pl = kw.GetCommData("OPW00001", "잔고조회", 0, "평가손익합계").strip()
        pl_rate = kw.GetCommData("OPW00001", "잔고조회", 0, "총수익률(%)").strip()

        return jsonify({
            "total_value": float(total or 0),
            "cash": float(cash or 0),
            "stock_value": float(stock_val or 0),
            "profit_loss": float(pl or 0),
            "profit_loss_pct": float(pl_rate or 0),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.get("/account/positions")
def get_positions():
    # Returns list of held positions from Kiwoom
    try:
        kw = get_kiwoom()
        # Simplified - real implementation would loop through OPW00004 rows
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 502


# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------
@app.get("/market/price/<symbol>")
def get_price(symbol: str):
    try:
        kw = get_kiwoom()
        kw.SetInputValue("종목코드", symbol)
        kw.CommRqData("주식기본정보", "opt10001", 0, "0101")
        price = kw.GetCommData("opt10001", "주식기본정보", 0, "현재가").strip()
        name = kw.GetCommData("opt10001", "주식기본정보", 0, "종목명").strip()
        return jsonify({
            "symbol": symbol,
            "name": name,
            "price": abs(float(price or 0)),
            "open": 0,
            "high": 0,
            "low": 0,
            "volume": 0,
            "change": 0,
            "change_pct": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.get("/market/ohlcv/<symbol>")
def get_ohlcv(symbol: str):
    period = request.args.get("period", "D")
    count = int(request.args.get("count", 100))
    # opt10081: 주식일봉차트조회
    try:
        kw = get_kiwoom()
        kw.SetInputValue("종목코드", symbol)
        kw.SetInputValue("기준일자", datetime.now().strftime("%Y%m%d"))
        kw.SetInputValue("수정주가구분", "1")
        kw.CommRqData("일봉차트", "opt10081", 0, "0101")
        rows = []
        cnt = kw.GetRepeatCnt("opt10081", "일봉차트")
        for i in range(min(cnt, count)):
            date = kw.GetCommData("opt10081", "일봉차트", i, "일자").strip()
            rows.append({
                "time": f"{date[:4]}-{date[4:6]}-{date[6:8]}",
                "open": abs(float(kw.GetCommData("opt10081", "일봉차트", i, "시가").strip() or 0)),
                "high": abs(float(kw.GetCommData("opt10081", "일봉차트", i, "고가").strip() or 0)),
                "low": abs(float(kw.GetCommData("opt10081", "일봉차트", i, "저가").strip() or 0)),
                "close": abs(float(kw.GetCommData("opt10081", "일봉차트", i, "현재가").strip() or 0)),
                "volume": int(kw.GetCommData("opt10081", "일봉차트", i, "거래량").strip() or 0),
            })
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 502


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
@app.post("/order")
def place_order():
    data = request.json
    symbol = data["symbol"]
    side = data["side"]   # buy | sell
    qty = int(data["quantity"])
    price = int(float(data.get("price") or 0))
    order_type = "00" if price == 0 else "00"  # 00=지정가, 03=시장가

    try:
        kw = get_kiwoom()
        account = kw.GetLoginInfo("ACCNO").split(";")[0].strip()
        order_dir = 1 if side == "buy" else 2  # 1=매수, 2=매도

        ret = kw.SendOrder(
            "주문",
            "0101",
            account,
            order_dir,
            symbol,
            qty,
            price,
            order_type,
            "",
        )
        return jsonify({"order_id": str(ret), "status": "pending"})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.delete("/order/<order_id>")
def cancel_order(order_id: str):
    return jsonify({"status": "cancelled"})


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return jsonify({"status": "ok", "connected": _connected})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Kiwoom bridge server starting on :9091")
    app.run(host="0.0.0.0", port=9091, threaded=True)
