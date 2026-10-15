import os
import time
import logging
import requests
import numpy as np
import pandas as pd
import yfinance as yf

from datetime import datetime, timezone

from market_analysis import analyze_market
from institutional_engine import analyze_institutional

# ==========================================
# DEVIL GOLD AI
# Liquidity Engine + Institutional Analysis
# Analysis and alerts only - no trade execution
# ==========================================

BOT_NAME = "DEVIL GOLD AI"

SYMBOL = os.getenv("GOLD_SYMBOL", "GC=F")
INTERVAL = os.getenv("CANDLE_INTERVAL", "5m")
HISTORY_PERIOD = os.getenv("HISTORY_PERIOD", "5d")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

MIN_SCORE = 70

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ==========================================
# TELEGRAM
# ==========================================

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning(
            "Telegram credentials are missing. "
            "Report will only appear in application logs."
        )
        return False

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendMessage"
    )

    try:
        response = requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message
            },
            timeout=15
        )

        response.raise_for_status()

        result = response.json()

        if not result.get("ok"):
            logging.error("Telegram rejected the message.")
            return False

        return True

    except requests.RequestException as exc:
        logging.error("Telegram delivery failed: %s", exc)
        return False


# ==========================================
# MARKET DATA
# ==========================================

def get_market_data():
    try:
        ticker = yf.Ticker(SYMBOL)

        data = ticker.history(
            period=HISTORY_PERIOD,
            interval=INTERVAL,
            auto_adjust=False
        )

        if data is None or data.empty:
            logging.warning("No market data received.")
            return None

        required = ["Open", "High", "Low", "Close", "Volume"]

        if not all(column in data.columns for column in required):
            logging.warning("Required market columns are missing.")
            return None

        data = data[required].copy()

        data = data.replace(
            [np.inf, -np.inf],
            np.nan
        )

        data = data.dropna()

        if len(data) < 60:
            logging.warning("Not enough candles for analysis.")
            return None

        data = data[~data.index.duplicated(keep="last")]
        data = data.sort_index()

        return data

    except Exception:
        logging.exception("Market data retrieval failed.")
        return None


# ==========================================
# TECHNICAL INDICATORS
# ==========================================

def calculate_indicators(data):
    df = data.copy()

    df["EMA20"] = df["Close"].ewm(
        span=20,
        adjust=False
    ).mean()

    df["EMA50"] = df["Close"].ewm(
        span=50,
        adjust=False
    ).mean()

    delta = df["Close"].diff()

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

    df["RSI"] = 100 - (100 / (1 + rs))

    previous_close = df["Close"].shift(1)

    true_range = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - previous_close).abs(),
            (df["Low"] - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    df["ATR"] = true_range.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False
    ).mean()

    df["AverageVolume"] = df["Volume"].rolling(20).mean()

    return df.dropna()


# ==========================================
# ENGINE 1: LIQUIDITY ANALYSIS
# ==========================================

def analyze_liquidity(df):
    result = {
        "direction": "NEUTRAL",
        "score": 0,
        "observations": []
    }

    if len(df) < 25:
        result["observations"].append(
            "Insufficient candles for liquidity analysis."
        )
        return result

    # Exclude the latest candle from reference levels.
    reference = df.iloc[-21:-1]
    candle = df.iloc[-1]

    previous_high = float(reference["High"].max())
    previous_low = float(reference["Low"].min())

    close = float(candle["Close"])
    high = float(candle["High"])
    low = float(candle["Low"])

    # Potential sweep above a prior high, followed by a close below it.
    swept_high = high > previous_high and close < previous_high

    # Potential sweep below a prior low, followed by a close above it.
    swept_low = low < previous_low and close > previous_low

    if swept_low:
        result["direction"] = "BULLISH"
        result["score"] = 25
        result["observations"].append(
            "Potential downside liquidity sweep and recovery."
        )

    elif swept_high:
        result["direction"] = "BEARISH"
        result["score"] = 25
        result["observations"].append(
            "Potential upside liquidity sweep and rejection."
        )

    else:
        result["observations"].append(
            "No confirmed sweep pattern in the latest candle."
        )

    result["previous_high"] = previous_high
    result["previous_low"] = previous_low

    return result


