import pandas as pd
import numpy as np


def calculate_rsi(series, period=14):
    """Calculates standard Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))


def calculate_momentum(series, period=20):
    """Calculates standard Momentum Oscillator indicator."""
    return series.diff(period)


def scan_knoxville_divergence(df, lookback_bars=200, rsi_period=14, mom_period=20):
    """
    Algorithmic execution of Rob Booker's Knoxville Divergence (RB_KnoxDiv).
    Evaluates lookback windows to safely trigger non-repainting buy/sell anchors.
    """
    if len(df) < lookback_bars:
        return {"trigger": False, "action": None, "metrics": {}}

    # 1. Compute Base Core Infrastructure Indicators
    close_series = df["Close"].astype(float)
    high_series = df["High"].astype(float)
    low_series = df["Low"].astype(float)

    rsi = calculate_rsi(close_series, rsi_period)
    momentum = calculate_momentum(close_series, mom_period)

    # 2. Extract Current Data Points (Most recent closed candle)
    current_high = high_series.iloc[-1]
    current_low = low_series.iloc[-1]
    current_close = close_series.iloc[-1]
    current_rsi = rsi.iloc[-1]
    current_mom = momentum.iloc[-1]

    # Lookback configurations mapping the specific indicator framework (TV-identical lookback = 30-bar pivot)
    pivot_window = 30

    # 3. Geometric Extreme Verifications
    is_highest_high = current_high >= high_series.iloc[-pivot_window:].max()
    is_lowest_low = current_low <= low_series.iloc[-pivot_window:].min()

    buy_trigger = False
    sell_trigger = False
    historical_anchor_price = current_close

    # 4. Bullish Divergence Analysis (BUY Entry Layer)
    if is_lowest_low:
        # Scan backward for the divergence window setup
        for i in range(5, pivot_window):
            past_mom = momentum.iloc[-i]
            past_low = low_series.iloc[-i]
            past_rsi = rsi.iloc[-i]

            # Condition: Price made a lower low, but momentum is rising and RSI was oversold
            if current_mom > past_mom and current_low < past_low and past_rsi <= 30:
                buy_trigger = True
                historical_anchor_price = past_low
                break

    # 5. Bearish Divergence Analysis (SELL Exit Layer)
    if is_highest_high:
        # Scan backward for the divergence window setup
        for i in range(5, pivot_window):
            past_mom = momentum.iloc[-i]
            past_high = high_series.iloc[-i]
            past_rsi = rsi.iloc[-i]

            # Condition: Price made a higher high, but momentum is falling and RSI was overbought
            if current_mom < past_mom and current_high > past_high and past_rsi >= 70:
                sell_trigger = True
                historical_anchor_price = past_high
                break

    # 6. Format Structural Responses
    if buy_trigger:
        return {
            "trigger": True,
            "action": "BUY",
            "title": "Rob Booker Knoxville Divergence [BULLISH BREAKOUT]",
            "message": (
                f"📈 **Indicator:** `RB_KnoxDiv` (Bars Back: {lookback_bars})\n"
                f"🔹 **Live Price:** ₹{current_close:,.2f}\n"
                f"🔹 **Downtrend Anchor Entry Point:** ₹{historical_anchor_price:,.2f}\n"
                f"🔹 **RSI:** {current_rsi:.2f} | **Momentum:** {current_mom:.2f}\n\n"
                f"📝 *Execution Note:* Bullish divergence detected at endpoints. Place BUY order tomorrow morning."
            ),
            "metrics": {
                "live_price": current_close,
                "low_target": current_close * 0.95,
                "high_target": current_close * 1.15,
                "historic_move": ((current_close - historical_anchor_price) / historical_anchor_price) * 100,
                "start_date": df.index[-1].strftime("%Y-%m-%d"),
                "end_date": df.index[-1].strftime("%Y-%m-%d")
            }
        }

    if sell_trigger:
        return {
            "trigger": True,
            "action": "SELL",
            "title": "Rob Booker Knoxville Divergence [BEARISH EXHAUSTION]",
            "message": (
                f"📉 **Indicator:** `RB_KnoxDiv` (Bars Back: {lookback_bars})\n"
                f"🔹 **Live Price:** ₹{current_close:,.2f}\n"
                f"🔹 **Uptrend Anchor Exit Point:** ₹{historical_anchor_price:,.2f}\n"
                f"🔹 **RSI:** {current_rsi:.2f} | **Momentum:** {current_mom:.2f}\n\n"
                f"📝 *Execution Note:* Bearish exhaustion hit resistance line endpoint. Take profits and close position tomorrow morning."
            ),
            "metrics": {
                "live_price": current_close,
                "low_target": current_close * 0.85,
                "high_target": current_close * 1.05,
                "historic_move": ((current_close - historical_anchor_price) / historical_anchor_price) * 100,
                "start_date": df.index[-1].strftime("%Y-%m-%d"),
                "end_date": df.index[-1].strftime("%Y-%m-%d")
            }
        }

    return {"trigger": False, "action": None, "metrics": {}}
