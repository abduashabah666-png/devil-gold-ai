import pandas as pd
import numpy as np


def analyze_market(data):
    """
    Devil Gold AI
    Market structure and potential liquidity analysis.
    Analysis only: no trading orders.
    """

    if data is None or len(data) < 60:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": "Not enough candles for reliable analysis."
        }

    df = data.copy()

    required = {"High", "Low", "Close"}

    if not required.issubset(df.columns):
        return {
            "status": "INVALID_DATA",
            "message": "Required OHLC columns are missing."
        }

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["High", "Low", "Close"])

    if len(df) < 60:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": "Not enough valid candles."
        }

    df["EMA20"] = df["Close"].ewm(
        span=20, adjust=False
    ).mean()

    df["EMA50"] = df["Close"].ewm(
        span=50, adjust=False
    ).mean()

    previous = df.iloc[-21:-1]
    latest = df.iloc[-1]

    close = float(latest["Close"])
    high = float(latest["High"])
    low = float(latest["Low"])

    ema20 = float(latest["EMA20"])
    ema50 = float(latest["EMA50"])

    previous_high = float(previous["High"].max())
    previous_low = float(previous["Low"].min())

    # Potential liquidity sweep patterns.
    sweep_high = (
        high > previous_high
        and close < previous_high
    )

    sweep_low = (
        low < previous_low
        and close > previous_low
    )

    if ema20 > ema50 and close > ema20:
        trend = "BULLISH"

    elif ema20 < ema50 and close < ema20:
        trend = "BEARISH"

    else:
        trend = "NEUTRAL"

    if sweep_low:
        liquidity = "POTENTIAL_LOW_SWEEP"

    elif sweep_high:
        liquidity = "POTENTIAL_HIGH_SWEEP"

    else:
        liquidity = "NO_CLEAR_SWEEP"

    if trend == "BULLISH" and sweep_low:
        assessment = "BULLISH_CONFLUENCE"

    elif trend == "BEARISH" and sweep_high:
        assessment = "BEARISH_CONFLUENCE"

    else:
        assessment = "WAIT_FOR_MORE_EVIDENCE"

    return {
        "status": "OK",
        "price": close,
        "trend": trend,
        "liquidity": liquidity,
        "assessment": assessment,
        "previous_high": previous_high,
        "previous_low": previous_low,
        "ema20": ema20,
        "ema50": ema50,
        "note": (
            "Heuristic price-pattern analysis only. "
            "It does not identify actual institutional orders "
            "or predict guaranteed market direction."
        )
    }
