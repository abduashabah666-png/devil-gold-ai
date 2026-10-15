import numpy as np
import pandas as pd


def analyze_institutional(data):
    """
    Devil Gold AI - Institutional-style analysis.

    Analyzes trend, momentum, volatility, and volume anomalies.
    It does not identify actual banks or institutional orders.
    No trade execution.
    """

    if data is None or len(data) < 60:
        return {
            "status": "INSUFFICIENT_DATA",
            "direction": "NEUTRAL",
            "score": 0,
            "observations": ["Not enough market data."]
        }

    required = {"High", "Low", "Close", "Volume"}

    if not required.issubset(data.columns):
        return {
            "status": "INVALID_DATA",
            "direction": "NEUTRAL",
            "score": 0,
            "observations": ["Required columns are missing."]
        }

    df = data.copy()
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=list(required))

    if len(df) < 60:
        return {
            "status": "INSUFFICIENT_DATA",
            "direction": "NEUTRAL",
            "score": 0,
            "observations": ["Not enough valid candles."]
        }

    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    volume = df["Volume"].astype(float)

    ema20 = close.ewm(
        span=20, adjust=False
    ).mean()

    ema50 = close.ewm(
        span=50, adjust=False
    ).mean()

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

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    previous_close = close.shift(1)

    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    atr = true_range.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False
    ).mean()

    latest_close = float(close.iloc[-1])
    latest_ema20 = float(ema20.iloc[-1])
    latest_ema50 = float(ema50.iloc[-1])
    latest_rsi = float(rsi.iloc[-1])
    latest_atr = float(atr.iloc[-1])

    observations = []
    score = 0
    direction = "NEUTRAL"

    # Trend analysis
    if latest_ema20 > latest_ema50 and latest_close > latest_ema20:
        direction = "BULLISH"
        score += 25
        observations.append("Trend structure is bullish.")

    elif latest_ema20 < latest_ema50 and latest_close < latest_ema20:
        direction = "BEARISH"
        score += 25
        observations.append("Trend structure is bearish.")

    else:
        observations.append("Trend is mixed or sideways.")

    # Momentum confirmation
    if direction == "BULLISH" and 50 <= latest_rsi <= 68:
        score += 15
        observations.append("Momentum supports the upward trend.")

    elif direction == "BEARISH" and 32 <= latest_rsi <= 50:
        score += 15
        observations.append("Momentum supports the downward trend.")

    else:
        observations.append("Momentum confirmation is limited.")

    # Relative volume anomaly; not actual global market volume.
    average_volume = float(volume.iloc[-21:-1].mean())
    latest_volume = float(volume.iloc[-1])

    if average_volume > 0:
        relative_volume = latest_volume / average_volume
    else:
        relative_volume = None

    if relative_volume is not None and relative_volume >= 1.8:
        observations.append(
            "Unusually high reported volume; source-specific."
        )
    else:
        observations.append(
            "No strong relative-volume anomaly detected."
        )

    # ATR relative to its recent baseline.
    atr_baseline = float(atr.iloc[-21:-1].mean())

    if atr_baseline > 0:
        volatility_ratio = latest_atr / atr_baseline
    else:
        volatility_ratio = None

    if volatility_ratio is not None and volatility_ratio >= 1.5:
        observations.append(
            "Volatility is elevated relative to its recent baseline."
        )
    elif volatility_ratio is not None and volatility_ratio <= 0.7:
        observations.append(
            "Volatility is relatively compressed."
        )
    else:
        observations.append(
            "No major volatility anomaly detected."
        )

    return {
        "status": "OK",
        "direction": direction,
        "score": score,
        "price": latest_close,
        "ema20": latest_ema20,
        "ema50": latest_ema50,
        "rsi": latest_rsi,
        "atr": latest_atr,
        "relative_volume": relative_volume,
        "volatility_ratio": volatility_ratio,
        "observations": observations,
        "note": (
            "Rule-based analysis, not a probability of success. "
            "Reported volume is source-specific and does not "
            "represent all global gold trading."
        )
  }
