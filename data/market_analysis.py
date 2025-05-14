from langchain_google_genai import GoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import os
import json
from typing import Dict, Any
from datetime import datetime, timedelta
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import logging

# Configure logging - Updated to use market_api.log for consistency
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(
            "market_api.log"
        ),  # Changed from market_analysis.log to market_api.log
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(
    "market_analysis"
)  # Keep unique logger name for component identification

# --- Load environment variables ---
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in environment variables.")

# --- Setup Gemini Client (Using gemini-2.0-flash) ---
genai.configure(api_key=GEMINI_API_KEY)
gemini_client = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={
        "temperature": 0.2,
        "max_output_tokens": 1024,
    },
)

# --- Constants ---
INDICES = {
    "Nifty 50": "^NSEI",
}


class MarketAnalysisGenerator:
    """
    Class to generate comprehensive market analysis and summary using Google's Gemini AI.
    """

    def __init__(self, api_key=None):
        """Initialize with API key."""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key is required")

        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        logger.info("MarketAnalysisGenerator initialized successfully")

    def _extract_key_data_points(self, market_data):
        """
        Extract key data points from the comprehensive market data
        to include in the prompt for analysis.
        """
        key_data = {}

        # Extract sector movement data
        if (
            "sector_and_fii" in market_data
            and "sector_movement" in market_data["sector_and_fii"]
        ):
            sector_data = market_data["sector_and_fii"]["sector_movement"].get(
                "data", []
            )
            key_data["sector_movement"] = "\n".join(
                [
                    f"- {s['sector_name']}: {s['change_percentage']:.2f}% change, {s['advances']} advances, {s['declines']} declines"
                    for s in sector_data[:5]
                ]
            )
            key_data["sector_insight"] = market_data["sector_and_fii"][
                "sector_movement"
            ].get("insight", "")

        # Extract FII/DII data
        if (
            "sector_and_fii" in market_data
            and "institutional_activity" in market_data["sector_and_fii"]
        ):
            inst_data = market_data["sector_and_fii"]["institutional_activity"].get(
                "data", {}
            )
            key_data["fii_activity"] = (
                f"FII: Buy {inst_data.get('fii', {}).get('buy_value', 0)} Cr, Sell {inst_data.get('fii', {}).get('sell_value', 0)} Cr, Net {inst_data.get('fii', {}).get('net_value', 0)} Cr"
            )
            key_data["dii_activity"] = (
                f"DII: Buy {inst_data.get('dii', {}).get('buy_value', 0)} Cr, Sell {inst_data.get('dii', {}).get('sell_value', 0)} Cr, Net {inst_data.get('dii', {}).get('net_value', 0)} Cr"
            )
            key_data["institutional_insight"] = market_data["sector_and_fii"][
                "institutional_activity"
            ].get("insight", "")

        # Extract news highlights - just titles
        if "news_highlights" in market_data:
            key_data["impact_news"] = market_data["news_highlights"].get(
                "impact_news", ""
            )
            key_data["india_news"] = market_data["news_highlights"].get(
                "india_news", ""
            )
            key_data["global_news"] = market_data["news_highlights"].get(
                "global_news", ""
            )

        # Extract financial indicators
        if (
            "financial_indicators" in market_data
            and "indicators" in market_data["financial_indicators"]
        ):
            indicators = market_data["financial_indicators"]["indicators"]
            key_data["financial_indicators"] = "\n".join(
                [
                    f"- {name}: {indicator.get('value', 'N/A')} ({indicator.get('percent_change', 'N/A')})"
                    for name, indicator in indicators.items()
                    if name != "_insights"
                ]
            )
            # If there are insights available for financial indicators
            if "_insights" in indicators:
                key_data["financial_indicators_insight"] = indicators["_insights"].get(
                    "value", ""
                )

        # Extract market snapshot data
        if (
            "market_snapshot" in market_data
            and "snapshot" in market_data["market_snapshot"]
        ):
            snapshot = market_data["market_snapshot"]["snapshot"]
            key_data["market_snapshot"] = "\n".join(
                [
                    f"- {index}: Close {data.get('close', 'N/A')}, RSI {data.get('rsi', 'N/A')}"
                    for index, data in snapshot.items()
                ]
            )
            key_data["market_snapshot_insight"] = market_data["market_snapshot"].get(
                "insights", ""
            )

        # Extract market overview
        if (
            "market_overview" in market_data
            and "market_data" in market_data["market_overview"]
        ):
            market_indices = market_data["market_overview"]["market_data"]
            # Exclude meta information
            market_indices_filtered = {
                k: v for k, v in market_indices.items() if k != "_meta"
            }

            key_data["market_indices"] = "\n".join(
                [
                    f"- {k}: Close {v.get('Close', 'N/A')}, Change {v.get('Change%', 'N/A')}%"
                    for k, v in market_indices_filtered.items()
                ]
            )
            key_data["market_overview_insight"] = market_data["market_overview"].get(
                "insights", ""
            )

        # Extract top performers
        if "top_performers" in market_data:
            # Top gainers
            top_gainers = market_data["top_performers"].get("top_gainers", [])
            if top_gainers:
                key_data["top_gainers"] = "\n".join(
                    [
                        f"- {g['company_name']}: {g['percentage_change']}% (₹{g['current_price']})"
                        for g in top_gainers[:3]
                    ]
                )

            # Top losers
            top_losers = market_data["top_performers"].get("top_losers", [])
            if top_losers:
                key_data["top_losers"] = "\n".join(
                    [
                        f"- {l['company_name']}: {l['percentage_change']}% (₹{l['current_price']})"
                        for l in top_losers[:3]
                    ]
                )

            key_data["top_performers_insight"] = market_data["top_performers"].get(
                "insight", ""
            )

        return key_data

    def generate_market_analysis(self, market_data):
        """
        Generate comprehensive market analysis based on all available data.
        """
        try:
            # Extract key data for the prompt
            key_data = self._extract_key_data_points(market_data)

            # Create the prompt
            prompt = f"""
            As a senior market analyst, provide a comprehensive analysis of the Indian stock market based on the following data:
            
            === SECTOR MOVEMENT ===
            {key_data.get('sector_movement', 'No data available')}
            
            === INSTITUTIONAL ACTIVITY ===
            {key_data.get('fii_activity', 'No data available')}
            {key_data.get('dii_activity', 'No data available')}
            
            === KEY MARKET INDICES ===
            {key_data.get('market_indices', 'No data available')}
            
            === TECHNICAL INDICATORS ===
            {key_data.get('market_snapshot', 'No data available')}
            
            === FINANCIAL INDICATORS ===
            {key_data.get('financial_indicators', 'No data available')}
            
            === TOP GAINERS ===
            {key_data.get('top_gainers', 'No data available')}
            
            === TOP LOSERS ===
            {key_data.get('top_losers', 'No data available')}
            
            === IMPACT NEWS HIGHLIGHTS ===
            {key_data.get('impact_news', 'No data available')}
            
            === INDIA NEWS HIGHLIGHTS ===
            {key_data.get('india_news', 'No data available')}
            
            Based on the data above, provide exactly 8-9 concise bullet points covering:
            1. Overall market sentiment and trend
            2. Key sector performance and rotation
            3. Institutional activity impact
            4. Technical outlook and indicators
            5. Global/local factors affecting the market
            6. Key investment themes and opportunities
            7. Potential risks and concerns
            8. Market breadth and participation
            9. Liquidity and volume analysis
            
            Guidelines:
            - Each bullet point must be a single, clear sentence
            - Start each point with a dash (-)
            - Be specific and quantitative where possible
            - Focus on actionable insights
            - Keep each point under 20 words
            - Use professional, formal tone
            """

            # Call Gemini model
            response = self.model.generate_content(prompt)
            analysis_text = response.text.strip()

            # Process the response to ensure proper bullet point formatting
            lines = analysis_text.split("\n")
            clean_lines = []

            for line in lines:
                line = line.strip()
                if line and not line.isspace():
                    # Skip header lines or empty lines
                    if any(
                        x in line.lower()
                        for x in ["analysis", "here", "following", "bullet"]
                    ):
                        continue

                    # Ensure each line starts with a dash
                    if not line.startswith("-"):
                        if line.startswith("*") or line.startswith("•"):
                            line = "- " + line[1:].strip()
                        else:
                            line = "- " + line

                    clean_lines.append(line)

            # Join with newlines for better readability
            final_analysis = "\n".join(clean_lines[:9])  # Limit to 9 points

            return final_analysis

        except Exception as e:
            logger.error(f"Error generating market analysis: {str(e)}")
            return f"Error generating market analysis: {str(e)}"

    def generate_market_summary(self, market_data, market_analysis):
        """
        Generate a concise market summary based on all the data and previously generated analysis.
        """
        try:
            # Create the prompt
            prompt = f"""
            Based on this market analysis:
            
            {market_analysis}
            
            Provide exactly 8-9 key takeaways for investors.
            
            Guidelines:
            - Each point must be a single, clear sentence
            - Start each point with a dash (-)
            - Focus on the most important actionable insights
            - Keep each point under 15 words
            - Be specific about what investors should do or watch
            - Cover both opportunities and risks
            - Include specific levels or targets where relevant
            - Use professional, formal tone
            """

            # Call Gemini model
            response = self.model.generate_content(prompt)
            summary_text = response.text.strip()

            # Process the response to ensure proper bullet point formatting
            lines = summary_text.split("\n")
            clean_lines = []

            for line in lines:
                line = line.strip()
                if line and not line.isspace():
                    # Skip header lines or empty lines
                    if any(
                        x in line.lower()
                        for x in ["summary", "takeaway", "here", "following"]
                    ):
                        continue

                    # Ensure each line starts with a dash
                    if not line.startswith("-"):
                        if line.startswith("*") or line.startswith("•"):
                            line = "- " + line[1:].strip()
                        else:
                            line = "- " + line

                    clean_lines.append(line)

            # Join with newlines for better readability
            final_summary = "\n".join(clean_lines[:9])  # Limit to 9 points

            return final_summary

        except Exception as e:
            logger.error(f"Error generating market summary: {str(e)}")
            return f"Error generating market summary: {str(e)}"

    def generate_market_prediction(self, market_data, market_analysis):
        """
        Generate a prediction for the next trading day based on current market data and analysis.
        """
        try:
            # Extract key data for the prediction prompt
            key_data = self._extract_key_data_points(market_data)

            # Create the prompt for market prediction
            prompt = f"""
                You are a senior financial market strategist.

                Using the market analysis below:

                {market_analysis}

                Generate exactly 8–9 **distinct and professional** predictions for the next trading day.

                **Output Format:**
                - Each prediction must be a single bullet point starting with a dash (-)
                - Each point should be a **clear, precise, and standalone insight**
                - Include a **brief rationale** (e.g., technical level, macro factor, sentiment driver)
                - Use **specific data** such as index levels, percentage changes, or price zones
                - Ensure predictions are **not repetitive** — each must cover a unique asset, sector, or angle
                - Cover both **upside and downside** possibilities
                - Address **major indices** (S&P 500, Nasdaq, Dow) and key sectors (tech, financials, energy, etc.)
                - Keep each prediction **under 35 words**
                - Maintain a **formal, analytical tone** used by institutional analysts

                The final output should be a clean, professional list of 10-12 forward-looking insights.
            """

            # Call Gemini model
            response = self.model.generate_content(prompt)
            prediction_text = response.text.strip()

            # Process the response to ensure proper bullet point formatting
            lines = prediction_text.split("\n")
            clean_lines = []

            for line in lines:
                line = line.strip()
                if line and not line.isspace():
                    # Skip header lines or empty lines
                    if any(
                        x in line.lower()
                        for x in ["prediction", "forecast", "here", "following"]
                    ):
                        continue

                    # Ensure each line starts with a dash
                    if not line.startswith("-"):
                        if line.startswith("*") or line.startswith("•"):
                            line = "- " + line[1:].strip()
                        else:
                            line = "- " + line

                    clean_lines.append(line)

            # Join with newlines for better readability
            final_prediction = "\n".join(clean_lines[:9])  # Limit to 9 points

            return final_prediction

        except Exception as e:
            logger.error(f"Error generating market prediction: {str(e)}")
            return f"Error generating market prediction: {str(e)}"
