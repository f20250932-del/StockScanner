import os
import json
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
import traceback

from scanner import MarketScanner, V20Strategy
import knoxville
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


def create_github_issue(ticker, current_price, target_size, action_type="BUY", strategy_tag="V20"):
    """Creates a tracking issue on GitHub for human approval confirmation layer."""
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")

    if not repo or not token:
        print("   ⚠️ GitHub credentials missing. Skipping approval tracking issue.")
        return None

    url = f"https://api.github.org/repos/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    issue_body = (
        f"### {strategy_tag}_QUANT_AUTOMATION_PAYLOAD\n"
        "```json\n"
        "{\n"
        f'  "ticker": "{ticker}",\n'
        f'  "action": "{action_type}",\n'
        f'  "price": {current_price},\n'
        f'  "allocation": {target_size},\n'
        f'  "strategy": "{strategy_tag}"\n'
        "}\n"
        "```\n\n"
        f"If you executed this {strategy_tag} trade in real life, click **Close Issue** below to sync your ledger."
    )

    payload = {
        "title": f"📢 [{strategy_tag} APPROVAL]: {action_type} {ticker} @ ₹{current_price}",
        "body": issue_body,
        "labels": [f"{strategy_tag.lower()}-trade-pending"]
    }

    try:
        response = requests.post(
            url, json=payload, headers=headers, timeout=10)
        if response.status_code == 201:
            print(
                f"   ✅ Provisioned GitHub Approval Issue for {ticker} ({strategy_tag}).")
            return response.json().get("html_url")
    except Exception as e:
        print(f"   ❌ Failed to contact GitHub Issue API endpoints: {e}")
    return None


