import os
import requests
import pandas as pd

ALERT_LOG_FILE = "Data/alerts.csv"
sent_alerts = set()

# 🔑 Your Telegram Gateway Credentials
TELEGRAM_TOKEN = "8852776438:AAGn1z4sAo1qe86neId2ezqp9Lh6oMJOqUw"
TELEGRAM_CHAT_ID = "8069715872"


def send_telegram_message(title, message):
    """Sends the alert text directly to your Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"⚠️ *{title}* ⚠️\n\n{message}",
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("🚀 Alert successfully broadcasted to Telegram channel!")
        else:
            print(
                f"Telegram API Warning: Code {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Telegram Delivery Error: {e}")


def trigger_alert(title, message, ticker, signal_type):
    alert_key = (ticker, signal_type)
    if alert_key in sent_alerts:
        return False

    print(f"\n{'='*60}\n{title}\n{message}\n{'='*60}")

    # 📱 Clean Mobile delivery (No desktop popup code to crash the cloud node)
    send_telegram_message(title, message)

    sent_alerts.add(alert_key)
    return True


def log_alert_to_csv(timestamp, signal_type, ticker, live_price, low_target, high_target, historic_move, start_date, end_date):
    row = pd.DataFrame([{
        "Timestamp": timestamp, "Signal": signal_type, "Ticker": ticker, "Live Price": live_price,
        "Entry Price": low_target, "Exit Price": high_target, "Historic Move %": historic_move,
        "Move Start Date": start_date, "Move End Date": end_date
    }])
    header = not os.path.exists(ALERT_LOG_FILE)
    row.to_csv(ALERT_LOG_FILE, mode="a", header=header, index=False)
