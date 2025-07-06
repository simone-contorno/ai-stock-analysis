# -*- coding: utf-8 -*-
"""
Module for managing the local news database.

This module handles saving and retrieving news from a local database
organized by stock symbol, reducing calls to the News API.
Each stock symbol has a single JSON file containing all news organized by date.
"""

import json
import os
import logging
from pathlib import Path
import datetime
from typing import Dict, List, Any, Optional

from config import get_config_value

# Logger configuration
logger = logging.getLogger(__name__)


class NewsDBManager:
    """Class for managing the local news database."""

    def __init__(self):
        """Initializes the NewsDBManager class instance."""
        # Create the main folder for the database if it doesn't exist
        self.db_dir = Path(
            os.path.join("data", "news_db")
        )
        self.db_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"Database directory: {self.db_dir}")

    def _get_symbol_file_path(self, symbol: str) -> Path:
        """Gets the file path for a specific symbol.

        Args:
            symbol: The stock symbol.

        Returns:
            Path: The file path for the symbol.
        """
        return self.db_dir / f"{symbol.upper()}.json"

    def _load_symbol_data(self, symbol: str) -> Dict[str, Any]:
        """Loads data for a specific symbol from the JSON file.

        Args:
            symbol: The stock symbol.

        Returns:
            Dict[str, Any]: The symbol data, an empty dictionary if the file does not exist.
        """
        file_path = self._get_symbol_file_path(symbol)
        if not file_path.exists():
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(
                f"Error loading data for {symbol}: {str(e)}"
            )
            return {}

    def _save_symbol_data(self, symbol: str, data: Dict[str, Any]) -> None:
        """Saves data for a specific symbol to the JSON file.

        Args:
            symbol: The stock symbol.
            data: The data to save.
        """
        file_path = self._get_symbol_file_path(symbol)
        try:
            # Sort dates from most recent to oldest
            sorted_data = {}
            for date in sorted(data.keys(), reverse=True):
                sorted_data[date] = data[date]

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(sorted_data, f, ensure_ascii=False, indent=2)
            # logger.info(f"Data saved for {symbol}")
        except Exception as e:
            logger.error(
                f"Error saving data for {symbol}: {str(e)}"
            )

    def save_news(
        self, symbol: str, date: datetime.date, news_data: Dict[str, Any]
    ) -> None:
        """Saves news to the local database.

        Args:
            symbol: The stock symbol.
            date: The date of the news.
            news_data: The news data to save.
        """
        try:
            # Load existing data for this symbol
            symbol_data = self._load_symbol_data(symbol)

            # Convert the date to string to use as key
            date_str = date.strftime("%Y-%m-%d")

            # Update the data with the new news
            symbol_data[date_str] = news_data

            # Save the updated data
            self._save_symbol_data(symbol, symbol_data)

            # logger.info(f"News saved for {symbol} on {date_str}")
        except Exception as e:
            logger.error(
                f"Error saving news for {symbol} on date {date}: {str(e)}"
            )

    def get_news(self, symbol: str, date: datetime.date) -> Optional[Dict[str, Any]]:
        """Retrieves news from the local database.

        Args:
            symbol: The stock symbol.
            date: The date of the news to retrieve.

        Returns:
            Optional[Dict[str, Any]]: The news data if present, otherwise None.
        """
        try:
            # Load existing data for this symbol
            symbol_data = self._load_symbol_data(symbol)

            # Convert the date to string to use as key
            date_str = date.strftime("%Y-%m-%d")

            # Check if there is news for this date
            if date_str not in symbol_data:
                # logger.info(f"No news found for {symbol} on {date_str}")
                return None

            # logger.info(f"News retrieved for {symbol} on {date_str}")
            return symbol_data[date_str]
        except Exception as e:
            logger.error(
                f"Error retrieving news for {symbol} on date {date}: {str(e)}"
            )
            return None

    def get_missing_dates(
        self, symbol: str, start_date: datetime.date, end_date: datetime.date
    ) -> List[datetime.date]:
        """Determines which dates in the specified period do not have saved news.

        Args:
            symbol: The stock symbol.
            start_date: The start date of the period.
            end_date: The end date of the period.

        Returns:
            List[datetime.date]: List of dates for which there is no saved news.
        """
        try:
            # Check if the option to update days without news is active
            refresh_no_news = get_config_value("news_api_refresh_no_news", False)
            
            # Load existing data for this symbol
            symbol_data = self._load_symbol_data(symbol)

            # Create a set of all dates in the period
            all_dates = set()
            current_date = start_date
            while current_date <= end_date:
                all_dates.add(current_date)
                current_date += datetime.timedelta(days=1)

            # Create a set of dates for which we already have valid news
            existing_dates = set()
            for date_str, data in symbol_data.items():
                try:
                    date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                    if start_date <= date <= end_date:
                        # Consider the date as existing only if:
                        # 1. It has articles, or
                        # 2. It is a weekend (is_weekend = True), or
                        # 3. It is a day without news (no_news = True) and the refresh_no_news option is False
                        if (
                            (data.get("articles") and len(data.get("articles")) > 0)
                            or data.get("is_weekend")
                            or (data.get("no_news") and not refresh_no_news)
                        ):
                            existing_dates.add(date)
                except ValueError:
                    # Ignore keys with invalid format
                    continue

            # Calculate missing dates
            missing_dates = list(all_dates - existing_dates)
            missing_dates.sort()  # Sort the dates

            logger.info(
                f"Missing dates for {symbol}: {len(missing_dates)} out of {len(all_dates)}"
            )
            return missing_dates
        except Exception as e:
            logger.error(
                f"Error calculating missing dates for {symbol}: {str(e)}"
            )
            return []

    def merge_news_data(
        self, cached_articles: List[Dict[str, Any]], new_articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merges existing articles with new articles, avoiding duplicates.

        Args:
            cached_articles: The articles already present in the cache.
            new_articles: The new articles to add.

        Returns:
            List[Dict[str, Any]]: The merged list of articles without duplicates.
        """
        # Create a set of URLs of existing articles to avoid duplicates
        existing_urls = {
            article.get("url") for article in cached_articles if article.get("url")
        }

        # Add only articles with URLs not present in the set
        merged_articles = cached_articles.copy()
        for article in new_articles:
            if article.get("url") and article.get("url") not in existing_urls:
                merged_articles.append(article)
                existing_urls.add(article.get("url"))

        return merged_articles
