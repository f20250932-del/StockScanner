import os
import json
import requests
import yfinance as yf
from datetime import datetime
import pytz
import traceback

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


def create_github_issue(ticker, current_price, target_size, action_type="BUY"):
    """Creates a tracking issue on GitHub for the interactive human approval confirmation layer."""
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")

    if not repo or not token:
        print("   ⚠️ GitHub Repository string or session GITHUB_TOKEN missing from environment. Skipping confirmation gate links.")
        return None

    url = f"https://api.github.org/repos/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    issue_body = (
        "### v20_QUANT_AUTOMATION_PAYLOAD\n"
        "```json\n"
        "{\n"
        f'  "ticker": "{ticker}",\n'
        f'  "action": "{action_type}",\n'
        f'  "price": {current_price},\n'
        f'  "allocation": {target_size}\n'
        "}\n"
        "```\n\n"
        f"If you executed this trade in real life, simply click **Close Issue** below. "
        "The background cloud engine will capture the callback event and automatically update your `portfolio.json` master ledger."
    )

    payload = {
        "title": f"📢 [TRADE APPROVAL]: {action_type} {ticker} @ ₹{current_price}",
        "body": issue_body,
        "labels": ["v20-trade-pending"]
    }

    try:
        response = requests.post(
            url, json=payload, headers=headers, timeout=10)
        if response.status_code == 201:
            print(
                f"   ✅ Successfully provisioned GitHub Issue tracking gate for {ticker}.")
            return response.json().get("html_url")
        else:
            print(
                f"   ⚠️ GitHub API rejected issue creation with Status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"   ❌ Failed to contact GitHub Issue API endpoints: {e}")
    return None


def execute_scan_cycle(tickers, portfolio_data):
    print("⏳ Initializing Risk-Aware Quantitative Engine...")

    v20_strategy = V20Strategy()
    scanner_engine = MarketScanner(strategy=v20_strategy)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_capital = float(portfolio_data.get(
        "total_portfolio_value_inr", 100000.0))
    three_percent_allocation = total_capital * 0.03
    target_trade_size = max(three_percent_allocation, 5000.0)
    max_six_percent_cap = target_trade_size * 2

    positions = portfolio_data.get("current_positions", {})

    for ticker in tickers:
        try:
            print(
                f"📡 Downloading market history for {ticker} via cloud framework...")
            df = yf.download(ticker, period="3y", progress=False)

            if df.empty:
                print(f"   ❌ Data stream empty for {ticker}. Skipping asset.")
                continue

            # 🛠️ MultiIndex Flattening Step (Fixes columns breaking if yfinance nests ticker headers)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Force simple upper-case columns to map clean list profiles
            df.columns = [str(col).capitalize() for col in df.columns]

            analysis = scanner_engine.scan_stock(ticker, df)

            if analysis["trigger"]:
                already_allocated = 0.0
                if ticker in positions:
                    already_allocated = float(
                        positions[ticker].get("allocated_capital", 0.0))

                if already_allocated >= max_six_percent_cap:
                    print(
                        f"🛑 Risk Core Bypass: {ticker} allocation maxed out. Trigger suppressed.")
                    continue

                is_averaging_run = already_allocated > 0.0
                allocation_string = f"₹{target_trade_size:,.2f}" if not is_averaging_run else f"₹{target_trade_size:,.2f} (Position Averaging Layer)"

                current_price = analysis["metrics"]["live_price"]

                # Run triggers explicitly
                approval_url = create_github_issue(
                    ticker, current_price, target_trade_size)

                custom_msg = analysis["message"] + \
                    f"\n\n💰 *Risk Allocation Matrix:* Allocate *{allocation_string}* to this trade block."
                if approval_url:
                    custom_msg += f"\n\n✅ [Click Here to Approve & Update Portfolio Ledger]({approval_url})"

                print(f"   📣 Firing notification vectors for {ticker}...")
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
            print(
                f"❌ Critical Exception encountered processing asset {ticker}: {e}")
            print(traceback.format_exc())


def main():
    print("🚀 Cloud Execution Hub Waking Up...")
    tz_ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(tz_ist)
    print(
        f"⏰ System Execution Timestamp: {now_ist.strftime('%Y-%m-%d %H:%M:%S')} IST")

    watchlist_data = load_json_config(
        WATCHLIST_FILE, {"V40": [], "V40_Next": []})
    portfolio_data = load_json_config(
        PORTFOLIO_FILE, {"total_portfolio_value_inr": 100000.0, "current_positions": {}})

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
