# -*- coding: utf-8 -*-
"""
Module for interacting with Together API.

This module uses the configured model (default: meta-llama/Llama-3.3-70B-Instruct-Turbo-Free)
to perform cross-analysis of market data and news.
"""

from pathlib import Path
import logging
import os
from typing import Dict, Any, Optional

import together
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logger configuration
# Logging is not configured here, it is done in main.py
logger = logging.getLogger(__name__)


class TogetherAPI:
    """Class for interacting with Together API."""

    def __init__(self):
        """Initializes the TogetherAPI class instance."""
        from config import get_config_value

        self.api_key = os.getenv("TOGETHER_API_KEY")
        if not self.api_key:
            logger.error(
                "API key for Together API not found in environment variables"
            )
            raise ValueError(
                "TOGETHER_API_KEY not found. Make sure it is set in the .env file"
            )

        try:
            # No longer assign together.api_key directly as it is deprecated
            # The Together library will automatically use the TOGETHER_API_KEY environment variable
            self.model = get_config_value(
                "together_model", "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
            )
            logger.info(
                f"Together API initialization completed with model: {self.model}"
            )
        except Exception as e:
            logger.error(f"Error during Together API initialization: {str(e)}")
            raise

    def analyze_data(
        self,
        stock_data: Dict[str, Any],
        news_data: Dict[str, Any],
        company_info: Dict[str, str],
        report_dir: Optional[Path] = None,
        prediction_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyzes financial data and news using the LLM model.

        Args:
            stock_data: Dictionary containing financial data and technical indicators.
            news_data: Dictionary containing news and sentiment analysis.
            company_info: Dictionary containing company information (name, symbol).

        Returns:
            Dictionary containing the analysis and recommendation.
        """
        try:
            # Extract relevant information
            company_name = company_info.get("name", "")
            symbol = company_info.get("symbol", "")

            # Prepare financial data in a readable format
            financial_summary = self._prepare_financial_summary(stock_data)

            # Prepare news in a readable format
            news_summary = self._prepare_news_summary(news_data)

            # Create the prompt for the LLM model
            prompt = self._create_analysis_prompt(
                company_name, symbol, financial_summary, news_summary, prediction_data
            )

            # Save the prompt to the log file if a report directory is provided
            if report_dir is not None:
                self._save_prompt_to_log(prompt, report_dir, symbol)

            logger.info(f"Sending analysis request to Together API for {symbol}")

            # Send the request to the LLM model
            try:
                # Get parameters from configuration with default values
                from config import get_config_value

                max_tokens = get_config_value("together_max_tokens", 2048)
                temperature = get_config_value("together_temperature", 0.3)
                top_p = get_config_value("together_top_p", 0.9)
                top_k = get_config_value("together_top_k", 40)
                repetition_penalty = get_config_value("together_repetition_penalty", 1.0)

                response = together.Complete.create(
                    prompt=prompt,
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    repetition_penalty=repetition_penalty,
                    stop=["\n\n\n"],
                )
                logger.info(
                    f"Response received from Together API: {type(response)}"
                )  # Log response type
            except Exception as e:
                logger.error(f"Error during Together API call: {str(e)}")
                raise

            # Extract the response
            # The response structure may be a dictionary
            if isinstance(response, dict):
                # Print the full response for debugging
                logger.info(f"Response structure: {response.keys()}")

                # Handle different response formats
                if "output" in response:
                    # Format: {'output': {'text': '...'}} or {'output': {'content': '...'}}
                    output = response["output"]
                    if isinstance(output, dict):
                        analysis_text = output.get("text", output.get("content", ""))
                    else:
                        analysis_text = str(output)
                elif "choices" in response:
                    # Format: {'choices': [{'text': '...'}]}
                    choices = response["choices"]
                    if choices and isinstance(choices, list) and len(choices) > 0:
                        analysis_text = choices[0].get("text", "")
                    else:
                        analysis_text = ""
                elif "text" in response:
                    # Format: {'text': '...'}
                    analysis_text = response["text"]
                elif "content" in response:
                    # Format: {'content': '...'}
                    analysis_text = response["content"]
                else:
                    # No recognized format
                    logger.warning(
                        f"Unrecognized response format: {str(response)[:200]}"
                    )
                    analysis_text = ""
            else:
                # Support for old response structure
                try:
                    analysis_text = response.output.text
                except AttributeError:
                    try:
                        analysis_text = response.text
                    except AttributeError:
                        analysis_text = str(response)

            # Ensure analysis_text is a non-empty string
            if not analysis_text:
                analysis_text = (
                    "It was not possible to generate an analysis. Please try again later."
                )
            else:
                analysis_text = analysis_text.strip()

            # Log successful extraction of text (without showing content)
            logger.info(
                f"Text successfully extracted from response (length: {len(analysis_text)} characters)"
            )

            # Save the response to the log file if a report directory is provided
            if report_dir is not None:
                self._save_response_to_log(analysis_text, report_dir, symbol)

            # Structure the response
            analysis_result = {
                "company": company_name,
                "symbol": symbol,
                "analysis": analysis_text,
                "recommendation": self._extract_recommendation(analysis_text),
            }

            logger.info(f"Analysis completed for {symbol}")
            return analysis_result

        except Exception as e:
            logger.error(
                f"Error during data analysis with Together API: {str(e)}"
            )
            return {
                "company": company_info.get("name", ""),
                "symbol": company_info.get("symbol", ""),
                "analysis": f"Error during analysis: {str(e)}",
                "recommendation": "N/A",
            }

    def _prepare_financial_summary(self, stock_data: Dict[str, Any]) -> str:
        """Prepares a summary of financial data in text format.

        Args:
            stock_data: Dictionary containing financial data and technical indicators.

        Returns:
            String containing the summary of financial data.
        """
        if not stock_data:
            return "No financial data available."

        # Extract indicators and convert to primitive types
        first_price = (
            float(stock_data.get("first_price", 0).iloc[0])
            if hasattr(stock_data.get("first_price", 0), "iloc")
            else float(stock_data.get("first_price", 0))
        )
        last_price = (
            float(stock_data.get("last_price", 0).iloc[0])
            if hasattr(stock_data.get("last_price", 0), "iloc")
            else float(stock_data.get("last_price", 0))
        )
        trend_pct = (
            float(stock_data.get("trend_pct", 0).iloc[0])
            if hasattr(stock_data.get("trend_pct", 0), "iloc")
            else float(stock_data.get("trend_pct", 0))
        )
        volatility = (
            float(stock_data.get("volatility", 0).iloc[0])
            if hasattr(stock_data.get("volatility", 0), "iloc")
            else float(stock_data.get("volatility", 0))
        )
        avg_volume = (
            float(stock_data.get("avg_volume", 0).iloc[0])
            if hasattr(stock_data.get("avg_volume", 0), "iloc")
            else float(stock_data.get("avg_volume", 0))
        )
        rsi = (
            float(stock_data.get("rsi", 0).iloc[0])
            if hasattr(stock_data.get("rsi", 0), "iloc")
            else float(stock_data.get("rsi", 0))
        )

        # Format the summary
        summary = f"""
- Initial price: ${first_price:.2f}
- Final price: ${last_price:.2f}
- Percentage change: {trend_pct:.2f}%
- Annualized volatility: {volatility:.2f}%
- Average daily volume: {avg_volume:.0f}
- RSI (Relative Strength Index): {rsi:.2f}
"""

        return summary

    def _prepare_news_summary(self, news_data: Dict[str, Any]) -> str:
        """Prepares a summary of news in text format.

        Args:
            news_data: Dictionary containing news and sentiment analysis.

        Returns:
            String containing the summary of news.
        """
        from config import get_config_value

        if not news_data or news_data.get("total_articles", 0) == 0:
            return "No news available."

        # Extract articles
        articles = news_data.get("articles", [])
        total_articles = news_data.get("total_articles", 0)

        # Get the maximum number of articles from configuration
        max_news_articles = get_config_value("max_news_articles", None)

        # If max_news_articles is None, include all available articles
        # otherwise limit to the number specified in the configuration
        if max_news_articles is None:
            max_articles = len(articles)
        else:
            # Ensure the number does not exceed available articles
            max_articles = min(max_news_articles, len(articles))

        selected_articles = articles[:max_articles]

        # Format the summary
        summary = (
            f"RELEVANT NEWS FROM THE LAST 4 WEEKS (total: {total_articles}):\n"
        )

        for i, article in enumerate(selected_articles, 1):
            title = article.get("title", "No title")
            date = article.get("publishedAt", "").split("T")[0]  # Extract only the date
            source = article.get("source", "Unknown source")
            summary += f"{i}. [{date}] {title} (Source: {source})\n"

        if total_articles > max_articles:
            summary += (
                f"... and {total_articles - max_articles} more articles not shown.\n"
            )

        return summary

    def _create_analysis_prompt(
        self, company_name: str, symbol: str, financial_summary: str, news_summary: str, prediction_summary: str = None
    ) -> str:
        """Creates the prompt for LLM analysis.

        Args:
            company_name: Company name.
            symbol: Stock symbol.
            financial_summary: Summary of financial data.
            news_summary: Summary of news.
            prediction_summary: Summary of predictions (optional).

        Returns:
            String containing the prompt for the LLM model.
        """
        from config import get_config_value

        # Get the investment horizon from configuration
        investment_horizon = get_config_value("investment_horizon", "medium term")
        # Add predictions to the prompt if available
        prediction_text = ""
        if prediction_summary:
            prediction_text = f"{prediction_summary}\n"

        # Get the output language from the configuration
        output_language = get_config_value("output_language", "english")
        
        prompt = f"""
<|begin_of_promptml|>
[System]
You are an expert financial analyst tasked with providing a comprehensive analysis and detailed recommendation for the stock {company_name} ({symbol}). Your analysis must be strictly based on the provided data and must be professional, objective, and easily interpretable.

[Input_Data]
- Financial Data (last 4 weeks): 
  {financial_summary}

- Relevant news (last 4 weeks):
  {news_summary}

- Future value predictions for the next days (if available):
  {prediction_text}

- Investment horizon: {investment_horizon}

[Analysis_Objectives]
1. **Historical Assessment:** Examine the recent historical performance of the stock, identifying significant trends and comparing it with market benchmarks if applicable.
2. **Volatility and Risk Analysis:** Assess the level of volatility and associated risks, highlighting any critical thresholds.
3. **News Impact:** Analyze the influence of news, giving greater relevance to authoritative and recent sources.
4. **Technical Indicators:** Identify and evaluate other relevant technical indicators (e.g., moving averages, RSI, MACD, supports and resistances).
5. **Market Context:** Consider the macroeconomic and sector context, integrating it into the analysis.
6. **Predictive Analysis:** If available, analyze the predicted future values, compare them with historical trends, and assess their plausibility based on the current context.
7. **Operational Recommendation:** Provide a clear final recommendation (BUY, SELL, or HOLD) with a detailed justification, highlighting any uncertainties or risks.

[Output_Format]
Organize the output into clear and well-structured sections:
- **Introduction:** Summary of the context, objectives, and main findings.
- **Historical and Technical Analysis:** Detailing trends, technical indicators, and volatility/risk assessment.
- **Sentiment and News Analysis:** Qualitative assessment of the impact of news, weighted by source/date.
- **Context and Benchmark:** Any comparisons with the general market or sector benchmarks.
- **Future Projections:** Analysis of predicted values for the coming days, assessment of their consistency with technical and fundamental analysis, and identification of possible turning points.
- **Final Recommendation:** Conclusions and operational indications (BUY, SELL, or HOLD) with detailed evidence and justifications.

The output language must be {output_language}.

[Output_Formatting]
Use "**" before and after the titles of the various output sections.

[Output]
<|assistant|>
<|end_of_promptml|>
"""
        return prompt

    def _save_prompt_to_log(self, prompt: str, report_dir: Path, symbol: str) -> None:
        """Saves the prompt sent to Together AI in a log file.

        Args:
            prompt: The prompt sent to Together AI.
            report_dir: The directory in which to save the log file.
            symbol: The stock symbol.
        """
        try:
            # Create the log file name
            log_filename = f"{symbol.upper()}_prompt.log"
            log_filepath = report_dir / log_filename

            # Save the prompt to the log file
            with open(log_filepath, "w", encoding="utf-8") as log_file:
                log_file.write(prompt)

            logger.info(f"Prompt saved in file: {log_filepath}")
        except Exception as e:
            logger.error(
                f"Error while saving the prompt to the log file: {str(e)}"
            )

    def _save_response_to_log(
        self, response_text: str, report_dir: Path, symbol: str
    ) -> None:
        """Saves the Together AI response in a log file.

        Args:
            response_text: The text of the Together AI response.
            report_dir: The directory in which to save the log file.
            symbol: The stock symbol.
        """
        try:
            # Create the log file name
            log_filename = f"{symbol.upper()}_response.log"
            log_filepath = report_dir / log_filename

            # Save the response to the log file
            with open(log_filepath, "w", encoding="utf-8") as log_file:
                log_file.write(response_text)

            logger.info(f"Response saved in file: {log_filepath}")
        except Exception as e:
            logger.error(
                f"Error while saving the response to the log file: {str(e)}"
            )

    def _extract_recommendation(self, analysis_text: str) -> str:
        """Extracts the final recommendation from the analysis.

        Args:
            analysis_text: Text of the analysis generated by the LLM model.

        Returns:
            String containing the recommendation (BUY, SELL, or HOLD).
        """
        # Log for debugging (without showing the text content)
        logger.info(f"Recommendation extraction completed")

        if not analysis_text:
            return "N/A"

        # Count exact (case sensitive) occurrences of the keywords
        buy_count = analysis_text.count("BUY")
        sell_count = analysis_text.count("SELL")
        hold_count = analysis_text.count("HOLD")

        logger.info(
            f"Occurrence count: BUY={buy_count}, SELL={sell_count}, HOLD={hold_count}"
        )

        # Find the maximum count
        max_count = max(buy_count, sell_count, hold_count)

        # If no occurrence found, return INDETERMINATE
        if max_count == 0:
            return "INDETERMINATE"

        # Create a list of recommendations with the maximum count
        recommendations = []
        if buy_count == max_count:
            recommendations.append("BUY")
        if sell_count == max_count:
            recommendations.append("SELL")
        if hold_count == max_count:
            recommendations.append("HOLD")

        # If there is more than one recommendation with the same maximum count, return UNKNOWN
        if len(recommendations) > 1:
            return "UNKNOWN"

        # Otherwise, return the only recommendation with the maximum count
        return recommendations[0]
