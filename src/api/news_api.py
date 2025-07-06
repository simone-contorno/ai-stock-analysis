# -*- coding: utf-8 -*-
"""
Module for interacting with News API.

This module retrieves relevant news related to a stock
for the last 4 weeks (28 days) using the newsapi-python library.
Implements a caching system to reduce API calls, saving news in a local database.
"""

import datetime
import logging
import os
from typing import List, Dict, Any

from newsapi import NewsApiClient
from dotenv import load_dotenv

from config import get_config_value

from src.utils.news_db_manager import NewsDBManager

# Load environment variables
load_dotenv()

# Logger configuration
# Logging is not configured here, it is done in main.py
logger = logging.getLogger(__name__)


class NewsAPI:
    """Class for interacting with News API."""

    def __init__(self):
        """Initializes the NewsAPI class instance."""
        self.api_key = os.getenv("NEWS_API_KEY")
        if not self.api_key:
            logger.error(
                "API key for News API not found in environment variables"
            )
            raise ValueError(
                "NEWS_API_KEY not found. Make sure you have set it in the .env file"
            )

        try:
            self.newsapi = NewsApiClient(api_key=self.api_key)
            # Initializes the local database manager
            self.db_manager = NewsDBManager()
            # Initializes counters for statistics
            self.days_from_db = 0
            self.days_from_api = 0
            self.days_without_news = 0
            logger.info(
                "Initialization of News API and local database completed"
            )
        except Exception as e:
            logger.error(f"Error during News API initialization: {str(e)}")
            raise

    def get_company_news(
        self, company_name: str, symbol: str, days: int = 28
    ) -> List[Dict[str, Any]]:
        """Retrieves news related to a company.

        Args:
            company_name: The company name (e.g. 'Apple').
            symbol: The stock symbol (e.g. 'AAPL').
            days: The number of days for which to retrieve news (default: 28).

        Returns:
            List of dictionaries containing the retrieved news.
        """
        try:
            # Resets counters for statistics
            self.days_from_db = 0
            self.days_from_api = 0
            self.days_without_news = 0

            # Calculates the start (today - days) and end date
            end_date = datetime.datetime.now().date()
            start_date = end_date - datetime.timedelta(days=days)

            # Formats the dates in the required format for News API (YYYY-MM-DD)
            from_date = start_date.strftime("%Y-%m-%d")
            to_date = end_date.strftime("%Y-%m-%d")

            logger.info(
                f"Analysis period for {company_name} ({symbol}): from {from_date} to {to_date}"
            )

            # Gets the configuration parameter for article refresh
            refresh_articles = get_config_value("news_api_refresh_articles", False)
            
            if refresh_articles:
                # If refresh_articles is true, consider all dates as missing
                # to force the retrieval of new news even for days that already contain articles
                logger.info(f"Article refresh mode active: retrieving new news for all dates")
                missing_dates = [(start_date + datetime.timedelta(days=i)) for i in range((end_date - start_date).days + 1)]
            else:
                # Checks which dates have no news in the local database
                missing_dates = self.db_manager.get_missing_dates(
                    symbol, start_date, end_date
                )

            # Calculates the number of days with news already present in the database
            total_days = (end_date - start_date).days + 1
            self.days_from_db = total_days - len(missing_dates)

            # If all dates are already present in the database, retrieves news from the database
            if not missing_dates:
                logger.info(
                    f"All news for {symbol} are already present in the local database"
                )
                # Logs statistics (all dates from DB, none from API)
                logger.info(
                    f"News retrieval statistics for {symbol}: {self.days_from_db} days from DB, {self.days_from_api} days from API, {self.days_without_news} days without news"
                )
                return self._get_news_from_db(symbol, start_date, end_date)

            # Filters missing dates excluding weekends (Saturday and Sunday)
            weekday_missing_dates = []
            weekend_dates = []
            for date in missing_dates:
                if (
                    date.weekday() < 5
                ):  # 0-4 are Monday-Friday, 5-6 are Saturday-Sunday
                    weekday_missing_dates.append(date)
                else:
                    weekend_dates.append(date)

            # Adds weekends to the database with a special identifier
            for date in weekend_dates:
                weekend_data = {
                    "date": date.strftime("%Y-%m-%d"),
                    "articles": [],
                    "total_articles": 0,
                    "is_weekend": True,  # Special identifier for weekends
                }
                self.db_manager.save_news(symbol, date, weekend_data)
                self.days_without_news += 1

            # If there are no missing weekdays, retrieves news from the database
            if not weekday_missing_dates:
                logger.info(f"No missing weekday for {symbol}, only weekends")
                logger.info(
                    f"News retrieval statistics for {symbol}: {self.days_from_db} days from DB, {self.days_from_api} days from API, {self.days_without_news} days without news"
                )
                return self._get_news_from_db(symbol, start_date, end_date)

            # Otherwise, retrieves missing news from the API only for the necessary period
            logger.info(
                f"Retrieving news for {company_name} ({symbol}) for {len(weekday_missing_dates)} missing weekdays"
            )

            # Determines the minimum necessary period for the API call
            min_date = min(weekday_missing_dates)
            max_date = max(weekday_missing_dates)

            # Formats the dates for the API call
            api_from_date = min_date.strftime("%Y-%m-%d")
            api_to_date = max_date.strftime("%Y-%m-%d")

            logger.info(
                f"API call for the period from {api_from_date} to {api_to_date}"
            )

            # Gets parameters from the configuration
            language = get_config_value("news_api_language", "en")
            sort_by = get_config_value("news_api_sort_by", "relevancy")
            page_size = get_config_value("news_api_page_size", 100)
            query_suffix = get_config_value("news_api_query_suffix", "")
            
            # Creates a query that specifically includes the stock symbol to ensure relevant results
            base_query = symbol.replace("^", "")
            query = f"{base_query}{' OR ' + query_suffix if query_suffix else ''}".strip()
            
            logger.info(f"Parameters for News API call: language={language}, sort_by={sort_by}, page_size={page_size}")
            logger.info(f"Query for News API: '{query}'")
            
            # Retrieves news for the missing dates
            # Since News API does not allow specifying single dates but only ranges,
            # we make a call for the minimum necessary period (from the oldest to the most recent missing dates)
            news_response = self.newsapi.get_everything(
                q=query,
                from_param=api_from_date,
                to=api_to_date,
                language=language,
                sort_by=sort_by,
                page_size=page_size,
            )

            new_articles = news_response.get("articles", [])
            logger.info(
                f"Retrieved {len(new_articles)} articles for {company_name} ({symbol}) from the API"
            )

            # Organizes articles by date
            articles_by_date = self._organize_articles_by_date(new_articles)

            # Updates counters for statistics - only counts the dates that were actually missing
            dates_with_articles = set(articles_by_date.keys())
            weekday_missing_dates_str = {
                d.strftime("%Y-%m-%d") for d in weekday_missing_dates
            }
            self.days_from_api = len(
                dates_with_articles.intersection(weekday_missing_dates_str)
            )
            self.days_without_news += len(weekday_missing_dates) - self.days_from_api
            if self.days_without_news < 0:
                self.days_without_news = 0

            # Saves articles in the local database for each date
            for date, articles in articles_by_date.items():
                date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
                # Creates a dictionary with the articles for this date
                news_data = {
                    "date": date,
                    "articles": articles,
                    "total_articles": len(articles),
                }
                # Saves in the database
                self.db_manager.save_news(symbol, date_obj, news_data)

            # Also saves the weekdays for which no articles were found
            for date in weekday_missing_dates:
                date_str = date.strftime("%Y-%m-%d")
                if date_str not in articles_by_date:
                    # Creates a dictionary with empty array for this date
                    news_data = {"date": date_str, "articles": [], "total_articles": 0}

                    # Sets the no_news flag only if the date is more than 7 days older than the current date
                    current_date = datetime.datetime.now().date()
                    if (current_date - date).days > 7:
                        news_data["no_news"] = (
                            True  # Identifier for weekdays without news older than 7 days
                        )
                    # Saves in the database
                    self.db_manager.save_news(symbol, date, news_data)

            # Logs statistics
            logger.info(
                f"News retrieval statistics for {symbol}: {self.days_from_db} days from DB, {self.days_from_api} days from API, {self.days_without_news} days without news"
            )

            # Retrieves all news from the database (including the newly saved ones)
            return self._get_news_from_db(symbol, start_date, end_date)

        except Exception as e:
            logger.error(
                f"Error while retrieving news for {company_name}: {str(e)}"
            )
            return []

    def _organize_articles_by_date(
        self, articles: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Organizes articles by publication date.

        Args:
            articles: List of articles retrieved from News API.

        Returns:
            Dictionary with date as key and list of articles as value.
        """
        articles_by_date = {}

        for article in articles:
            # Extracts the publication date (format: 2023-01-01T12:00:00Z)
            published_at = article.get("publishedAt", "")
            if published_at:
                # Extracts only the date part (2023-01-01)
                date_str = published_at.split("T")[0]

                # Initializes the list if the date does not exist yet
                if date_str not in articles_by_date:
                    articles_by_date[date_str] = []

                # Adds the article to the list for this date
                articles_by_date[date_str].append(article)

        return articles_by_date

    def _get_news_from_db(
        self, symbol: str, start_date: datetime.date, end_date: datetime.date
    ) -> List[Dict[str, Any]]:
        """Retrieves news from the local database for the specified period.

        Args:
            symbol: The stock symbol.
            start_date: The start date of the period.
            end_date: The end date of the period.

        Returns:
            List of dictionaries containing the retrieved news.
        """
        all_articles = []
        current_date = start_date
        
        # Gets the configuration parameter for the limit of articles per day
        max_articles_per_day = get_config_value("max_articles_per_day", None)
        if max_articles_per_day is not None and isinstance(max_articles_per_day, int) and max_articles_per_day > 0:
            logger.info(f"Limit of articles per day for {symbol}: {max_articles_per_day}")
        else:
            logger.info(f"Limit of articles per day not configured for {symbol}")
        
        # Iterates over all dates in the period
        while current_date <= end_date:
            # Retrieves news for this date
            news_data = self.db_manager.get_news(symbol, current_date)

            # If there are news and it is not a weekend (or does not have the special identifier), add them to the list
            if (
                news_data
                and "articles" in news_data
                and not news_data.get("is_weekend", False)
            ):
                # Applies the limit of articles per day if configured
                if max_articles_per_day is not None and isinstance(max_articles_per_day, int) and max_articles_per_day > 0:
                    articles_for_day = news_data["articles"][:max_articles_per_day]
                    all_articles.extend(articles_for_day)
                    #if len(news_data["articles"]) > max_articles_per_day:
                    #    logger.info(f"Limited to {max_articles_per_day} articles out of {len(news_data['articles'])} available for {symbol} on date {current_date}")
                else:
                    all_articles.extend(news_data["articles"])

            # Moves to the next date
            current_date += datetime.timedelta(days=1)

        logger.info(
            f"Retrieved {len(all_articles)} articles from the local database for {symbol}"
        )
        return all_articles

    def analyze_sentiment(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyzes the sentiment of the retrieved news.

        Args:
            articles: List of articles retrieved from News API.

        Returns:
            Dictionary containing the sentiment analysis.
        """
        if not articles:
            logger.warning("No article to analyze")
            return {
                "total_articles": 0,
                "sentiment_summary": "No news available for analysis",
                "articles": [],
            }

        try:
            # Extracts titles and descriptions for analysis
            processed_articles = []

            for article in articles:
                # Extracts relevant information
                processed_article = {
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "url": article.get("url", ""),
                    "publishedAt": article.get("publishedAt", ""),
                    "source": article.get("source", {}).get("name", ""),
                }
                processed_articles.append(processed_article)

            # Prepares the dictionary with the analysis
            sentiment_analysis = {
                "total_articles": len(processed_articles),
                "articles": processed_articles,
            }

            logger.info(
                f"Sentiment analysis completed for {len(processed_articles)} articles"
            )
            return sentiment_analysis

        except Exception as e:
            logger.error(f"Error during sentiment analysis: {str(e)}")
            return {
                "total_articles": len(articles),
                "sentiment_summary": f"Error during analysis: {str(e)}",
                "articles": [],
            }
