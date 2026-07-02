import os
import requests
import csv
from datetime import datetime


def check_signal_age(ticker, current_strategy, window_days=15):
    """
    Analyzes historical CSV telemetry data to determine if a signal is Fresh or Old.
    Returns: (state, days_in_zone, first_seen_date_string)
    """
    file_path = "Data/alert_history_log.csv"
    today_str = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(file_path):
        return "BRAND_NEW", 0, today_str

    first_seen_date = None

    try:
        with open(file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Ticker") == ticker and row.get("Strategy") == current_strategy:
                    try:
                        log_date = datetime.strptime(
                            row.get("Timestamp").split()[0], "%Y-%m-%d").date()
                        if first_seen_date is None or log_date < first_seen_date:
                            first_seen_date = log_date
                    except Exception:
                        continue
    except Exception as e:
        print(f"   ⚠️ Error checking historical signal memory: {e}")
        return "BRAND_NEW", 0, today_str

    if first_seen_date is None:
        return "BRAND_NEW", 0, today_str

    today = datetime.now().date()
    days_in_zone = (today - first_seen_date).days
    first_seen_str = first_seen_date.strftime("%Y-%m-%d")

    if days_in_zone <= window_days:
        return "FRESH", days_in_zone, first_seen_str
    else:
        return "OLD", days_in_zone, first_seen_str


def trigger_alert(title, message, ticker, signal_type):
    """Dispatches breakout payloads straight to your Telegram Bot Chat using bulletproof HTML parsing."""
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print(
            f"   ⚠️ Telegram credentials missing. Suppression on alert for {ticker}.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Check signal state classification and pull original entry date
    state, days, original_date = check_signal_age(ticker, title)
    is_friday = datetime.now().weekday() == 4

    # Core Routing Gate Logic
    if state == "OLD" and not is_friday:
        print(
            f"   💤 {ticker} is a MATURE resident ({days} days in zone). Suppressed on daily feed.")
        return False

    # Apply tag prefixes containing explicit historical trigger timestamps
    if state == "OLD" and is_friday:
        header_tag = f"<b>💤 [MATURE MATRIX REVIEW]</b>\n<b>📅 Triggered On: {original_date}</b> ({days}d Ago)\n<b>🔔 {title}</b>"
    elif state == "FRESH":
        header_tag = f"<b>🔥 [FRESH TRADING SIGNAL]</b>\n<b>📅 Triggered On: {original_date}</b> ({days}d Ago)\n<b>🔔 {title}</b>"
    else:
        header_tag = f"<b>🌟 [BRAND NEW INITIALIZATION]</b>\n<b>📅 Triggered On: {original_date}</b> (Today)\n<b>🔔 {title}</b>"

    clean_msg = message.replace("*", "").replace("•", "🔹")
    html_text = f"{header_tag}\n\n{clean_msg}"

    payload = {
        "chat_id": chat_id,
        "text": html_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(
                f"   📣 Telegram notification dispatched successfully for {ticker} ({state})!")
            return True
        else:
            print(
                f"   ❌ Telegram API Error (Status {response.status_code}): {response.text}")
    except Exception as e:
        print(f"   ❌ Network failure connecting to Telegram: {e}")
    return False


def log_alert_to_csv(timestamp, strategy, ticker, price, floor, ceiling, move, start, end):
    """Appends structural alert data parameters safely to your local telemetry history files."""
    os.makedirs("Data", exist_ok=True)
    file_path = "Data/alert_history_log.csv"

    file_exists = os.path.exists(file_path)
    headers = ["Timestamp", "Strategy", "Ticker", "Live_Price",
               "Buy_Floor", "Exit_Ceiling", "Move_Pct", "Zone_Start", "Zone_End"]

    try:
        with open(file_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow([timestamp, strategy, ticker, price,
                            floor, ceiling, f"{move:.2f}%", start, end])
        print(
            f"   💾 Quantitative records appended to telemetry log sheet for {ticker}.")
    except Exception as e:
        print(f"   ⚠️ Failed to save metrics to CSV ledger: {e}")
