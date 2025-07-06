# -*- coding: utf-8 -*-
"""
Main module for stock trend analysis.

This module integrates data from Yahoo Finance API, News API, and Together API
to generate an investment recommendation (buy, sell, or hold).
"""

import argparse
import logging
import os
import sys
import datetime
from pathlib import Path
from typing import Dict, Any
import time

from dotenv import load_dotenv

from src.api.yahoo_finance_api import YahooFinanceAPI
from src.api.news_api import NewsAPI
from src.api.together_api import TogetherAPI
from src.utils.pdf_generator import PDFGenerator
from src.utils.prediction_integration import PredictionIntegration
from config.config import load_config

# Load environment variables
load_dotenv()

# Configure the logger
# Remove all existing handlers to avoid duplication
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)


# Function to create the folder structure for logs and reports
def create_report_directory(symbol: str) -> tuple:
    # Create the output/logs folder if it doesn't exist
    logs_dir = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "logs"))
    logs_dir.mkdir(exist_ok=True, parents=True)

    # Create the subfolder for the symbol if it doesn't exist
    symbol_dir = logs_dir / symbol.upper()
    symbol_dir.mkdir(exist_ok=True)

    # Generate the timestamp for the folder
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create the subfolder with the timestamp
    report_dir = symbol_dir / f"{symbol.upper()}_{timestamp}"
    report_dir.mkdir(exist_ok=True)

    # Generate the log file name
    log_filename = f"{symbol.upper()}_{timestamp}.log"
    log_filepath = report_dir / log_filename

    return report_dir, log_filepath, timestamp


# Function to configure the logger with the log file path based on the symbol
# Global counters for log messages
log_counters = {"INFO": 0, "WARNING": 0, "ERROR": 0}


# Custom class to count log messages
class LogCounterHandler(logging.Handler):
    def emit(self, record):
        if record.levelname in log_counters:
            log_counters[record.levelname] += 1


def setup_logger(symbol: str):
    # Create the folder structure and get the log file path
    _, log_filepath, _ = create_report_directory(symbol)

    # Reset the counters
    for key in log_counters:
        log_counters[key] = 0

    # Configure the logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(
                str(log_filepath), mode="w"
            ),  # Mode 'w' to overwrite the file at each run
            logging.StreamHandler(),
        ],
    )

    # Create the custom handler to count messages
    counter_handler = LogCounterHandler()

    # Add the custom handler to the root logger to capture all messages
    root_logger = logging.getLogger()
    root_logger.addHandler(counter_handler)

    # Get the logger specific to this module
    logger = logging.getLogger(__name__)

    # Save the log file path to be able to add the summary at the end
    logger.log_filepath = log_filepath

    return logger


def write_log_summary(news_api=None):
    """Writes a summary of log messages at the end of the log file.

    Args:
        news_api: Instance of the NewsAPI class to retrieve statistics.
    """
    if hasattr(logger, "log_filepath") and logger.log_filepath:
        with open(str(logger.log_filepath), "a") as log_file:
            log_file.write("\n" + "=" * 50 + "\n")
            log_file.write("LOG SUMMARY:\n")

            # Add the summary of news retrieval if available
            if news_api is not None:
                log_file.write("\nNEWS RETRIEVAL STATISTICS:\n")
                log_file.write(
                    f"- Number of days with news retrieved from Database: {news_api.days_from_db}\n"
                )
                log_file.write(
                    f"- Number of days with news retrieved with NewsAPI: {news_api.days_from_api}\n"
                )
                log_file.write(
                    f"- Number of days with no news: {news_api.days_without_news}\n"
                )

            # Add the count of log messages
            log_file.write("\nLOG MESSAGE COUNT:\n")
            log_file.write(f"INFO: {log_counters['INFO']}\n")
            log_file.write(f"WARNING: {log_counters['WARNING']}\n")
            log_file.write(f"ERROR: {log_counters['ERROR']}\n")
            log_file.write("=" * 50 + "\n")


# Initialize the logger with a temporary file name
logger = logging.getLogger(__name__)


