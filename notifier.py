import os
import requests
import csv


def trigger_alert(title, message, ticker, signal_type):
    """Dispatches breakout payloads straight to your Telegram Bot Chat using bulletproof HTML parsing."""
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print(
            f"   ⚠️ Telegram configuration credentials missing from environment variables. Suppression on alert for {ticker}.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # We clean up any loose markdown characters to prevent string formatting crashes
    clean_msg = message.replace("*", "").replace("•", "🔹")

    # Formulate a beautiful HTML formatted text block (bulletproof against special character bugs)
    html_text = (
        f"<b>🔔 {title}</b>\n\n"
        f"{clean_msg}"
    )

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
                f"   📣 Telegram notification dispatched successfully for {ticker}!")
            return True
        else:
            print(
                f"   ❌ Telegram API Error (Status {response.status_code}): {response.text}")
    except Exception as e:
        print(f"   ❌ Network failure connecting to Telegram nodes: {e}")
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
