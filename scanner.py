import yfinance as yf
import pandas as pd


def detect_historical_impulse(df):
    in_green_streak = False
    streak_start_idx = 0

    for i in range(len(df) - 1):
        is_green = df["Close"].iloc[i] > df["Open"].iloc[i]
        if is_green:
            if not in_green_streak:
                in_green_streak = True
                streak_start_idx = i
        else:
            if in_green_streak:
                streak_data = df.iloc[streak_start_idx:i]
                lowest_low = streak_data["Low"].min()
                highest_high = streak_data["High"].max()
                move_pct = ((highest_high - lowest_low) / lowest_low) * 100

                if move_pct >= 20:
                    start_dt = streak_data.index[0]
                    end_dt = streak_data.index[-1]
                    days_taken = (end_dt - start_dt).days
                    return True, lowest_low, highest_high, move_pct, start_dt.strftime("%d-%b-%Y"), end_dt.strftime("%d-%b-%Y"), days_taken
                in_green_streak = False

    return False, None, None, 0, None, None, 0


def scan_single_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        # Switched period from '1y' to '2y' (covers past 2 years of trading days)
        df = stock.history(period="2y", interval="1d")
        if df.empty or len(df) < 10:
            return None

        live_price = float(df["Close"].iloc[-1])
        found, low_target, high_target, historic_move, start_date, end_date, days_taken = detect_historical_impulse(
            df)

        if found:
            return {
                "live_price": live_price, "low_target": low_target, "high_target": high_target,
                "historic_move": historic_move, "start_date": start_date, "end_date": end_date,
                "days_taken": days_taken
            }
    except Exception as e:
        print(f"Error reading data for {ticker}: {e}")
    return None
