import yfinance as yf
import pandas as pd
import numpy as np

SYMBOL = "GC=F"
PERIOD = "2y"
INTERVAL = "1d"

def main():
    print("DEVIL GOLD AI - HISTORICAL BACKTEST")
    print("=" * 40)

    data = yf.download(
        SYMBOL,
        period=PERIOD,
        interval=INTERVAL,
        auto_adjust=False,
        progress=False
    )

    if data.empty:
        raise RuntimeError("No historical data received.")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.dropna(subset=["Close"]).copy()

    if len(data) < 100:
        raise RuntimeError("Not enough historical data.")

    close = data["Close"]

    data["EMA20"] = close.ewm(
        span=20, adjust=False
    ).mean()

    data["EMA50"] = close.ewm(
        span=50, adjust=False
    ).mean()

    # اتجاه صاعد أو هابط وفق تقاطع المتوسطات
    data["Signal"] = np.where(
        data["EMA20"] > data["EMA50"], 1, -1
    )

    # استخدام إشارة اليوم السابق لتجنب النظر إلى المستقبل
    data["Position"] = data["Signal"].shift(1).fillna(0)

    data["Market_Return"] = close.pct_change().fillna(0)

    data["Strategy_Return"] = (
        data["Position"] * data["Market_Return"]
    )

    # لا تشمل النتائج الرسوم أو الانزلاق السعري
    data["Equity"] = (
        1 + data["Strategy_Return"]
    ).cumprod()

    data["Buy_Hold"] = (
        1 + data["Market_Return"]
    ).cumprod()

    running_peak = data["Equity"].cummax()

    drawdown = (
        data["Equity"] / running_peak
    ) - 1

    total_return = (data["Equity"].iloc[-1] - 1) * 100
    buy_hold_return = (data["Buy_Hold"].iloc[-1] - 1) * 100
    max_drawdown = drawdown.min() * 100

    trades = data["Position"].diff().abs().fillna(0)
    changes = int((trades > 0).sum())

    print(f"Symbol: {SYMBOL}")
    print(f"Period: {data.index[0]} to {data.index[-1]}")
    print(f"Data rows: {len(data)}")
    print(f"Strategy return: {total_return:.2f}%")
    print(f"Buy-and-hold return: {buy_hold_return:.2f}%")
    print(f"Maximum drawdown: {max_drawdown:.2f}%")
    print(f"Position changes: {changes}")
    print("=" * 40)
    print("Historical simulation only.")
    print("No trades executed.")
    print("Fees and slippage are not included.")

if __name__ == "__main__":
    main()
