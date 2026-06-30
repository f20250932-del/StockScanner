import pandas as pd
from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    """
    Abstract Base Class for all trading strategies. 
    Any future strategy you write must inherit this class and implement its methods.
    """
    @abstractmethod
    def name(self) -> str:
        """Returns the identifier name of the strategy."""
        pass

    @abstractmethod
    def analyze(self, ticker: str, data: pd.DataFrame) -> dict:
        """
        Analyzes historical stock data.
        Returns a dictionary containing:
        {
            "trigger": bool,
            "title": str,
            "message": str,
            "metrics": dict
        }
        """
        pass


class V20Strategy(BaseStrategy):
    """
    The core V20 Trading Strategy implementation.
    Tracks volume-backed breakout metrics.
    """

    def name(self) -> str:
        return "V20_Breakout"

    def analyze(self, ticker: str, data: pd.DataFrame) -> dict:
        # Fallback dictionary if conditions aren't met
        result = {"trigger": False, "title": "", "message": "", "metrics": {}}

        if data is None or len(data) < 21:
            return result

        # 1. Fetch relevant metrics from the pandas DataFrame
        current_close = float(data['Close'].iloc[-1])
        current_volume = float(data['Volume'].iloc[-1])

        # Calculate trailing 20-day averages
        avg_volume_20 = float(data['Volume'].iloc[-21:-1].mean())
        highest_close_20 = float(data['Close'].iloc[-21:-1].max())

        # 2. V20 Technical Rules Assessment
        # Example condition: Close beats 20-day high AND volume is 1.5x the 20-day average
        is_price_breakout = current_close > highest_close_20
        is_volume_spike = current_volume > (avg_volume_20 * 1.5)

        if is_price_breakout and is_volume_spike:
            vol_expansion_pct = ((current_volume / avg_volume_20) - 1) * 100

            result["trigger"] = True
            result["title"] = f"🚀 V20 Breakout Alert: {ticker}"
            result["message"] = (
                f"Ticker {ticker} has triggered a formal V20 breakout!\n"
                f"• Current Price: ₹{current_close:.2f} (Beats 20-day high of ₹{highest_close_20:.2f})\n"
                f"• Volume Expansion: {vol_expansion_pct:.1f}% above 20-day average."
            )
            result["metrics"] = {
                "live_price": current_close,
                "low_target": highest_close_20,
                "high_target": current_close * 1.20,  # Example +20% target
                "historic_move": vol_expansion_pct,
                "start_date": data.index[-21].strftime('%Y-%m-%d'),
                "end_date": data.index[-1].strftime('%Y-%m-%d')
            }

        return result


class MarketScanner:
    """Core scanning engine that coordinates data processing and strategy assessment."""

    def __init__(self, strategy: BaseStrategy):
        self.strategy = strategy

    def scan_stock(self, ticker: str, historical_data: pd.DataFrame) -> dict:
        """Executes the loaded strategy rules against the incoming ticker data stream."""
        return self.strategy.analyze(ticker, historical_data)
