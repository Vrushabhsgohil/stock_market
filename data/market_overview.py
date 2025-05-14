from fastapi import FastAPI, APIRouter
import yfinance as yf
from datetime import datetime
import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv
import json
import time
import asyncio

# Load environment variables
load_dotenv()

app = FastAPI()
router = APIRouter()

# Configure logging - Using same format and approach as the first file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("market_api.log"),  # Using market_api.log for consistency
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(
    "market_data"
)  # Unique logger name for component identification

# Primary and alternative symbols for Indian indices
# Format: (primary_symbol, [list_of_alternative_symbols])
index_mapping = [
    ("^NSEI", ["NIFTY50.NS", "NIFTY.NS"]),  # Nifty 50
    ("^BSESN", ["SENSEX.BO", "BSE.NS"]),  # BSE SENSEX
    ("^CRSLDX", ["CRSLDX.NS"]),  # CRSLDX
    ("^NSEBANK", ["BANKNIFTY.NS", "NIFTYBANK.NS"]),  # Bank Nifty
    ("^CNXIT", ["CNXIT.NS", "NIFTYIT.NS"]),  # IT Index
    ("^NSEMDCP50", ["NIFTYMDCP50.NS", "NIFTYMIDCAP50.NS"]),  # Midcap 50
]

# Create flat list of primary symbols (these will be returned in response)
primary_symbols = [item[0] for item in index_mapping]

# Set up Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Index name mapping
index_names = {
    "^NSEI": "NIFTY 50",
    "^BSESN": "SENSEX",
    "^CRSLDX": "CRSLDX",
    "^NSEBANK": "BANK NIFTY",
    "^CNXIT": "NIFTY IT",
    "^NSEMDCP50": "NIFTY Midcap 50",
}


def fetch_market_data():
    """
    Fetch market data for all indices with retry and fallback mechanisms
    """
    market_data = {}

    # Add metadata
    now = datetime.now()
    market_data["_meta"] = {
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now.strftime("%H:%M:%S"),
    }

    # For each primary symbol and its alternatives
    for primary_symbol, alternative_symbols in index_mapping:
        logger.info(f"Attempting to fetch data for {primary_symbol}")

        # Try all possible periods for better chances of success
        for period in ["2d", "5d", "1wk"]:
            # First try with the primary symbol
            all_symbols_to_try = [primary_symbol] + alternative_symbols

            for symbol in all_symbols_to_try:
                try:
                    # Add delay to avoid rate limiting
                    time.sleep(0.5)

                    logger.info(f"Trying {symbol} with period {period}")
                    data = yf.Ticker(symbol)
                    history = data.history(period=period)

                    if len(history) >= 2:
                        prev_close = history.iloc[-2]["Close"]
                        current = history.iloc[-1]

                        # Calculate change
                        change = current["Close"] - prev_close
                        change_percent = (change / prev_close) * 100

                        # Store under the primary symbol regardless of which alternative worked
                        market_data[primary_symbol] = {
                            "Open": round(current["Open"], 2),
                            "High": round(current["High"], 2),
                            "Low": round(current["Low"], 2),
                            "Close": round(current["Close"], 2),
                            "Change": round(change, 2),
                            "Change%": round(change_percent, 2),
                            "PrevClose": round(prev_close, 2),
                            "FetchedFrom": symbol,  # Track which symbol actually worked
                        }
                        logger.info(
                            f"Successfully fetched data for {primary_symbol} using {symbol}"
                        )
                        break  # Success! Break the symbol loop

                except Exception as e:
                    logger.warning(
                        f"Failed to fetch {symbol} with period {period}: {str(e)}"
                    )
                    continue

            # Check if we got data for this primary symbol
            if primary_symbol in market_data:
                break  # Success! Break the period loop

        # If we still don't have data after trying all options
        if primary_symbol not in market_data:
            logger.warning(
                f"Could not fetch data for {primary_symbol} or any of its alternatives"
            )
            market_data[primary_symbol] = {"Error": "Data unavailable"}

    return market_data


async def fetch_market_data_async():
    """
    Async version of fetch_market_data
    """
    return await asyncio.to_thread(fetch_market_data)


def generate_concise_insights(market_data, sentence_count=6):
    """
    Generate insights using Gemini API in exactly 5-6 sentences
    """
    # Prepare readable data, only for indices with valid data
    readable_text = ""
    valid_data_count = 0

    for symbol, data in market_data.items():
        if symbol != "_meta" and "Open" in data:
            index_name = index_names.get(symbol, symbol)
            readable_text += (
                f"{index_name}: Open={data['Open']}, High={data['High']}, "
                f"Low={data['Low']}, Close={data['Close']}, "
                f"Change={data['Change']} ({data['Change%']}%)\n"
            )
            valid_data_count += 1

    # If no valid data, provide a generic message
    if valid_data_count == 0:
        logger.warning("No valid market data for generating insights")
        return "Market analysis unavailable due to data retrieval issues. Please check back later for updates on Indian market indices."

    # Prompt that specifically asks for 5-6 sentences
    prompt = f"""As a professional financial analyst, provide a comprehensive analysis of the Indian market indices in exactly {sentence_count} sentences. 
Use this data for your analysis:

{readable_text}

Your analysis should cover:
1. Overall market sentiment and major index movements
2. Sector-specific performance (IT, Banking, etc.)
3. Key factors influencing today's market
4. Notable outliers or significant data points
5. Brief market outlook based on today's performance
6. Format as a continuous paragraph or 5-6 points
"""

    try:
        # Initialize Gemini model
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Generate response
        response = model.generate_content(prompt)
        insights_text = response.text.strip()

        return insights_text

    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        return "Market analysis unavailable at this time."


async def generate_concise_insights_async(market_data, sentence_count=6):
    """
    Async version of generate_concise_insights
    """
    return await asyncio.to_thread(
        generate_concise_insights, market_data, sentence_count
    )


def generate_report():
    """
    Generate a complete market report (includes all data with detailed insights)
    """
    all_data = fetch_market_data()
    insights = generate_concise_insights(all_data)

    return {
        "date": all_data["_meta"]["date"],
        "timestamp": all_data["_meta"]["timestamp"],
        "market_data": all_data,
        "insights": insights,
    }


async def generate_report_async():
    """
    Async version of generate_report
    """
    all_data = await fetch_market_data_async()
    insights = await generate_concise_insights_async(all_data)

    return {
        "date": all_data["_meta"]["date"],
        "timestamp": all_data["_meta"]["timestamp"],
        "market_data": all_data,
        "insights": insights,
    }
