import pandas as pd
import numpy as np
from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    """Abstract Base Class for all quantitative trading strategies."""
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def analyze(self, ticker: str, data: pd.DataFrame) -> dict:
        pass


class V20Strategy(BaseStrategy):
    """
    V20 Quantitative Strategy.
    1. Scans the last 750 days of daily candlestick bars.
    2. Identifies blocks of strictly continuous green candles (Close > Open).
    3. Filters streaks where the move from the bunch's lowest low to highest high is >= 20%.
    4. Triggers a buy signal if the current price is testing the historical lowest low floor.
    """

    def name(self) -> str:
        return "V20_Range_Breakout"

    def analyze(self, ticker: str, data: pd.DataFrame) -> dict:
        result = {"trigger": False, "title": "", "message": "", "metrics": {}}

        if data is None or len(data) < 2:
            return result

        # Ensure we are looking at the dataframe row by row
        close_prices = data['Close'].values
        open_prices = data['Open'].values
        high_prices = data['High'].values
        low_prices = data['Low'].values
        dates = data.index

        valid_bunches = []
        current_bunch = []

        # Step 1: Track and extract all continuous green candle blocks
        for i in range(len(data)):
            is_green = close_prices[i] > open_prices[i]

            if is_green:
                current_bunch.append(i)
            else:
                # Streak broke, evaluate the completed bunch if it exists
                if current_bunch:
                    self._evaluate_and_store_bunch(
                        current_bunch, low_prices, high_prices, dates, valid_bunches)
                    current_bunch = []

        # Catch any active streak right up to the final bar
        if current_bunch:
            self._evaluate_and_store_bunch(
                current_bunch, low_prices, high_prices, dates, valid_bunches)

        if not valid_bunches:
            return result

        # Step 2: Use the most recent valid V20 bunch to establish our lines
        latest_bunch = valid_bunches[-1]
        buy_floor = latest_bunch["lowest_low"]
        sell_ceiling = latest_bunch["highest_high"]
        move_pct = latest_bunch["move_pct"]

        # Step 3: Check if the current price is at or near the 'lowest low' buy line
        current_close = float(close_prices[-1])

        # Trigger buy if price is within a 2.5% buffer of the support floor, but not broken below it significantly
        is_at_buy_line = (current_close >= buy_floor *
                          0.98) and (current_close <= buy_floor * 1.025)

        if is_at_buy_line:
            result["trigger"] = True
            result["title"] = f"🟩 V20 Buy Signal: {ticker}"
            result["message"] = (
                f"Asset *{ticker}* has retraced to its structural V20 support line!\n\n"
                f"• *Current Price:* ₹{current_close:.2f}\n"
                f"• *Entry Buy Line (Lowest Low):* ₹{buy_floor:.2f}\n"
                f"• *Exit Target Line (Highest High):* ₹{sell_ceiling:.2f}\n"
                f"• *Historical Move:* +{move_pct:.1f}% established between {latest_bunch['start_date']} and {latest_bunch['end_date']}.\n\n"
                f"💼 *Risk Management Notice:* Risk exactly 3% of your capital on this trade allocation max. No Stop Loss is applied per strategy configuration guidelines."
            )
            result["metrics"] = {
                "live_price": current_close,
                "low_target": buy_floor,
                "high_target": sell_ceiling,
                "historic_move": move_pct,
                "start_date": latest_bunch['start_date'],
                "end_date": latest_bunch['end_date']
            }

        return result

    def _evaluate_and_store_bunch(self, bunch_indices, low_prices, high_prices, dates, valid_bunches):
        """Helper matrix method to check if a continuous green streak satisfies the >20% move threshold."""
        bunch_lows = [low_prices[idx] for idx in bunch_indices]
        bunch_highs = [high_prices[idx] for idx in bunch_indices]

        lowest_low = float(min(bunch_lows))
        highest_high = float(max(bunch_highs))

        # Calculate percent gain from structural lowest low to highest high
        move_pct = ((highest_high - lowest_low) / lowest_low) * 100

        if move_pct >= 20.0:
            valid_bunches.append({
                "lowest_low": lowest_low,
                "highest_high": highest_high,
                "move_pct": move_pct,
                "start_date": dates[bunch_indices[0]].strftime('%Y-%m-%d'),
                "end_date": dates[bunch_indices[-1]].strftime('%Y-%m-%d')
            })


class MarketScanner:
    """Core scanning engine framework."""

    def __init__(self, strategy: BaseStrategy):
        self.strategy = strategy

    def scan_stock(self, ticker: str, historical_data: pd.DataFrame) -> dict:
        return self.strategy.analyze(ticker, historical_data)
