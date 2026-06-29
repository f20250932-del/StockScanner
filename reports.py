# reports.py
import os
import pandas as pd
from datetime import datetime


def categorize_and_write_report(df_filtered, report_type, filename):
    if df_filtered.empty:
        return

    # Parse numbers safely
    df_filtered["Historic Move %"] = df_filtered["Historic Move %"].astype(
        str).str.replace('%', '').astype(float)

    tier1 = df_filtered[df_filtered["Historic Move %"] >= 50]
    tier2 = df_filtered[(df_filtered["Historic Move %"] >= 30)
                        & (df_filtered["Historic Move %"] < 50)]
    tier3 = df_filtered[(df_filtered["Historic Move %"] >= 20)
                        & (df_filtered["Historic Move %"] < 30)]

    with open(filename, "w") as f:
        f.write(f"=== {report_type} PERFORMANCE REPORT ===\n")
        f.write(
            f"Generated on: {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}\n")
        f.write(f"Total Signals: {len(df_filtered)}\n\n")
        f.write(f"Tier 1 (Massive Moves >= 50%): {len(tier1)} signals\n")
        f.write(f"Tier 2 (Strong Moves 30%-50%): {len(tier2)} signals\n")
        f.write(f"Tier 3 (Standard Moves 20%-30%): {len(tier3)} signals\n\n")
        f.write("= SIGNAL DETAILS =\n")
        f.write(df_filtered[["Timestamp", "Ticker", "Signal",
                "Live Price", "Historic Move %"]].to_string(index=False))


def generate_all_reports(force_all=False):
    csv_path = "Data/alerts.csv"
    if not os.path.exists(csv_path):
        return

    df = pd.read_csv(csv_path)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    now = datetime.now()

    # 1. Daily Filter
    df_today = df[df['Timestamp'].dt.date == now.date()]
    if not df_today.empty:
        categorize_and_write_report(
            df_today, "DAILY", f"Data/daily_report_{now.strftime('%Y-%m-%d')}.txt")
        print("📊 Generated Categorized Daily Report.")

    # 2. End of Week Check
    if now.weekday() == 4 or force_all:
        df_week = df[df['Timestamp'].dt.isocalendar().week ==
                     now.isocalendar().week]
        categorize_and_write_report(
            df_week, "WEEKLY", f"Data/weekly_report_Wk{now.isocalendar().week}.txt")
        print("📊 Generated Categorized Weekly Report.")

    # 3. End of Month Check
    next_day = now.timestamp() + 86400
    is_last_day_of_month = datetime.fromtimestamp(next_day).month != now.month
    if is_last_day_of_month or force_all:
        df_month = df[df['Timestamp'].dt.month == now.month]
        categorize_and_write_report(
            df_month, "MONTHLY", f"Data/monthly_report_{now.strftime('%b-%Y')}.txt")
        print("📊 Generated Categorized Monthly Report.")

    # 4. End of Year Check
    is_last_day_of_year = datetime.fromtimestamp(next_day).year != now.year
    if is_last_day_of_year or force_all:
        df_year = df[df['Timestamp'].dt.year == now.year]
        categorize_and_write_report(
            df_year, "YEARLY", f"Data/yearly_report_{now.year}.txt")
        print("📊 Generated Categorized Yearly Report.")
