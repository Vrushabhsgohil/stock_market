import os
import json
import yfinance as yf
import ta
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time
from yfinance.exceptions import YFRateLimitError
import logging
import asyncio

# Set up logging with simpler format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("market_api.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)
# --- Load environment variables ---
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY is not set in environment variables.")
    raise RuntimeError("GEMINI_API_KEY is not set in environment variables.")

# --- Setup Gemini Client (Using gemini-2.0-flash) ---
logger.info("Configuring Gemini API client")
genai.configure(api_key=GEMINI_API_KEY)
gemini_client = genai.GenerativeModel(
    model_name="gemini-2.0-flash-001",
    generation_config={
        "temperature": 0.2,
        "max_output_tokens": 1024,
    },
)

# --- Constants ---
INDICES = {
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN",
    "Nifty Bank": "^NSEBANK",
    "Nifty IT": "^CNXIT",
    "Nifty FMCG": "^CNXFMCG",
}


# --- Utility Functions ---
def get_previous_trading_day():
    today = datetime.now()
    previous_day = today - timedelta(days=1)
    while previous_day.weekday() >= 5:  # Skip Saturday and Sunday
        previous_day -= timedelta(days=1)
    return previous_day.strftime("%B %d, %Y")


def fetch_technical_snapshot():
    """Fetch technical data for Indian indices."""
    logger.info("Fetching technical snapshot for indices")
    snapshot = {}
    for name, symbol in INDICES.items():
        logger.info(f"Processing {name} ({symbol})")
        ticker = yf.Ticker(symbol)
        try:
            logger.info(f"Fetching 6-month history for {symbol}")
            hist = ticker.history(period="6mo", interval="1d")
        except YFRateLimitError:
            logger.error("Yahoo Finance rate limit reached")
            raise RuntimeError(
                "Too Many Requests to Yahoo Finance. Please try again later."
            )
        if hist.empty or len(hist) < 50:
            logger.warning(f"Insufficient data for {symbol}, skipping")
            continue

        close = hist["Close"]
        snapshot[name] = {
            "close": round(close.iloc[-1], 2),
            "support": round(close.tail(20).min(), 2),
            "rsi": round(ta.momentum.RSIIndicator(close=close).rsi().iloc[-1], 2),
            "macd": {
                "line": round(ta.trend.MACD(close=close).macd().iloc[-1], 2),
                "signal": round(ta.trend.MACD(close=close).macd_signal().iloc[-1], 2),
            },
        }
        logger.info(
            f"Successfully processed {name} with close price {snapshot[name]['close']}"
        )
        time.sleep(1)  # Add a 1-second delay between requests

    logger.info(f"Completed technical snapshot with {len(snapshot)} indices")
    return snapshot


async def fetch_technical_snapshot_async():
    """Async version of fetch_technical_snapshot."""
    # Use a thread pool to run the synchronous function
    return await asyncio.to_thread(fetch_technical_snapshot)


def generate_insights(snapshot_data: dict):
    """Send snapshot data to Gemini and receive financial insights."""
    logger.info("Generating insights from technical snapshot")
    prompt = f"""
    You are a professional financial analyst.
    Analyze the following JSON data on Indian stock market indices. Generate 6-7 concise insights.
    
    Guidelines:
    - Each insight must be one sentence maximum
    - Focus on clear market implications
    - Identify key technical patterns and their significance
    - Mention support/resistance levels when relevant
    - Highlight overbought/oversold conditions
    - Note any divergences or unusual patterns
    - Provide actionable insights for traders/investors
    
    Input Data:
    {json.dumps(snapshot_data, indent=2)}
    
    Output:
    - Exactly 6-7 bullet points
    - Each point < 15 words
    - Professional, formal tone
    - No extra explanations
    - Focus on actionable insights
    """

    try:
        logger.info("Sending request to Gemini API")
        response = gemini_client.generate_content(prompt)
        insights_text = response.text.strip()
        logger.info("Successfully received response from Gemini API")

        # Clean and split insights
        insights = [
            line.lstrip("-* ").strip()
            for line in insights_text.splitlines()
            if line.strip()
            and not any(x in line.lower() for x in ["insight", "below", "here"])
        ]
        logger.info(f"Generated {len(insights)} market insights")
        return insights
    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        raise


async def generate_insights_async(snapshot_data: dict):
    """Async version of generate_insights."""
    return await asyncio.to_thread(generate_insights, snapshot_data)


def get_market_technical_snapshot():
    """Main function to get technical snapshot and insights."""
    logger.info("Starting market technical snapshot process")
    try:
        snapshot = fetch_technical_snapshot()
        if not snapshot:
            logger.error("No stock data available")
            raise RuntimeError("No stock data available.")

        insights = generate_insights(snapshot)
        result = {
            "date": get_previous_trading_day(),
            "snapshot": snapshot,
            "insights": insights,
        }
        logger.info("Successfully completed market technical snapshot")
        return result
    except Exception as e:
        logger.error(f"Error in get_market_technical_snapshot: {str(e)}")
        raise


async def get_market_technical_snapshot_async():
    """Async version of get_market_technical_snapshot."""
    logger.info("Starting async market technical snapshot process")
    try:
        snapshot = await fetch_technical_snapshot_async()
        if not snapshot:
            logger.error("No stock data available")
            raise RuntimeError("No stock data available.")

        insights = await generate_insights_async(snapshot)
        result = {
            "date": get_previous_trading_day(),
            "snapshot": snapshot,
            "insights": insights,
        }
        logger.info("Successfully completed async market technical snapshot")
        return result
    except Exception as e:
        logger.error(f"Error in get_market_technical_snapshot_async: {str(e)}")
        raise
