import os
import json
import yfinance as yf
from datetime import datetime
import pytz

# Import our modular infrastructure components
from scanner import MarketScanner, V20Strategy
import notifier
import reports

WATCHLIST_FILE = "watchlists.json"


def load_watchlist():
    """Loads target stock tickers from the local JSON config layout."""
    if not os.path.exists(WATCHLIST_FILE):
        # Fallback defaults if the file gets misplaced
        default_data = {"tickers": ["RELIANCE.NS", "TCS.NS", "INFY.NS"]}
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(default_data, f, indent=4)
        return default_data["tickers"]

    with open(WATCHLIST_FILE, "r") as f:
        data = json.load(f)
        return data.get("tickers", [])


def execute_scan_cycle(tickers):
    """Core scanning execution loop utilizing the modular strategy engine framework."""
    print("⏳ Initializing Quantitative Engine Architecture...")

    # Instantiate the V20 strategy and pass it right into the decoupled scanner engine
    v20_strategy = V20Strategy()
    scanner_engine = MarketScanner(strategy=v20_strategy)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"📡 Processing live technical sweeps for {len(tickers)} assets...\n")

    for ticker in tickers:
        try:
            # Download 3 years of daily historical bars to satisfy the full 750-day V20 lookup window
            df = yf.Ticker(ticker).history(period="3y")
            if df.empty or len(df) < 21:
                print(f"⚠️ Skipped {ticker}: Insufficient historical bars.")
                continue

            # Pass the pandas DataFrame directly to the strategy framework
            analysis = scanner_engine.scan_stock(ticker, df)

            if analysis["trigger"]:
                # Broadcast the live breakout warning right to your Telegram chat app
                notifier.trigger_alert(
                    title=analysis["title"],
                    message=analysis["message"],
                    ticker=ticker,
                    signal_type=v20_strategy.name()
                )

                # Permanently append metric variables to Data/alerts.csv
                m = analysis["metrics"]
                notifier.log_alert_to_csv(
                    timestamp=timestamp,
                    signal_type=v20_strategy.name(),
                    ticker=ticker,
                    live_price=m["live_price"],
                    low_target=m["low_target"],
                    high_target=m["high_target"],
                    historic_move=m["historic_move"],
                    start_date=m["start_date"],
                    end_date=m["end_date"]
                )
        except Exception as e:
            print(f"❌ Error processing analysis matrix for {ticker}: {e}")


def main():
    print("🚀 Cloud Execution Hub Waking Up...")

    # Standardize time tracking zones to Indian Standard Time (IST)
    tz_ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(tz_ist)
    print(
        f"⏰ System Execution Timestamp: {now_ist.strftime('%Y-%m-%d %H:%M:%S')} IST")

    # Load tickers
    tickers = load_watchlist()
    if not tickers:
        print("🛑 Watchlist file is completely empty. Powering down engine.")
        return

    # Execute main analytical scan loop
    execute_scan_cycle(tickers)

    # ⏱️ Production Time Gate: Only write full files at market close (3:00 PM IST or later)
    if now_ist.hour >= 15:
        print("📄 Post-market window detected. Generating deep historical data reports...")
        reports.generate_all_reports()
    else:
        print("ℹ️ Morning/Intraday run cycle. Skipping afternoon file compiling step.")

    print("✅ Run cycle complete. Powering down cloud node safely.")


if __name__ == "__main__":
    main()