def get_company_name_from_symbol(symbol: str) -> str:
    """Gets the company name from the stock symbol.

    This is a simplified function that contains only some common symbols.
    In a real application, you could use a more complete API or database.

    Args:
        symbol: The stock symbol.

    Returns:
        The company name corresponding to the symbol.
    """
    company_map = {
        "AAPL": "Apple",
        "MSFT": "Microsoft",
        "GOOGL": "Google",
        "AMZN": "Amazon",
        "META": "Meta",
        "TSLA": "Tesla",
        "NVDA": "NVIDIA",
        "NFLX": "Netflix",
        "INTC": "Intel",
        "AMD": "AMD",
    }

    return company_map.get(symbol.upper(), f"Company {symbol}")


def analyze_stock(
    symbol: str | None = None, period: int | None = None
) -> tuple[Dict[str, Any], NewsAPI]:
    """Analyzes a stock and generates a recommendation.

    Args:
        symbol: The stock symbol to analyze. If None, the value from the config file is used.
        period: The period in days for which to retrieve data. If None, the value from the config file is used.

    Returns:
        Dictionary containing the analysis and recommendation.
    """
    # Load the configuration
    config = load_config()

    # Use the provided symbol or the one from the configuration
    if symbol is None:
        symbol = config["stock_symbol"]
        logger.info(f"Using symbol from configuration: {symbol}")

    # Use the provided period or the one from the configuration
    if period is None:
        period = config["analysis_period_days"]
        logger.info(f"Using period from configuration: {period} days")
    try:
        logger.info(f"Starting analysis for stock {symbol}")

        # Get the company name from the symbol
        # Add type check to ensure symbol is not None before passing to function
        if symbol is None:
            raise ValueError("Symbol cannot be None")
        company_name = get_company_name_from_symbol(symbol)
        company_info = {"name": company_name, "symbol": symbol}

        # Create the folder structure for reports
        report_dir, _, timestamp = create_report_directory(symbol)

        # Initialize the APIs
        yahoo_api = YahooFinanceAPI()
        news_api = NewsAPI()
        together_api = TogetherAPI()

        # Retrieve financial data
        logger.info(
            f"Retrieving financial data for {symbol} for a period of {period} days"
        )
        # Ensure period is not None before passing to get_stock_data
        if period is None:
            raise ValueError("Period cannot be None")
        stock_data_df = yahoo_api.get_stock_data(symbol, period)
        if stock_data_df is None:
            logger.error(f"Unable to retrieve financial data for {symbol}")
            return {
                "success": False,
                "error": f"Unable to retrieve financial data for {symbol}",
            }

        # Calculate technical indicators
        stock_data = yahoo_api.calculate_technical_indicators(stock_data_df)

        # Retrieve news
        logger.info(f"Retrieving news for {company_name} ({symbol})")
        articles = news_api.get_company_news(company_name, symbol)

        # Analyze the sentiment of the news
        news_data = news_api.analyze_sentiment(articles)

        # Get predictions from the external AI stock prediction system
        prediction_data = None
        try:
            logger.info(f"Attempting to retrieve predictions from external system for {symbol}")
            prediction_integration = PredictionIntegration(config["prediction_path"])
            prediction_data = prediction_integration.get_predictions(symbol)
            if prediction_data:
                logger.info(f"Predictions successfully retrieved for {symbol}")
            else:
                logger.warning(f"Unable to retrieve predictions for {symbol}, analysis will proceed without predictions")
        except Exception as e:
            logger.error(f"Error while retrieving predictions: {str(e)}")
            logger.warning("Analysis will proceed without predictions")
            prediction_data = None

        # Analyze the data with Together API
        logger.info(f"Analyzing data with Together API for {symbol}")
        analysis_result = together_api.analyze_data(
            stock_data, news_data, company_info, report_dir, prediction_data
        )

        # Add additional information to the result
        analysis_result["success"] = True

        # Generate the PDF report
        logger.info(f"Generating PDF report for {symbol}")
        pdf_generator = PDFGenerator()
        pdf_filename = f"{symbol.upper()}_{timestamp}.pdf"
        pdf_path = pdf_generator.generate_report(
            analysis_result, stock_data, prediction_data, report_dir, pdf_filename
        )

        if pdf_path:
            analysis_result["pdf_path"] = pdf_path
            logger.info(f"PDF report successfully generated: {pdf_path}")
        else:
            logger.warning(f"Unable to generate PDF report for {symbol}")

        logger.info(
            f"Analysis completed for {symbol} with recommendation: {analysis_result.get('recommendation', 'N/A')}"
        )
        return analysis_result, news_api

    except Exception as e:
        logger.error(f"Error during analysis of stock {symbol}: {str(e)}")
        return {"success": False, "error": str(e)}, None


