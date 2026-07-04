import os
import pandas as pd
from datetime import datetime


def categorize_and_write_report(df_filtered, report_type, filename):
    if df_filtered.empty:
        return

    # Normalize column names to lowercase to prevent KeyErrors
    df_filtered.columns = df_filtered.columns.str.strip()

    # Safely extract and parse move percentages
    move_col = None
    for col in df_filtered.columns:
        if 'move' in col.lower():
            move_col = col
            break

    if move_col:
        df_filtered[move_col] = df_filtered[move_col].astype(
            str).str.replace('%', '').str.strip()
        df_filtered[move_col] = pd.to_numeric(
            df_filtered[move_col], errors='coerce').fillna(0.0)
    else:
        # Create fallback column if none found
        df_filtered["move_pct_parsed"] = 0.0
        move_col = "move_pct_parsed"

    # Define strategy-appropriate performance buckets (Tiers sorted by % drift)
    tier1 = df_filtered[df_filtered[move_col].abs() >= 5.0]
    tier2 = df_filtered[(df_filtered[move_col].abs() >= 2.0)
                        & (df_filtered[move_col].abs() < 5.0)]
    tier3 = df_filtered[df_filtered[move_col].abs() < 2.0]

    # Dynamically resolve available columns for printing
    available_cols = df_filtered.columns.tolist()
    print_cols = ["Timestamp", "Ticker"]

    # Try to append strategy/signal label
    for c in ["Strategy", "Signal", "action"]:
        if c in available_cols:
            print_cols.append(c)
            break

    # Try to append price and move layout
    for c in ["Live_Price", "Live Price", "live_price"]:
        if c in available_cols:
            print_cols.append(c)
            break
    print_cols.append(move_col)

    # Intersect to make sure we only print valid existing columns
    print_cols = [c for c in print_cols if c in available_cols]

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"=== {report_type} PERFORMANCE REPORT ===\n")
        f.write(
            f"Generated on: {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}\n")
        f.write(f"Total Signals Logs Processed: {len(df_filtered)}\n\n")
        f.write(
            f"Tier 1 (High Volatility Moves >= 5%): {len(tier1)} signals\n")
        f.write(f"Tier 2 (Moderate Volatility 2%-5%): {len(tier2)} signals\n")
        f.write(f"Tier 3 (Low Volatility < 2%): {len(tier3)} signals\n\n")
        f.write("= STRATEGY LOG DETAILS =\n")
        f.write(df_filtered[print_cols].to_string(index=False))


def generate_all_reports(force_all=False):
    log_files = ["Data/alert_history_log.csv",
                 "Data/alert_history_log_knoxville.csv"]
    dfs_to_combine = []

    for file_path in log_files:
        if os.path.exists(file_path):
            try:
                temp_df = pd.read_csv(file_path)
                if not temp_df.empty:
                    # Rename columns to ensure consistency across strategies
                    temp_df.columns = temp_df.columns.str.strip()
                    if "Strategy" not in temp_df.columns:
                        if "knoxville" in file_path.lower():
                            temp_df["Strategy"] = "KNOXVILLE"
                        else:
                            temp_df["Strategy"] = "V20"
                    dfs_to_combine.append(temp_df)
            except Exception as e:
                print(f"⚠️ Error reading {file_path}: {e}")

    if not dfs_to_combine:
        print("⚠️ No log history found to build reports.")
        return

    # Merge dataframes safely regardless of column mismatches
    df = pd.concat(dfs_to_combine, ignore_index=True, sort=False)

    # Clean timestamps
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    df = df.dropna(subset=['Timestamp']).sort_values(
        by='Timestamp', ascending=False)

    now = datetime.now()

    # 1. Daily Summary
    df_today = df[df['Timestamp'].dt.date == now.date()]
    if not df_today.empty:
        categorize_and_write_report(
            df_today.copy(), "DAILY", f"Data/daily_report_{now.strftime('%Y-%m-%d')}.txt")
        print("📊 Generated Categorized Daily Combined Report.")

    # 2. Weekly Summary (Every Friday or when forced)
    if now.weekday() == 4 or force_all:
        df_week = df[df['Timestamp'].dt.isocalendar().week ==
                     now.isocalendar().week]
        categorize_and_write_report(
            df_week.copy(), "WEEKLY", f"Data/weekly_report_Wk{now.isocalendar().week}.txt")
        print("📊 Generated Categorized Weekly Combined Report.")

    # 3. Monthly Summary (Last day of month or when forced)
    next_day = now.timestamp() + 86400
    is_last_day_of_month = datetime.fromtimestamp(next_day).month != now.month
    if is_last_day_of_month or force_all:
        df_month = df[df['Timestamp'].dt.month == now.month]
        categorize_and_write_report(
            df_month.copy(), "MONTHLY", f"Data/monthly_report_{now.strftime('%b-%Y')}.txt")
        print("📊 Generated Categorized Monthly Combined Report.")

    # 4. Yearly Summary
    is_last_day_of_year = datetime.fromtimestamp(next_day).year != now.year
    if is_last_day_of_year or force_all:
        df_year = df[df['Timestamp'].dt.year == now.year]
        categorize_and_write_report(
            df_year.copy(), "YEARLY", f"Data/yearly_report_{now.year}.txt")
        print("📊 Generated Categorized Yearly Combined Report.")
