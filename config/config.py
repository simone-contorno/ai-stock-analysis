# -*- coding: utf-8 -*-
"""
Configuration module for the financial analysis application.

This module manages loading configurations from a JSON file
and provides default values for configuration parameters.
"""

import json
import logging
import os
from typing import Dict, Any

# Logger configuration
logger = logging.getLogger(__name__)

# Default values
DEFAULT_CONFIG = {
    "together_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    "together_max_tokens": 2048,
    "together_temperature": 0.3,
    "together_top_p": 0.9,
    "together_top_k": 40,
    "together_repetition_penalty": 1.0,
    "investment_horizon": "medium term",
    "output_language": "english",
    "stock_symbol": "AAPL",
    "analysis_period_days": 28,
    "max_news_articles": None,
    "max_articles_per_day": 5,
    "news_api_language": "en",
    "news_api_sort_by": "relevancy",
    "news_api_page_size": 100,
    "news_api_query_suffix": "",
    "news_api_refresh_no_news": False,
    "news_api_refresh_articles": False
}

# Path to the configuration file
CONFIG_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "config.json"
)


def load_config() -> Dict[str, Any]:
    """
    Loads the configuration from the JSON file if it exists, otherwise uses the default values.

    Returns:
        Dictionary containing the configuration.
    """
    config = DEFAULT_CONFIG.copy()

    try:
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, "r") as config_file:
                user_config = json.load(config_file)

                # Extract parameters from sections
                general_config = user_config.get("general", {})
                yahoo_finance_config = user_config.get("yahoo_finance", {})
                together_ai_config = user_config.get("together_ai", {})
                news_api_config = user_config.get("news_api", {})
                
                # Support for backward compatibility (unstructured config)
                # If the configuration file is not structured in sections, treat as flat config
                if not any([general_config, yahoo_finance_config, together_ai_config, news_api_config]):
                    general_config = together_ai_config = news_api_config = user_config

                # Together AI parameters
                if "together_model" in together_ai_config:
                    config["together_model"] = together_ai_config["together_model"]
                    logger.info(f"Together AI model set to: {config['together_model']}")
                
                if "together_max_tokens" in together_ai_config:
                    config["together_max_tokens"] = together_ai_config["together_max_tokens"]
                
                if "together_temperature" in together_ai_config:
                    config["together_temperature"] = together_ai_config["together_temperature"]
                
                if "together_top_p" in together_ai_config:
                    config["together_top_p"] = together_ai_config["together_top_p"]
                
                if "together_top_k" in together_ai_config:
                    config["together_top_k"] = together_ai_config["together_top_k"]
                
                if "together_repetition_penalty" in together_ai_config:
                    config["together_repetition_penalty"] = together_ai_config["together_repetition_penalty"]
                
                if "investment_horizon" in together_ai_config:
                    config["investment_horizon"] = together_ai_config["investment_horizon"]
                    logger.info(f"Investment horizon set to: {config['investment_horizon']}")

                if "output_language" in together_ai_config:
                    config["output_language"] = together_ai_config["output_language"]
                    logger.info(f"Output language set to: {config['output_language']}")
                
                # General parameters
                if "stock_symbol" in general_config:
                    if (
                        isinstance(general_config["stock_symbol"], str)
                        and general_config["stock_symbol"].strip()
                    ):
                        config["stock_symbol"] = general_config["stock_symbol"].upper()
                        logger.info(f"Stock symbol set to: {config['stock_symbol']}")
                    else:
                        logger.warning(
                            "Invalid stock symbol in configuration file, using default value"
                        )

                if "analysis_period_days" in general_config:
                    try:
                        period = int(general_config["analysis_period_days"])
                        if period > 0:
                            config["analysis_period_days"] = period
                            logger.info(f"Analysis period set to: {config['analysis_period_days']} days")
                        else:
                            logger.warning(
                                "Analysis period must be a positive number, using default value"
                            )
                    except (ValueError, TypeError):
                        logger.warning(
                            "Invalid analysis period in configuration file, using default value"
                        )

                if "prediction_path" in general_config:
                    if isinstance(general_config["prediction_path"], str):
                        config["prediction_path"] = general_config["prediction_path"]
                        logger.info(f"Prediction path set to: {config['prediction_path']}")
                    else:
                        logger.warning(
                            "Invalid prediction path in configuration file, using default value"
                        )
                        
                # News API parameters
                if "max_news_articles" in news_api_config:
                    if news_api_config["max_news_articles"] is None or (
                        isinstance(news_api_config["max_news_articles"], int)
                        and news_api_config["max_news_articles"] > 0
                    ):
                        config["max_news_articles"] = news_api_config["max_news_articles"]
                        logger.info(f"Maximum number of articles set to: {config['max_news_articles']}")
                    else:
                        logger.warning(
                            f"Invalid value for max_news_articles: {news_api_config['max_news_articles']}. Using default value: {DEFAULT_CONFIG['max_news_articles']}"
                        )
                
                if "news_api_language" in news_api_config:
                    if isinstance(news_api_config["news_api_language"], str):
                        config["news_api_language"] = news_api_config["news_api_language"]
                        logger.info(f"Language for News API set to: {config['news_api_language']}")
                    else:
                        logger.warning(f"Invalid value for news_api_language. Using default value: {DEFAULT_CONFIG['news_api_language']}")
                
                if "news_api_sort_by" in news_api_config:
                    if isinstance(news_api_config["news_api_sort_by"], str):
                        config["news_api_sort_by"] = news_api_config["news_api_sort_by"]
                        logger.info(f"Sort criterion for News API set to: {config['news_api_sort_by']}")
                    else:
                        logger.warning(f"Invalid value for news_api_sort_by. Using default value: {DEFAULT_CONFIG['news_api_sort_by']}")
                
                if "news_api_page_size" in news_api_config:
                    try:
                        page_size = int(news_api_config["news_api_page_size"])
                        if 1 <= page_size <= 100:  # News API limits to 100 results per page
                            config["news_api_page_size"] = page_size
                            logger.info(f"Page size for News API set to: {config['news_api_page_size']}")
                        else:
                            logger.warning(f"Out of range value for news_api_page_size: {page_size}. Must be between 1 and 100. Using default value: {DEFAULT_CONFIG['news_api_page_size']}")
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid value for news_api_page_size. Using default value: {DEFAULT_CONFIG['news_api_page_size']}")
                
                if "news_api_query_suffix" in news_api_config:
                    if isinstance(news_api_config["news_api_query_suffix"], str):
                        config["news_api_query_suffix"] = news_api_config["news_api_query_suffix"]
                        logger.info(f"Query suffix for News API set to: {config['news_api_query_suffix']}")
                    else:
                        logger.warning(f"Invalid value for news_api_query_suffix. Using default value: {DEFAULT_CONFIG['news_api_query_suffix']}")
                        
                if "news_api_refresh_no_news" in news_api_config:
                    if isinstance(news_api_config["news_api_refresh_no_news"], bool):
                        config["news_api_refresh_no_news"] = news_api_config["news_api_refresh_no_news"]
                        logger.info(f"Update news when not available: {config['news_api_refresh_no_news']}")
                    else:
                        logger.warning(f"Invalid value for news_api_refresh_no_news. Using default value: {DEFAULT_CONFIG['news_api_refresh_no_news']}")
                        
                if "news_api_refresh_articles" in news_api_config:
                    if isinstance(news_api_config["news_api_refresh_articles"], bool):
                        config["news_api_refresh_articles"] = news_api_config["news_api_refresh_articles"]
                        logger.info(f"Update news for days with existing articles: {config['news_api_refresh_articles']}")
                    else:
                        logger.warning(f"Invalid value for news_api_refresh_articles. Using default value: {DEFAULT_CONFIG['news_api_refresh_articles']}")
                
                if "max_articles_per_day" in news_api_config:
                    if news_api_config["max_articles_per_day"] is None or (
                        isinstance(news_api_config["max_articles_per_day"], int)
                        and news_api_config["max_articles_per_day"] > 0
                    ):
                        config["max_articles_per_day"] = news_api_config["max_articles_per_day"]
                        logger.info(f"Maximum number of articles per day set to: {config['max_articles_per_day']}")
                    else:
                        logger.warning(
                            f"Invalid value for max_articles_per_day: {news_api_config['max_articles_per_day']}. Using default value: {DEFAULT_CONFIG['max_articles_per_day']}"
                        )

                logger.info("Configuration successfully loaded from file")
        else:
            logger.info(
                f"Configuration file not found at {CONFIG_FILE_PATH}, using default values"
            )
            # Create a configuration file with default values
            create_default_config()
    except Exception as e:
        logger.error(f"Error while loading configuration: {str(e)}")
        logger.info("Using default values")

    return config


def create_default_config() -> None:
    """
    Creates a configuration file with default values.
    """
    try:
        with open(CONFIG_FILE_PATH, "w") as config_file:
            json.dump(DEFAULT_CONFIG, config_file, indent=4)
        logger.info(f"Default configuration file created at {CONFIG_FILE_PATH}")
    except Exception as e:
        logger.error(
            f"Error while creating default configuration file: {str(e)}"
        )


# Global variable to store cached configuration
_config_cache = None

def get_config_value(key: str, default: Any = None) -> Any:
    """
    Gets a specific value from the configuration.

    Args:
        key: The key of the value to get.
        default: The default value to return if the key does not exist.

    Returns:
        The configuration value or the default value.
    """
    global _config_cache

    # If the configuration has not been loaded yet, load it
    if _config_cache is None:
        _config_cache = load_config()
        logger.debug(f"Configuration loaded into cache")
    
    return _config_cache.get(key, default)
