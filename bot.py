import yfinance as yf
import pandas as pd
import time
from datetime import datetime, timezone

SYMBOL = "GC=F"
INTERVAL = "5m"
PERIOD = "5d"


def get_market_data():
    data = yf.download(
        SYMBOL,
        period=PERIOD,
        interval=INTERVAL,
        progress=False,
        auto_adjust=False
    )

    if data.empty:
        raise RuntimeError("No market data received.")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.dropna(subset=["Close"]).copy()

    if len(data) < 50:
        raise RuntimeError("Not enough candles for analysis.")

    return data


def analyze_gold(data):
    close = data["Close"]

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))

    price = float(close.iloc[-1])
    fast = float(ema20.iloc[-1])
    slow = float(ema50.iloc[-1])
    current_rsi = float(rsi.iloc[-1])

    if fast > slow and price > fast:
        trend = "BULLISH"
    elif fast < slow and price < fast:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"

    if current_rsi >= 70:
        momentum = "HIGH RSI"
    elif current_rsi <= 30:
        momentum = "LOW RSI"
    else:
        momentum = "RSI IN NORMAL RANGE"

    return {
        "price": price,
        "ema20": fast,
        "ema50": slow,
        "rsi": current_rsi,
        "trend": trend,
        "momentum": momentum,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def build_report(result):
    return f"""
🐋 DEVIL GOLD AI
========================
Symbol: {SYMBOL}
Latest candle close: {result['price']:.2f}

Trend: {result['trend']}
RSI: {result['rsi']:.2f}
Momentum: {result['momentum']}

EMA20: {result['ema20']:.2f}
EMA50: {result['ema50']:.2f}

Analysis time: {result['timestamp']}

IMPORTANT:
Analysis only; no trades are executed.
This is not a verified trading signal.
Yahoo Finance data may differ from broker prices.
========================
""".strip()


def main():
    print("Starting DEVIL GOLD AI...")
    print("Mode: analysis only; no live trading")

    try:
        data = get_market_data()
        result = analyze_gold(data)
        print(build_report(result))

    except Exception as error:
        print("Analysis failed:", error)


if __name__ == "__main__":
    main()