def print_analysis_result(result: Dict[str, Any]) -> None:
    """Prints the analysis result in a readable format.

    Args:
        result: Dictionary containing the analysis result.
    """
    if not result.get("success", False):
        print(f"\n❌ ERROR: {result.get('error', 'Unknown error')}\n")
        return

    company = result.get("company", "")
    symbol = result.get("symbol", "")
    recommendation = result.get("recommendation", "N/A")
    analysis = result.get("analysis", "")

    # Determine the color and emoji for the recommendation
    if recommendation == "BUY":
        rec_color = "\033[92m"  # Green
        rec_emoji = "🟢"
    elif recommendation == "SELL":
        rec_color = "\033[91m"  # Red
        rec_emoji = "🔴"
    elif recommendation == "HOLD":
        rec_color = "\033[93m"  # Yellow
        rec_emoji = "🟡"
    else:
        rec_color = "\033[0m"  # No color
        rec_emoji = "❓"

    reset_color = "\033[0m"

    print("\n" + "=" * 80)
    print(f"📊 STOCK ANALYSIS: {company} ({symbol})")
    print("=" * 80)
    print(f"\n{rec_emoji} RECOMMENDATION: {rec_color}{recommendation}{reset_color}\n")
    print("📝 DETAILED ANALYSIS:")
    print("-" * 80)
    print(analysis)
    print("-" * 80)

    # PDF report information
    pdf_path = result.get("pdf_path")
    if pdf_path:
        print(f"\n📄 PDF REPORT: The report has been saved in {pdf_path}")

    print("\n" + "=" * 80 + "\n")


def main():
    global logger

    """Main function of the program."""
    try:
        # Load the configuration
        config = load_config()
        logger.info("Configuration successfully loaded")

        # Configure the argument parser
        parser = argparse.ArgumentParser(
            description="Analyze the trend of a stock and generate a recommendation."
        )
        parser.add_argument(
            "-s",
            "--symbol",
            type=str,
            default=config["stock_symbol"],
            help=f"The stock symbol to analyze (default: {config['stock_symbol']} from configuration)",
        )
        parser.add_argument(
            "-p",
            "--period",
            type=int,
            default=config["analysis_period_days"],
            help=f"Analysis period in days (default: {config['analysis_period_days']} from configuration)",
        )
        parser.add_argument(
            "-c",
            "--config",
            action="store_true",
            help="Show the current configuration and exit",
        )
        args = parser.parse_args()

        # If requested, show the configuration and exit
        if args.config:
            print("\nCurrent configuration:")
            for key, value in config.items():
                print(f"  {key}: {value}")
            return {"success": True, "message": "Configuration shown"}
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}")
        return {"success": False, "error": str(e)}

    # Configure the logger with the stock symbol
    logger = setup_logger(args.symbol)

    # Check that the necessary API keys are present
    if not os.getenv("NEWS_API_KEY"):
        logger.error(
            "API key for News API not found. Set NEWS_API_KEY in the .env file"
        )
        print(
            "❌ Error: API key for News API not found. Set NEWS_API_KEY in the .env file"
        )
        sys.exit(1)

    if not os.getenv("TOGETHER_API_KEY"):
        logger.error(
            "API key for Together API not found. Set TOGETHER_API_KEY in the .env file"
        )
        print(
            "❌ Error: API key for Together API not found. Set TOGETHER_API_KEY in the .env file"
        )
        sys.exit(1)

    # Analyze the stock
    result, news_api = analyze_stock(args.symbol, args.period)

    # Print the result
    print_analysis_result(result)

    # Write the log summary at the end of the log file
    write_log_summary(news_api)

    return result


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"Execution time: {round(end_time - start_time,2)} seconds")
