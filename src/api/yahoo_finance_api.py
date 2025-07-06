# -*- coding: utf-8 -*-
"""
Module for interacting with Yahoo Finance API.

This module retrieves financial data for a stock
for the last 4 weeks (28 days) using the yfinance library.
"""

import datetime
import logging
from typing import Dict, Any, Optional

import pandas as pd
import yfinance as yf

# Logger configuration
# Logging is not configured here, it is done in main.py
logger = logging.getLogger(__name__)


class YahooFinanceAPI:
    """Class for interacting with Yahoo Finance API."""

    def __init__(self):
        """Initializes the YahooFinanceAPI class instance."""
        logger.info("Yahoo Finance API initialization")

    def get_stock_data(self, symbol: str, period: int = 28) -> Optional[pd.DataFrame]:
        """Retrieves historical data for a stock.

        Args:
            symbol: The stock symbol (e.g. 'AAPL' for Apple).
            period: The period in days for which to retrieve data (default: 28).

        Returns:
            DataFrame containing the historical data or None in case of error.
        """
        try:
            # Calculate the start date (today - period days)
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=period)

            logger.info(
                f"Retrieving data for {symbol} from {start_date.date()} to {end_date.date()}"
            )

            # Retrieve historical data
            stock_data = yf.download(symbol, start=start_date, end=end_date)

            if stock_data.empty:
                logger.warning(f"No data found for symbol {symbol}")
                return None

            logger.info(f"Retrieved {len(stock_data)} records for {symbol}")
            return stock_data

        except Exception as e:
            logger.error(f"Error retrieving data for {symbol}: {str(e)}")
            return None

    def calculate_technical_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculates technical indicators from historical data.

        Args:
            data: DataFrame containing the historical data.

        Returns:
            Dictionary containing the calculated technical indicators.
        """
        if data is None or data.empty:
            logger.warning(
                "Unable to calculate indicators: missing or empty data"
            )
            return {}

        try:
            # Calculate percentage change
            data["Daily_Return"] = data["Close"].pct_change()

            # Calculate 7-day moving average
            data["MA7"] = data["Close"].rolling(window=7).mean()

            # Calculate volatility (standard deviation of returns)
            volatility = data["Daily_Return"].std() * (252**0.5)  # Annualized

            # Calculate trend (percentage difference between first and last price)
            first_price = data["Close"].iloc[0]
            last_price = data["Close"].iloc[-1]
            trend_pct = ((last_price - first_price) / first_price) * 100

            # Calculate average volume
            avg_volume = data["Volume"].mean()

            # Calculate simplified RSI (Relative Strength Index)
            delta = data["Close"].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).fillna(0)
            current_rsi = rsi.iloc[-1]

            # Prepare the dictionary with indicators
            indicators = {
                "first_price": first_price,
                "last_price": last_price,
                "trend_pct": trend_pct,
                "volatility": volatility,
                "avg_volume": avg_volume,
                "rsi": current_rsi,
                "data": data,  # Include the full DataFrame for future analysis
            }

            logger.info(f"Technical indicators calculated successfully")
            return indicators

        except Exception as e:
            logger.error(
                f"Error calculating technical indicators: {str(e)}"
            )
            return {}
