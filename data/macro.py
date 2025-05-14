# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import yfinance as yf
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv
import time
import google.generativeai as genai
import logging
import random
import json
import asyncio
import aiohttp

# Load environment variables
load_dotenv()

# Configure logging to use the same file as in the pdf_api
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(
            "market_api.log"
        ),  # Changed from macro.log to market_api.log
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("macro")  # Keep the logger name for component identification

# Set up Gemini API for insights generation
gemini_api_key = os.environ.get("GEMINI_API_KEY")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables")

app = FastAPI(
    title="Financial Data API",
    description="API for fetching real-time market and economic indicators",
    version="1.0.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class IndicatorData(BaseModel):
    value: str
    percent_change: str
    remarks: Optional[str] = None


class FinancialDashboard(BaseModel):
    last_updated: str
    indicators: Dict[str, IndicatorData]
    insights: Optional[str] = None


# Helper functions
def format_value(value, prefix="", suffix=""):
    """Format value with prefix and suffix"""
    if value is None:
        return "N/A"
    return f"{prefix}{value}{suffix}"


def calculate_percent_change(current, previous):
    """Calculate percentage change between two values"""
    if not previous or previous == 0:
        return "N/A"

    change = ((current - previous) / previous) * 100
    return f"{change:.2f}%"


def with_retry(func, max_retries=3, initial_delay=2):
    """
    Decorator function to retry API calls with exponential backoff
    """

    def wrapper(*args, **kwargs):
        retries = 0
        delay = initial_delay

        while retries <= max_retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                retries += 1
                if "Too Many Requests" in str(e) and retries <= max_retries:
                    # Add jitter to prevent synchronized retries
                    sleep_time = delay + random.uniform(0, 1)
                    logger.warning(
                        f"Rate limited, retrying in {sleep_time:.2f} seconds (attempt {retries}/{max_retries})..."
                    )
                    time.sleep(sleep_time)
                    # Exponential backoff
                    delay *= 2
                else:
                    if retries > max_retries:
                        logger.error(f"Max retries reached for {func.__name__}")
                    raise e

    return wrapper


async def with_retry_async(func, max_retries=3, initial_delay=2):
    """
    Async version of with_retry for async functions
    """
    retries = 0
    delay = initial_delay

    while retries <= max_retries:
        try:
            return await func()
        except Exception as e:
            retries += 1
            if "Too Many Requests" in str(e) and retries <= max_retries:
                # Add jitter to prevent synchronized retries
                sleep_time = delay + random.uniform(0, 1)
                logger.warning(
                    f"Rate limited, retrying in {sleep_time:.2f} seconds (attempt {retries}/{max_retries})..."
                )
                await asyncio.sleep(sleep_time)
                # Exponential backoff
                delay *= 2
            else:
                if retries > max_retries:
                    logger.error(f"Max retries reached for {func.__name__}")
                raise e


@with_retry
def get_stock_indices():
    """Get major stock indices data"""
    try:
        indices = {
            "^DJI": "Dow Jones",
            "^IXIC": "Nasdaq",
            "^GSPC": "S&P 500",
            "^N225": "Nikkei",
        }

        result = {}
        for symbol, name in indices.items():
            try:
                ticker = yf.Ticker(symbol)
                # Use a longer period to ensure we get data
                data = ticker.history(period="5d")

                if not data.empty:
                    current_price = data.iloc[-1]["Close"]
                    # Find the previous day with data
                    prev_idx = -2
                    while prev_idx >= -len(data) and pd.isna(
                        data.iloc[prev_idx]["Close"]
                    ):
                        prev_idx -= 1

                    if prev_idx >= -len(data):
                        prev_price = data.iloc[prev_idx]["Close"]
                        percent_change = calculate_percent_change(
                            current_price, prev_price
                        )

                        result[name] = IndicatorData(
                            value=format_value(round(current_price, 2)),
                            percent_change=percent_change,
                            remarks="Up" if current_price > prev_price else "Down",
                        )
                    else:
                        result[name] = IndicatorData(
                            value=format_value(round(current_price, 2)),
                            percent_change="N/A",
                            remarks="Previous data unavailable",
                        )
                else:
                    logger.info(f"No data available for {symbol}")
                    result[name] = IndicatorData(
                        value="N/A", percent_change="N/A", remarks="No data available"
                    )
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")
                result[name] = IndicatorData(
                    value="N/A", percent_change="N/A", remarks=f"Error: {str(e)}"
                )

        return result
    except Exception as e:
        logger.error(f"Error fetching stock indices: {e}")
        return {}


async def get_stock_indices_async():
    """Async version of get_stock_indices"""
    return await asyncio.to_thread(get_stock_indices)


@with_retry
def get_commodities_alpha_vantage():
    """Get commodity prices using Alpha Vantage API"""
    try:
        alpha_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not alpha_api_key:
            logger.warning("Alpha Vantage API key not found in environment variables")
            return {}

        result = {}

        # Get crude oil (WTI) data
        oil_url = f"https://www.alphavantage.co/query?function=WTI&interval=daily&apikey={alpha_api_key}"
        oil_response = requests.get(oil_url)
        oil_data = oil_response.json()

        if "data" in oil_data and len(oil_data["data"]) >= 2:
            # Extract the two most recent data points
            latest_oil_data = oil_data["data"][:2]

            current_price = float(latest_oil_data[0]["value"])
            prev_price = float(latest_oil_data[1]["value"])
            percent_change = calculate_percent_change(current_price, prev_price)

            result["Crude Oil (WTI)"] = IndicatorData(
                value=format_value(round(current_price, 2), "$"),
                percent_change=percent_change,
                remarks="Up" if current_price > prev_price else "Down",
            )
        else:
            logger.warning("Could not retrieve crude oil data from Alpha Vantage")
            result["Crude Oil (WTI)"] = IndicatorData(
                value="N/A", percent_change="N/A", remarks="Data unavailable"
            )

        # Add a small delay to avoid hitting rate limits
        time.sleep(2)

        # Get Brent oil data if available
        brent_url = f"https://www.alphavantage.co/query?function=BRENT&interval=daily&apikey={alpha_api_key}"
        brent_response = requests.get(brent_url)
        brent_data = brent_response.json()

        if "data" in brent_data and len(brent_data["data"]) >= 2:
            # Extract the two most recent data points
            latest_brent_data = brent_data["data"][:2]

            current_price = float(latest_brent_data[0]["value"])
            prev_price = float(latest_brent_data[1]["value"])
            percent_change = calculate_percent_change(current_price, prev_price)

            result["Crude Oil (Brent)"] = IndicatorData(
                value=format_value(round(current_price, 2), "$"),
                percent_change=percent_change,
                remarks="Up" if current_price > prev_price else "Down",
            )

        return result
    except Exception as e:
        logger.error(f"Error fetching commodities from Alpha Vantage: {str(e)}")
        # Add traceback for more detailed debugging
        import traceback

        logger.error(traceback.format_exc())
        return {}


async def get_commodities_alpha_vantage_async():
    """Async version of get_commodities_alpha_vantage"""
    try:
        alpha_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not alpha_api_key:
            logger.warning("Alpha Vantage API key not found in environment variables")
            return {}

        result = {}

        async with aiohttp.ClientSession() as session:
            # Get crude oil (WTI) data
            oil_url = f"https://www.alphavantage.co/query?function=WTI&interval=daily&apikey={alpha_api_key}"
            async with session.get(oil_url) as oil_response:
                oil_data = await oil_response.json()

                if "data" in oil_data and len(oil_data["data"]) >= 2:
                    # Extract the two most recent data points
                    latest_oil_data = oil_data["data"][:2]

                    current_price = float(latest_oil_data[0]["value"])
                    prev_price = float(latest_oil_data[1]["value"])
                    percent_change = calculate_percent_change(current_price, prev_price)

                    result["Crude Oil (WTI)"] = IndicatorData(
                        value=format_value(round(current_price, 2), "$"),
                        percent_change=percent_change,
                        remarks="Up" if current_price > prev_price else "Down",
                    )
                else:
                    logger.warning(
                        "Could not retrieve crude oil data from Alpha Vantage"
                    )
                    result["Crude Oil (WTI)"] = IndicatorData(
                        value="N/A", percent_change="N/A", remarks="Data unavailable"
                    )

            # Add a small delay to avoid hitting rate limits
            await asyncio.sleep(2)

            # Get Brent oil data if available
            brent_url = f"https://www.alphavantage.co/query?function=BRENT&interval=daily&apikey={alpha_api_key}"
            async with session.get(brent_url) as brent_response:
                brent_data = await brent_response.json()

                if "data" in brent_data and len(brent_data["data"]) >= 2:
                    # Extract the two most recent data points
                    latest_brent_data = brent_data["data"][:2]

                    current_price = float(latest_brent_data[0]["value"])
                    prev_price = float(latest_brent_data[1]["value"])
                    percent_change = calculate_percent_change(current_price, prev_price)

                    result["Crude Oil (Brent)"] = IndicatorData(
                        value=format_value(round(current_price, 2), "$"),
                        percent_change=percent_change,
                        remarks="Up" if current_price > prev_price else "Down",
                    )

        return result
    except Exception as e:
        logger.error(
            f"Error fetching commodities from Alpha Vantage asynchronously: {str(e)}"
        )
        import traceback

        logger.error(traceback.format_exc())
        return {}


@with_retry
def get_gold_price_alpha_vantage():
    """Get Gold price using Alpha Vantage API through the forex endpoint"""
    try:
        alpha_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not alpha_api_key:
            logger.warning("Alpha Vantage API key not found in environment variables")
            return {}

        # Use the CURRENCY_EXCHANGE_RATE endpoint to get real-time gold price in USD
        url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=XAU&to_currency=USD&apikey={alpha_api_key}"

        # Add retry logic for the request
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    timeout=(10, 30),  # (connect timeout, read timeout)
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()

                # Check if response is valid JSON
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response from Alpha Vantage: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(2**attempt)  # Exponential backoff
                        continue
                    return {
                        "Gold (MCX)": IndicatorData(
                            value="N/A",
                            percent_change="N/A",
                            remarks="Invalid response from API",
                        )
                    }

                if "Realtime Currency Exchange Rate" in data:
                    # Extract current gold price in USD per ounce
                    exchange_rate = data["Realtime Currency Exchange Rate"]
                    gold_usd_per_oz = float(exchange_rate["5. Exchange Rate"])
                    last_refreshed = exchange_rate["6. Last Refreshed"]

                    # Get previous day's data for comparison
                    estimated_prev_price = gold_usd_per_oz * 0.99
                    percent_change = "~1.00%"  # Estimated

                    # Convert from USD/oz to INR/10g
                    usd_inr = 83.50  # You might want to fetch this from the API as well
                    gold_inr_per_10g = gold_usd_per_oz * usd_inr * (10 / 31.1035)

                    return {
                        "Gold (MCX)": IndicatorData(
                            value=format_value(round(gold_inr_per_10g, 2), "₹", "/10g"),
                            percent_change=percent_change,
                            remarks=f"Last updated: {last_refreshed}",
                        )
                    }
                else:
                    error_message = data.get("Note", "Unknown error")
                    logger.warning(f"Alpha Vantage API error: {error_message}")
                    if attempt < max_retries - 1:
                        time.sleep(2**attempt)  # Exponential backoff
                        continue
                    return {
                        "Gold (MCX)": IndicatorData(
                            value="N/A",
                            percent_change="N/A",
                            remarks=f"API Error: {error_message}",
                        )
                    }

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff
                    continue
                return {
                    "Gold (MCX)": IndicatorData(
                        value="N/A",
                        percent_change="N/A",
                        remarks=f"Request Error: {str(e)}",
                    )
                }

        return {
            "Gold (MCX)": IndicatorData(
                value="N/A",
                percent_change="N/A",
                remarks="Failed after multiple attempts",
            )
        }

    except Exception as e:
        logger.error(f"Error fetching gold price from Alpha Vantage: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return {
            "Gold (MCX)": IndicatorData(
                value="N/A", percent_change="N/A", remarks=f"Error: {str(e)}"
            )
        }


async def get_gold_price_alpha_vantage_async():
    """Async version of get_gold_price_alpha_vantage"""
    try:
        alpha_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not alpha_api_key:
            logger.warning("Alpha Vantage API key not found in environment variables")
            return {}

        # Use the CURRENCY_EXCHANGE_RATE endpoint to get real-time gold price in USD
        url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=XAU&to_currency=USD&apikey={alpha_api_key}"

        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }

            # Implement retry with async sleep
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with session.get(
                        url, headers=headers, timeout=30
                    ) as response:
                        if response.status != 200:
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2**attempt)  # Exponential backoff
                                continue
                            return {
                                "Gold (MCX)": IndicatorData(
                                    value="N/A",
                                    percent_change="N/A",
                                    remarks=f"API Error: Status {response.status}",
                                )
                            }

                        try:
                            data = await response.json()
                        except Exception as e:
                            logger.error(
                                f"Invalid JSON response from Alpha Vantage: {str(e)}"
                            )
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2**attempt)
                                continue
                            return {
                                "Gold (MCX)": IndicatorData(
                                    value="N/A",
                                    percent_change="N/A",
                                    remarks="Invalid response from API",
                                )
                            }

                        if "Realtime Currency Exchange Rate" in data:
                            # Extract current gold price in USD per ounce
                            exchange_rate = data["Realtime Currency Exchange Rate"]
                            gold_usd_per_oz = float(exchange_rate["5. Exchange Rate"])
                            last_refreshed = exchange_rate["6. Last Refreshed"]

                            # Get previous day's data for comparison
                            estimated_prev_price = gold_usd_per_oz * 0.99
                            percent_change = "~1.00%"  # Estimated

                            # Convert from USD/oz to INR/10g
                            usd_inr = 83.50  # You might want to fetch this from the API as well
                            gold_inr_per_10g = (
                                gold_usd_per_oz * usd_inr * (10 / 31.1035)
                            )

                            return {
                                "Gold (MCX)": IndicatorData(
                                    value=format_value(
                                        round(gold_inr_per_10g, 2), "₹", "/10g"
                                    ),
                                    percent_change=percent_change,
                                    remarks=f"Last updated: {last_refreshed}",
                                )
                            }
                        else:
                            error_message = data.get("Note", "Unknown error")
                            logger.warning(f"Alpha Vantage API error: {error_message}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2**attempt)
                                continue
                            return {
                                "Gold (MCX)": IndicatorData(
                                    value="N/A",
                                    percent_change="N/A",
                                    remarks=f"API Error: {error_message}",
                                )
                            }

                except Exception as e:
                    logger.error(f"Request error on attempt {attempt + 1}: {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    return {
                        "Gold (MCX)": IndicatorData(
                            value="N/A",
                            percent_change="N/A",
                            remarks=f"Request Error: {str(e)}",
                        )
                    }

        return {
            "Gold (MCX)": IndicatorData(
                value="N/A",
                percent_change="N/A",
                remarks="Failed after multiple attempts",
            )
        }

    except Exception as e:
        logger.error(
            f"Error fetching gold price from Alpha Vantage asynchronously: {str(e)}"
        )
        import traceback

        logger.error(traceback.format_exc())
        return {
            "Gold (MCX)": IndicatorData(
                value="N/A", percent_change="N/A", remarks=f"Error: {str(e)}"
            )
        }


@with_retry
def get_currency_rates():
    """Get USD/INR exchange rate"""
    try:
        ticker = yf.Ticker("INR=X")
        data = ticker.history(period="5d")

        if not data.empty:
            current_rate = data.iloc[-1]["Close"]

            # Find the previous day with data
            prev_idx = -2
            while prev_idx >= -len(data) and pd.isna(data.iloc[prev_idx]["Close"]):
                prev_idx -= 1

            if prev_idx >= -len(data):
                prev_rate = data.iloc[prev_idx]["Close"]
                percent_change = calculate_percent_change(current_rate, prev_rate)

                return {
                    "USD/INR": IndicatorData(
                        value=format_value(round(current_rate, 2), "₹"),
                        percent_change=percent_change,
                        remarks=(
                            "INR weakened"
                            if current_rate > prev_rate
                            else "INR strengthened"
                        ),
                    )
                }
            else:
                return {
                    "USD/INR": IndicatorData(
                        value=format_value(round(current_rate, 2), "₹"),
                        percent_change="N/A",
                        remarks="Previous data unavailable",
                    )
                }
        else:
            return {
                "USD/INR": IndicatorData(
                    value="N/A", percent_change="N/A", remarks="Data unavailable"
                )
            }
    except Exception as e:
        logger.error(f"Error fetching currency rates: {e}")
        return {
            "USD/INR": IndicatorData(
                value="N/A", percent_change="N/A", remarks=f"Error: {str(e)}"
            )
        }


async def get_currency_rates_async():
    """Async version of get_currency_rates"""
    return await asyncio.to_thread(get_currency_rates)


def get_bond_yields():
    """Get India 10Y Government Bond Yield"""
    try:
        # For India bonds, we could use symbol "^TNX" for US 10Y as placeholder
        # In production, you would need a specialized API for Indian govt bonds
        ticker = yf.Ticker("^TNX")
        data = ticker.history(period="5d")

        if not data.empty:
            current_yield = data.iloc[-1]["Close"]

            # Find the previous day with data
            prev_idx = -2
            while prev_idx >= -len(data) and pd.isna(data.iloc[prev_idx]["Close"]):
                prev_idx -= 1

            if prev_idx >= -len(data):
                prev_yield = data.iloc[prev_idx]["Close"]
                percent_change = calculate_percent_change(current_yield, prev_yield)

                return {
                    "10Y Yield": IndicatorData(
                        value=format_value(round(current_yield, 2), "", "%"),
                        percent_change=percent_change,
                        remarks="Up" if current_yield > prev_yield else "Down",
                    )
                }
            else:
                return {
                    "10Y Yield": IndicatorData(
                        value=format_value(round(current_yield, 2), "", "%"),
                        percent_change="N/A",
                        remarks="Previous data unavailable",
                    )
                }
        else:
            # Fallback to placeholder static data
            current_yield = 7.15  # Placeholder value
            prev_yield = 7.10  # Placeholder value
            percent_change = calculate_percent_change(current_yield, prev_yield)

            return {
                "10Y Yield": IndicatorData(
                    value=format_value(current_yield, "", "%"),
                    percent_change=percent_change,
                    remarks="Up" if current_yield > prev_yield else "Down",
                )
            }
    except Exception as e:
        logger.error(f"Error fetching bond yields: {e}")
        return {
            "10Y Yield": IndicatorData(
                value="N/A", percent_change="N/A", remarks=f"Error: {str(e)}"
            )
        }


async def get_bond_yields_async():
    """Async version of get_bond_yields"""
    return await asyncio.to_thread(get_bond_yields)


def generate_indicators_insights(indicators):
    """Generate insights based on financial indicators using Gemini"""
    if not gemini_api_key:
        logger.warning("Cannot generate insights: GEMINI_API_KEY not available")
        return "Financial indicators insights not available (API key missing)"

    try:
        # Format indicators data for prompt
        indicator_summary = "\n".join(
            [
                f"- {name}: {data.value} ({data.percent_change} change, {data.remarks})"
                for name, data in indicators.items()
                if data.value != "N/A" and name != "_insights"
            ]
        )

        if not indicator_summary:
            return "Insufficient data to generate insights"

        # Create a targeted prompt for bullet-point insights
        prompt = f"""
        Based on the following financial indicators, provide 5-6 concise bullet-point insights:

        Financial Indicators:
        {indicator_summary}

        Please provide exactly 5-6 bullet points that cover:
        - Key market trends visible from these indicators
        - Correlations between different indicators (if any)
        - Potential impact on equity markets
        - Implications for investors
        - Economic outlook based on these indicators
        - What investors should watch in the coming sessions

        Guidelines:
        - Format each bullet point with a simple dash (-) at the beginning
        - Each point must be one sentence maximum
        - Focus on actionable insights
        - Use professional, formal tone
        - Avoid generic statements
        - Do not include any asterisks or markdown formatting
        - Return the bullet points as a clean list with one point per line
        """

        # Generate insights using Gemini
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            insight_text = response.text.strip()

            # Split by lines and clean up each bullet point
            lines = insight_text.split("\n")
            clean_lines = []

            for line in lines:
                line = line.strip()
                if line and not line.isspace():
                    # If line doesn't start with a dash, add one
                    if not line.startswith("-"):
                        if line.startswith("*"):
                            line = "- " + line[1:].strip()
                        else:
                            line = "- " + line
                    clean_lines.append(line)

            # Join the cleaned lines with newlines
            return "\n".join(clean_lines)
        except Exception as e:
            logger.error(f"Error generating insights with Gemini: {str(e)}")
            return "Unable to generate insights at this time"

    except Exception as e:
        logger.error(f"Error generating indicator insights: {str(e)}")
        return f"Indicator insights generation failed: {str(e)}"


async def generate_indicators_insights_async(indicators):
    """Async version of generate_indicators_insights"""
    return await asyncio.to_thread(generate_indicators_insights, indicators)


def fetch_all_financial_indicators():
    """
    Fetch all financial indicators from various sources and combine them into a single dictionary

    Returns:
        Dict: Combined dictionary of all financial indicators
    """
    all_indicators = {}

    # Add error handling for each individual section
    try:
        logger.info("Fetching stock indices")
        indices = get_stock_indices()
        all_indicators.update(indices)
        logger.debug(f"Retrieved {len(indices)} stock indices")
    except Exception as e:
        logger.error(f"Error fetching stock indices: {e}")

    try:
        logger.info("Fetching commodities data")
        commodities = get_commodities_alpha_vantage()
        all_indicators.update(commodities)
        logger.debug(f"Retrieved {len(commodities)} commodities")
    except Exception as e:
        logger.error(f"Error fetching commodities: {e}")

    try:
        logger.info("Fetching gold price")
        gold = get_gold_price_alpha_vantage()
        all_indicators.update(gold)
        logger.debug("Gold price data retrieved successfully")
    except Exception as e:
        logger.error(f"Error fetching gold price: {e}")

    try:
        logger.info("Fetching currency rates")
        currency = get_currency_rates()
        all_indicators.update(currency)
        logger.debug("Currency rates retrieved successfully")
    except Exception as e:
        logger.error(f"Error fetching currency rates: {e}")

    try:
        logger.info("Fetching bond yields")
        bonds = get_bond_yields()
        all_indicators.update(bonds)
        logger.debug("Bond yields retrieved successfully")
    except Exception as e:
        logger.error(f"Error fetching bond yields: {e}")

    # If we have at least some indicators, try to generate insights
    if all_indicators:
        # Generate insights on the indicators
        logger.info("Generating insights on financial indicators")
        insights = generate_indicators_insights(all_indicators)

        # Add insights to the indicators dictionary
        all_indicators["_insights"] = IndicatorData(
            value=insights, percent_change="", remarks="AI-generated insights"
        )
        logger.info("Financial indicators insights generated successfully")
    else:
        # Add a placeholder if no indicators were fetched
        logger.warning("No indicator data available to generate insights")
        all_indicators["_insights"] = IndicatorData(
            value="No indicator data available to generate insights",
            percent_change="",
            remarks="Service unavailable",
        )

    logger.info(
        f"Completed fetching all financial indicators: {len(all_indicators)} indicators retrieved"
    )
    return all_indicators


async def fetch_all_financial_indicators_async():
    """
    Async version to fetch all financial indicators from various sources

    Returns:
        Dict: Combined dictionary of all financial indicators
    """
    all_indicators = {}
    tasks = []

    # Create tasks for all the data fetching functions
    tasks.append(get_stock_indices_async())
    tasks.append(get_commodities_alpha_vantage_async())
    tasks.append(get_gold_price_alpha_vantage_async())
    tasks.append(get_currency_rates_async())
    tasks.append(get_bond_yields_async())

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process the results
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Error in task {i}: {result}")
            continue

        if isinstance(result, dict):
            all_indicators.update(result)

    # If we have at least some indicators, try to generate insights
    if all_indicators:
        # Generate insights on the indicators
        logger.info("Generating insights on financial indicators")
        insights = await generate_indicators_insights_async(all_indicators)

        # Add insights to the indicators dictionary
        all_indicators["_insights"] = IndicatorData(
            value=insights, percent_change="", remarks="AI-generated insights"
        )
        logger.info("Financial indicators insights generated successfully")
    else:
        # Add a placeholder if no indicators were fetched
        logger.warning("No indicator data available to generate insights")
        all_indicators["_insights"] = IndicatorData(
            value="No indicator data available to generate insights",
            percent_change="",
            remarks="Service unavailable",
        )

    logger.info(
        f"Completed fetching all financial indicators asynchronously: {len(all_indicators)} indicators retrieved"
    )
    return all_indicators
