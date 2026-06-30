import os
import json
import yfinance as yf
from datetime import datetime
import pytz

from scanner import MarketScanner, V20Strategy
import notifier
import reports

WATCHLIST_FILE = "watchlists.json"
PORTFOLIO_FILE = "portfolio.json"


def load_json_config(filepath, default_structure):
    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            json.dump(default_structure, f, indent=4)
        return default_structure
    with open(filepath, "r") as f:
        return json.load(f)


def execute_scan_cycle(tickers, portfolio_data):
    print("⏳ Initializing Risk-Aware Quantitative Engine...")

    v20_strategy = V20Strategy()
    scanner_engine = MarketScanner(strategy=v20_strategy)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 🧮 Compute risk allocation parameters globally for this run
    total_capital = float(portfolio_data.get(
        "total_portfolio_value_inr", 100000.0))
    three_percent_allocation = total_capital * 0.03

    # Mathematical Rule: Max of 3% or ₹5,000 flat ceiling
    target_trade_size = max(three_percent_allocation, 5000.0)
    max_six_percent_cap = target_trade_size * 2

    positions = portfolio_data.get("current_positions", {})

    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).history(period="3y")
            if df.empty or len(df) < 21:
                continue

            analysis = scanner_engine.scan_stock(ticker, df)

            if analysis["trigger"]:
                # 🛡️ RISK GUARD LAYER: Assess holding position allocations prior to firing alert
                already_allocated = 0.0
                if ticker in positions:
                    already_allocated = float(
                        positions[ticker].get("allocated_capital", 0.0))

                # Check if we have already used up our 2 allowed entries (6% maximum capital depth)
                if already_allocated >= max_six_percent_cap:
                    print(
                        f"🛑 Risk Core Bypass: {ticker} triggered buy line, but allocation is maxed out at 6% (₹{already_allocated}). Trigger suppressed.")
                    continue

                is_averaging_run = already_allocated > 0.0
                allocation_string = f"₹{target_trade_size:,.2f}" if not is_averaging_run else f"₹{target_trade_size:,.2f} (Position Averaging Layer)"

                # Enhance message with risk telemetry variables
                custom_msg = analysis["message"] + \
                    f"\n\n💰 *Risk Allocation Matrix:* Allocate *{allocation_string}* to this trade block."

                notifier.trigger_alert(
                    title=analysis["title"] +
                    (" [AVERAGING ENTRY]" if is_averaging_run else ""),
                    message=custom_msg,
                    ticker=ticker,
                    signal_type=v20_strategy.name()
                )

                m = analysis["metrics"]
                notifier.log_alert_to_csv(
                    timestamp, v20_strategy.name(), ticker,
                    m["live_price"], m["low_target"], m["high_target"],
                    m["historic_move"], m["start_date"], m["end_date"]
                )
        except Exception as e:
            print(f"❌ Error processing asset {ticker}: {e}")


def main():
    print("🚀 Cloud Execution Hub Waking Up...")
    tz_ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(tz_ist)
    print(
        f"⏰ System Execution Timestamp: {now_ist.strftime('%Y-%m-%d %H:%M:%S')} IST")

    # Load watchlists and portfolio data configurations
    watchlist_data = load_json_config(
        WATCHLIST_FILE, {"V40": [], "V40_Next": []})
    portfolio_data = load_json_config(
        PORTFOLIO_FILE, {"total_portfolio_value_inr": 100000.0, "current_positions": {}})

    # Combine lists into a single consolidated execution sequence
    tickers = watchlist_data.get("V40", []) + \
        watchlist_data.get("V40_Next", [])

    if not tickers:
        print("🛑 No target tickers found across indexing targets.")
        return

    execute_scan_cycle(tickers, portfolio_data)

    if now_ist.hour >= 15:
        print("📄 Post-market window detected. Compiling data history sheets...")
        reports.generate_all_reports()
    else:
        print("ℹ️ Intraday window. Skipping storage compilation.")

    print("✅ System Run Completed Safely.")


if __name__ == "__main__":
    main()
