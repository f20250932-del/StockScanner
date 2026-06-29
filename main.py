# main.py
import json
import os
from datetime import datetime, timedelta
import scanner
import reports
import notifier


def load_watchlist_tickers():
    """Safely loads tickers from watchlists.json without importing it as a module."""
    watchlist_path = "watchlists.json"
    if os.path.exists(watchlist_path):
        try:
            with open(watchlist_path, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "tickers" in data:
                    return data["tickers"]
                elif isinstance(data, dict):
                    for key, val in data.items():
                        if isinstance(val, list):
                            return val
        except Exception as e:
            print(f"⚠️ Error reading watchlists.json: {e}")
    return ["SBIN.NS", "TATAMOTORS.NS", "RELIANCE.NS"]


def execute_scan_cycle(tickers, force_alerts=False):
    """Loops through all tickers and processes scans via your scanner module."""
    print(f"🔍 Scanning {len(tickers)} assets...")
    for ticker in tickers:
        try:
            result = scanner.scan_single_stock(ticker)

            if result and isinstance(result, dict):
                title = f"SIGNAL DETECTED: {ticker}"
                message = (
                    f"Ticker: {ticker}\n"
                    f"Live Price: ₹{result.get('live_price')}\n"
                    f"Entry Price Target: ₹{result.get('low_target')}\n"
                    f"Exit Target: ₹{result.get('high_target')}\n"
                    f"Historic Move: {result.get('historic_move')}%"
                )
                # If force_alerts is True (EOD audit), it bypasses line-cross rules
                notifier.trigger_alert(title, message, ticker, "Impulse Zone")
        except Exception as e:
            print(f"⚠️ Error processing {ticker}: {e}")


def is_market_hours():
    """Checks if the current time falls within NSE/BSE trading sessions (Mon-Fri, 9:15 AM - 3:30 PM IST)."""
    now_utc = datetime.utcnow()
    now_ist = now_utc + timedelta(hours=5, minutes=30)

    if now_ist.weekday() >= 5:
        return False

    market_start = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    market_end = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)

    return market_start <= now_ist <= market_end


def main():
    print("🚀 Cloud Engine Instance Initiated...")

    now_utc = datetime.utcnow()
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    tickers = load_watchlist_tickers()

    if is_market_hours():
        print(
            f"\n🔔 Market is Open [{now_ist.strftime('%H:%M:%S')} IST]. Processing live tracking routine...")
        execute_scan_cycle(tickers, force_alerts=False)
    else:
        print(
            f"💤 Market Closed (Current IST: {now_ist.strftime('%Y-%m-%d %H:%M:%S')}). Running post-market evaluation...")
        execute_scan_cycle(tickers, force_alerts=True)

        # Auto-generate summaries if it's the late afternoon run
        # if now_ist.hour >= 15:
        print("📝 Generating post-market analytical data summaries...")
        reports.generate_all_reports()

    print("✅ Run cycle complete. Powering down cloud node safely.")


if __name__ == "__main__":
    main()