def execute_scan_cycle(watchlist_data, portfolio_data, now_ist):
    print("⏳ Initializing Dual-Engine Risk-Aware Quantitative Desk...")

    v20_strategy = V20Strategy()
    scanner_engine = MarketScanner(strategy=v20_strategy)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_capital = float(portfolio_data.get(
        "total_portfolio_value_inr", 100000.0))
    target_trade_size = max(total_capital * 0.03, 5000.0)
    max_six_percent_cap = target_trade_size * 2

    v40_tickers = watchlist_data.get("V40", [])
    v40_next_tickers = watchlist_data.get("V40_Next", [])
    all_tickers = list(set(v40_tickers + v40_next_tickers))

    pending_alerts_queue = []
    is_post_market = now_ist.hour >= 15 and now_ist.minute >= 45 or now_ist.hour > 15

    for ticker in all_tickers:
        try:
            print(f"📡 Downloading market history for {ticker}...")
            df = yf.download(ticker, period="3y", progress=False)

            if df.empty:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.columns = [str(col).capitalize() for col in df.columns]

            # ---------------------------------------------------------
            # ENGINE MODULE 1: V20 STRATEGY
            # ---------------------------------------------------------
            try:
                v20_analysis = scanner_engine.scan_stock(ticker, df)
                if v20_analysis and v20_analysis.get("trigger"):
                    strategy_name = v20_strategy.name()
                    m = v20_analysis["metrics"]

                    # Exact structural mapping to match your CSV reporting columns
                    notifier.log_alert_to_csv(
                        timestamp, strategy_name, ticker, m["live_price"],
                        m["low_target"], m["high_target"], m.get(
                            "historic_move", m.get("Historic Move %", 0.0)),
                        m["start_date"], m["end_date"]
                    )

                    allocated = float(portfolio_data.get("current_positions", {}).get(
                        ticker, {}).get("allocated_capital", 0.0))
                    if allocated < max_six_percent_cap:
                        _, _, orig_date = notifier.check_signal_age(
                            ticker, strategy_name)
                        pending_alerts_queue.append({
                            "ticker": ticker, "strategy_tag": "V20", "original_date_str": orig_date,
                            "analysis": v20_analysis, "allocated": allocated, "size": target_trade_size
                        })
            except Exception as v20_err:
                print(
                    f"   ⚠️ V20 Strategy error processing {ticker}: {v20_err}")

            # ---------------------------------------------------------
            # ENGINE MODULE 2: KNOXVILLE DIVERGENCE
            # ---------------------------------------------------------
            if ticker in v40_tickers and is_post_market:
                try:
                    knox_analysis = knoxville.scan_knoxville_divergence(df)
                    if knox_analysis and knox_analysis.get("trigger"):
                        strategy_name = "KNOXVILLE"
                        m = knox_analysis["metrics"]

                        notifier.log_alert_to_csv(
                            timestamp, strategy_name, ticker, m["live_price"],
                            m["low_target"], m["high_target"], m.get(
                                "historic_move", m.get("Historic Move %", 0.0)),
                            m["start_date"], m["end_date"]
                        )

                        allocated = float(portfolio_data.get("current_positions", {}).get(
                            ticker, {}).get("allocated_capital", 0.0))
                        action = knox_analysis.get("action", "BUY")
                        if action == "SELL" or allocated < max_six_percent_cap:
                            _, _, orig_date = notifier.check_signal_age(
                                ticker, strategy_name)
                            pending_alerts_queue.append({
                                "ticker": ticker, "strategy_tag": "KNOXVILLE", "original_date_str": orig_date,
                                "analysis": knox_analysis, "allocated": allocated, "size": target_trade_size
                            })
                except Exception as knox_err:
                    print(
                        f"   ⚠️ Knoxville Strategy error processing {ticker}: {knox_err}")

        except Exception as e:
            print(f"❌ Core Exception processing asset {ticker}: {e}")

    # CHRONOLOGICAL DISPATCH LAYER (Fixed Action Key & Safe String Evaluation)
    if pending_alerts_queue:
        print(
            f"\nSorting {len(pending_alerts_queue)} total pending triggers safely...")
        try:
            pending_alerts_queue.sort(
                key=lambda x: str(x.get("original_date_str", "")))
        except Exception as sort_err:
            print(
                f"⚠️ Chronological sorting fell back to unstructured layout: {sort_err}")

        for item in pending_alerts_queue:
            try:
                t = item["ticker"]
                stag = item["strategy_tag"]
                action = item["analysis"].get("action", "BUY")
                is_avg = item["allocated"] > 0.0 and action == "BUY"

                alloc_str = f"₹{item['size']:,.2f}" if not is_avg else f"₹{item['size']:,.2f} (Position Averaging Layer)"
                if action == "SELL":
                    alloc_str = "LIQUIDATE POSITION (Take Profits)"

                approval_url = create_github_issue(
                    t, item["analysis"]["metrics"]["live_price"], item["size"], action, stag)

                custom_msg = item["analysis"]["message"] + \
                    f"\n\n💰 *Risk Matrix:* {alloc_str}"
                if approval_url and action == "BUY":
                    custom_msg += f"\n\n✅ [Click Here to Approve Trade & Log Link]({approval_url})"

                print(
                    f"   📣 Firing chronological update for {t} via {stag} channel vector...")
                notifier.trigger_alert(
                    title=item["analysis"]["title"] +
                    (" [AVERAGING ENTRY]" if is_avg else ""),
                    message=custom_msg, ticker=t, signal_type=stag
                )
            except Exception as dispatch_err:
                print(
                    f"   ❌ Error dispatching alert for {item.get('ticker')}: {dispatch_err}")


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

    execute_scan_cycle(watchlist_data, portfolio_data, now_ist)

    if now_ist.hour >= 15:
        print("📄 Post-market window detected. Compiling performance review assets...")
        try:
            reports.generate_all_reports()
            print("✅ Performance reviews compiled and delivered successfully.")
        except Exception as repo_err:
            print(f"❌ Failed to compile reports layout: {repo_err}")

    print("✅ System Run Completed Safely.")


if __name__ == "__main__":
    main()