# ==========================================
# ENGINE 2: INSTITUTIONAL-STYLE ANALYSIS
# ==========================================

def analyze_institutional(df):
    candle = df.iloc[-1]

    close = float(candle["Close"])
    ema20 = float(candle["EMA20"])
    ema50 = float(candle["EMA50"])
    rsi = float(candle["RSI"])
    atr = float(candle["ATR"])

    result = {
        "direction": "NEUTRAL",
        "score": 0,
        "observations": []
    }

    if ema20 > ema50 and close > ema20:
        result["direction"] = "BULLISH"
        result["score"] += 25

        result["observations"].append(
            "Price and moving averages indicate an upward trend."
        )

    elif ema20 < ema50 and close < ema20:
        result["direction"] = "BEARISH"
        result["score"] += 25

        result["observations"].append(
            "Price and moving averages indicate a downward trend."
        )

    else:
        result["observations"].append(
            "Trend conditions are mixed."
        )

    if result["direction"] == "BULLISH" and 50 <= rsi <= 68:
        result["score"] += 15

        result["observations"].append(
            "Momentum supports the upward trend."
        )

    elif result["direction"] == "BEARISH" and 32 <= rsi <= 50:
        result["score"] += 15

        result["observations"].append(
            "Momentum supports the downward trend."
        )

    else:
        result["observations"].append(
            "Momentum confirmation is insufficient."
        )

    result["rsi"] = rsi
    result["atr"] = atr
    result["ema20"] = ema20
    result["ema50"] = ema50

    return result


# ==========================================
# COMBINED ANALYSIS
# ==========================================

def build_report(df):
    
def build_report(df):
    liquidity = analyze_market(df)
    institutional = analyze_institutional(df)

    if liquidity["status"] != "OK":
        return "DEVIL GOLD AI: Insufficient data for liquidity analysis."

    if institutional["status"] != "OK":
        return "DEVIL GOLD AI: Insufficient data for institutional analysis."

    price = float(df["Close"].iloc[-1])

    liquidity_signal = liquidity["assessment"]
    institutional_direction = institutional["direction"]

    agreement = (
        (liquidity_signal == "BULLISH_CONFLUENCE"
         and institutional_direction == "BULLISH")
        or
        (liquidity_signal == "BEARISH_CONFLUENCE"
         and institutional_direction == "BEARISH")
    )

    if agreement:
        status = "BOTH ENGINES AGREE"
    else:
        status = "WAIT - NO FULL AGREEMENT"

    observations = "\n".join(
        "- " + item
        for item in institutional["observations"]
    )

    return f"""
🐋 DEVIL GOLD AI
━━━━━━━━━━━━━━━━━━
Symbol: {SYMBOL}
Latest candle close: {price:.3f}

🐋 LIQUIDITY ENGINE
Trend: {liquidity["trend"]}
Pattern: {liquidity["liquidity"]}
Assessment: {liquidity_signal}

🏦 INSTITUTIONAL-STYLE ENGINE
Direction: {institutional_direction}
Heuristic score: {institutional["score"]}/40
RSI: {institutional["rsi"]:.2f}
ATR: {institutional["atr"]:.3f}

🧠 COMBINED RESULT
{status}

Observations:
{observations}

⚠️ Analysis only. No trade execution.
Scores are not probabilities of success.
Yahoo data may differ from broker quotes.
━━━━━━━━━━━━━━━━━━
""".strip()

# ==========================================
# MAIN LOOP
# ==========================================

def main():
    logging.info("%s starting.", BOT_NAME)
    logging.info("Symbol: %s", SYMBOL)
    logging.info("Interval: %s", INTERVAL)

    last_report_key = None

    while True:
        try:
            data = get_market_data()

            if data is None:
                time.sleep(CHECK_INTERVAL)
                continue

            data = calculate_indicators(data)

            if data.empty:
                logging.warning("Indicator data is empty.")
                time.sleep(CHECK_INTERVAL)
                continue

            report = build_report(data)

            # Avoid repeatedly sending the same candle report.
            report_key = str(data.index[-1])

            if report_key != last_report_key:
                logging.info("\n%s", report)
                send_telegram(report)
                last_report_key = report_key
            else:
                logging.info("No new candle; waiting.")

        except Exception:
            logging.exception("Unexpected analysis error.")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
