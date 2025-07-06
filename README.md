# AI Stock Analysis

This project is a Python application that integrates multiple APIs and an external AI prediction system to analyze stock trends and provide investment recommendations (buy, sell, or hold) for the upcoming period.

## 📑 Index

- [📈 How It Works](#-how-it-works)
- [🛠️ Requirements](#️-requirements)
- [⚙️ Installation](#️-installation)
- [💻 Command Line Usage](#-command-line-usage)
- [📁 Project Structure](#-project-structure)
- [🤖 Prediction Integration](#-prediction-integration)
- [📝 Configuration](#-configuration)
- [❗ Error Handling](#-error-handling)
- [🔒 Security](#-security)
- [📄 License](#-license)
- [🤝 Contributing](#-contributing)

## 📈 How It Works

The workflow is as follows:
1. **Yahoo Finance API**: Retrieves historical financial data (prices, volumes, etc.) for a stock over the last 4 weeks (28 days).
2. **News API**: Obtains all relevant news related to the stock for the same period, with caching to minimize API calls.
3. **Prediction Integration**: Runs an external AI stock prediction system ([ai-stock-prediction](https://github.com/simone-contorno/ai-stock-prediction)) to generate future price forecasts.  
   The path to this system is configurable via the `prediction_path` parameter in your `config.json` (see below).
4. **Together API**: Uses the meta-llama/Llama-3.3-70B-Instruct-Turbo-Free model to perform cross-analysis of market data, news, and AI-generated predictions.
5. **PDF Report**: Generates a detailed PDF report with all results, including the recommendation.

The analysis synthesizes financial data, news, and AI-generated price predictions to formulate a professional forecast of the stock's trend for the following month. This includes a detailed evaluation with key parameters such as historical performance, volatility, news impact, future price projections, and other indicators useful for deciding whether to buy, sell, or hold the stock.

## 🛠️ Requirements

- Python 3.8 or higher
- API Key for [News API](https://newsapi.org/)
- API Key for [Together AI](https://www.together.ai/)
- Clone [ai-stock-prediction](https://github.com/simone-contorno/ai-stock-prediction) and configure its `config.json`

## ⚙️ Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/trading-portfolio.git
cd trading-portfolio
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables:

```bash
cp .env.example .env
```

Edit the `.env` file and insert your API keys:

```
# API Key for News API
NEWS_API_KEY=your_news_api_key_here

# API Key for Together AI
TOGETHER_API_KEY=your_together_api_key_here
```

4. For prediction integration, clone [ai-stock-prediction](https://github.com/simone-contorno/ai-stock-prediction) to your machine.  
   Set the path to this folder using the `prediction_path` parameter in the `general` section of your `config.json`.

## 💻 Command Line Usage

You can run the analyzer directly from the command line and override configuration parameters using CLI arguments.

### Basic Usage

To analyze a stock (e.g., Apple), run:
```bash
python main.py --symbol AAPL
```

### Passing Parameters

You can specify the stock symbol and the analysis period (in days) as follows:
```bash
python main.py --symbol MSFT --period 14
```
or using short options:
```bash
python main.py -s MSFT -p 14
```
- `--symbol` or `-s`: The stock symbol to analyze (e.g., `AAPL`, `MSFT`, `GOOGL`).
- `--period` or `-p`: The number of days to analyze (e.g., `14` for the last 2 weeks).

If you omit these parameters, the defaults from your `config.json` will be used.

### Show Current Configuration

To display the current configuration without running an analysis:
```bash
python main.py --config
```
or
```bash
python main.py -c
```

## 📁 Project Structure

- **main.py**: Main orchestrator. Loads configuration, manages logging, and coordinates the workflow.
- **src/api/yahoo_finance_api.py**: Retrieves financial data and calculates technical indicators.
- **src/api/news_api.py**: Retrieves relevant news, caches results, and analyzes sentiment.
- **src/api/together_api.py**: Calls Together AI's LLM to analyze all data and generate a recommendation.
- **src/utils/prediction_integration.py**: Integrates with the external [ai-stock-prediction](https://github.com/simone-contorno/ai-stock-prediction) library to obtain future price predictions.
- **src/utils/pdf_generator.py**: Generates a PDF report with all results.
- **src/utils/news_db_manager.py**: Manages local caching of news articles by stock symbol and date, reducing redundant News API calls and efficiently storing/retrieving news data.
- **config/config.py**: Loads and manages configuration from `config.json`.

## 🤖 Prediction Integration

The prediction step uses the [ai-stock-prediction](https://github.com/simone-contorno/ai-stock-prediction) library. This is run as an external process, and its output is integrated into the analysis. You can configure its path and settings as needed.

## 📝 Configuration

The application supports custom configuration through the `config.json` file. This file is organized into sections that group parameters by functionality.

### Configuration Parameters

#### `general` Section
- `stock_symbol`: The stock symbol to analyze (e.g., "^GSPC" for S&P 500, "AAPL" for Apple)
- `analysis_period_days`: The time period in days for which to retrieve historical data and news
- `prediction_path`: **(New)** The path to the external AI stock prediction system.  
  This should point to the folder where you cloned [ai-stock-prediction](https://github.com/simone-contorno/ai-stock-prediction).

#### `yahoo_finance` Section
- Reserved for future parameters related to Yahoo Finance API

#### `together_ai` Section
- `together_model`: Together AI model to use (e.g., "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free")
- `together_max_tokens`, `together_temperature`, `together_top_p`, `together_top_k`, `together_repetition_penalty`: LLM generation parameters
- `investment_horizon`: Investment time horizon for analysis (e.g., "10 years")
- `output_language`: Output language for TogetherAI responses

#### `news_api` Section
- `max_news_articles`: Max number of articles to retrieve (null = no limit)
- `max_articles_per_day`: Max articles per day (null = no limit)
- `news_api_language`: Language of articles (e.g., "en")
- `news_api_sort_by`: Sorting criterion ("relevancy", "popularity", "publishedAt")
- `news_api_page_size`, `news_api_query_suffix`, `news_api_refresh_no_news`, `news_api_refresh_articles`: Additional News API options

You can override some values using command line arguments. See [Command Line Usage](#command-line-usage) for details.

## ❗ Error Handling

The project implements robust error handling to manage potential issues with the APIs. Each module includes detailed logging to facilitate debugging and problem resolution.

## 🔒 Security

API keys and other sensitive parameters are securely managed through environment variables, using the `.env` file and the `python-dotenv` library.

## 📄 License

This project is distributed under the [MIT license](LICENSE). See the `LICENSE` file for more details.

## 🤝 Contributing

Contributions are welcome! Please open an issue or a pull request to suggest changes or improvements.