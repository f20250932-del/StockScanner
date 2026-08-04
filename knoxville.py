import os
import time
import requests
import numpy as np
import pandas as pd
import yfinance as yf

# Exact V40 Companies List from Spreadsheet
V40_STOCKS = [
    # Conglomerates & Banks
    "LT.NS", "RELIANCE.NS", "SBIN.NS", "HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS", "KOTAKBANK.NS",
    # IT & Non-Banking Financials
    "HCLTECH.NS", "INFY.NS", "TCS.NS", "HDFCAMC.NS", "NAM-INDIA.NS", "HDFCLIFE.NS", "ICICIPRULI.NS",
    "ICICIGI.NS", "BAJAJFINSV.NS", "BAJAJHLDNG.NS", "BAJFINANCE.NS",
    # Auto & FMCG
    "BAJAJ-AUTO.NS", "MARUTI.NS", "HINDUNILVR.NS", "NESTLEIND.NS", "PGHH.NS", "PIDILITIND.NS",
    "COLPAL.NS", "DABUR.NS", "GILLETTE.NS", "MARICO.NS", "ITC.NS",
    # Consumer Products, Pharma & Paint
    "TITAN.NS", "PAGEIND.NS", "BATAINDIA.NS", "HAVELLS.NS", "VOLTAS.NS",
    "GLAXO.NS", "ABBOTINDIA.NS", "PFIZER.NS", "SANOFI.NS", "ASIANPAINT.NS", "BERGEPAINT.NS"
]


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculates Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def calculate_momentum(series: pd.Series, period: int = 20) -> pd.Series:
    """Calculates Momentum Oscillator."""
    return series - series.shift(period)


def send_telegram_alert(symbol: str, signal_type: str, price: float, rsi_val: float, mom_val: float):
    """Dispatches real-time signal notification to Telegram."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print(
            f"⚠️ Telegram credentials missing for {symbol}. Set TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID.")
        return

    is_bullish = "Bullish" in signal_type
    emoji = "🟢 BULLISH SIGNAL" if is_bullish else "🔴 BEARISH SIGNAL"

    message = (
        f"🚨 *RB_KnoxDiv ALERT TRIGGERED* 🚨\n\n"
        f"📌 *Stock Ticker:* `{symbol}`\n"
        f"⚡ *Signal Type:* {emoji}\n"
        f"📉 *Indicator:* Rob Booker Knoxville Divergence\n"
        f"💰 *Current Price:* ₹{price:.2f}\n"
        f"📊 *RSI (14):* {rsi_val:.2f}\n"
        f"🚀 *Momentum (20):* {mom_val:.2f}\n\n"
        f"⚙️ *Settings:* Bars Back: 200 | RSI: 14 | Mom: 20"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print(f"✅ Telegram notification delivered for {symbol}!")
        else:
            print(f"❌ Telegram API Error for {symbol}: {res.text}")
    except Exception as err:
        print(f"❌ Failed to deliver alert for {symbol}: {err}")


def analyze_knoxville_divergence(symbol: str, bars_back: int = 200, rsi_period: int = 14, mom_period: int = 20):
    """Evaluates Rob Booker Knoxville Divergence matching exact TradingView Settings."""
    try:
        df = yf.download(symbol, period="2y", interval="1d", progress=False)

        if df.empty or len(df) < bars_back:
            print(f"⚠️ Insufficient data for {symbol}.")
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df['RSI'] = calculate_rsi(df['Close'], period=rsi_period)
        df['Momentum'] = calculate_momentum(df['Close'], period=mom_period)

        # Inspect recent 5 daily candles to catch active divergence lines
        for i in range(-1, -6, -1):
            curr_price = float(df['Close'].iloc[i])
            curr_rsi = float(df['RSI'].iloc[i])
            curr_mom = float(df['Momentum'].iloc[i])

            start_idx = max(0, len(df) + i - bars_back)
            end_idx = len(df) + i

            hist_prices = df['Close'].iloc[start_idx:end_idx]
            hist_moms = df['Momentum'].iloc[start_idx:end_idx]
            hist_rsi = df['RSI'].iloc[start_idx:end_idx]

            # 1. Bullish Knoxville Divergence
            if (curr_price <= hist_prices.min() * 1.01) and (curr_mom > hist_moms.min()) and (curr_rsi <= 38 or hist_rsi.min() <= 30):
                signal_type = "Bullish Knoxville Divergence"
                print(
                    f"🎯 [{symbol}] {signal_type} Detected! Price: ₹{curr_price:.2f}")
                send_telegram_alert(symbol, signal_type,
                                    curr_price, curr_rsi, curr_mom)
                return "BULLISH"

            # 2. Bearish Knoxville Divergence
            if (curr_price >= hist_prices.max() * 0.99) and (curr_mom < hist_moms.max()) and (curr_rsi >= 62 or hist_rsi.max() >= 70):
                signal_type = "Bearish Knoxville Divergence"
                print(
                    f"🎯 [{symbol}] {signal_type} Detected! Price: ₹{curr_price:.2f}")
                send_telegram_alert(symbol, signal_type,
                                    curr_price, curr_rsi, curr_mom)
                return "BEARISH"

        print(f"ℹ️ [{symbol}] No active Knoxville Divergence signal.")
        return None

    except Exception as e:
        print(f"❌ Error processing {symbol}: {e}")
        return None


def run_full_v40_scan():
    """Runs scanner across all companies in the updated V40 list."""
    print("==================================================")
    print(
        f"🚀 STARTING V40 KNOXVILLE SCANNER ENGINE ({len(V40_STOCKS)} STOCKS)")
    print("==================================================")

    triggered_signals = []

    for idx, symbol in enumerate(V40_STOCKS, 1):
        print(f"\n[Scanning {idx}/{len(V40_STOCKS)}] {symbol}...")
        signal = analyze_knoxville_divergence(symbol)
        if signal:
            triggered_signals.append((symbol, signal))
        time.sleep(0.3)

    print("\n==================================================")
    print(
        f"🏁 SCAN COMPLETED! Total Signals Detected: {len(triggered_signals)}")
    for sym, sig in triggered_signals:
        print(f"  👉 {sym}: {sig}")
    print("==================================================")


if __name__ == "__main__":
    run_full_v40_scan()
