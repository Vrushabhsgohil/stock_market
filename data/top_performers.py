import os
import json
import logging
import re
from datetime import datetime
import time
from typing import Dict, List, Any

# Langchain imports
from langchain_google_genai import GoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

# Third party imports
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure logging
# Set up logging with simpler format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            "market_api.log"
        ),  # Added file handler to write to market_api.log
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Only use Trendlyne URLs for gainers and losers
TRENDLYNE_GAINERS_URL = (
    "https://trendlyne.com/stock-screeners/price-based/top-gainers/today/"
)
TRENDLYNE_LOSERS_URL = (
    "https://trendlyne.com/stock-screeners/price-based/top-losers/today/"
)

# Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)


class TopPerformersScraper:
    """Class to scrape market data from Trendlyne and generate insights with Gemini"""

    def __init__(self):
        """Initialize the scraper"""
        self.gemini_llm = None
        if GEMINI_API_KEY:
            try:
                # Updated to use the correct model name - check if it's "gemini-1.5-pro" instead
                self.gemini_llm = GoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    google_api_key=GEMINI_API_KEY,
                    temperature=0.2,
                    max_output_tokens=1024,
                )
                logger.info("Successfully initialized Gemini API")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {str(e)}")
                # Fallback to another model if needed
                try:
                    self.gemini_llm = GoogleGenerativeAI(
                        model="gemini-1.0-pro",
                        google_api_key=GEMINI_API_KEY,
                        temperature=0.2,
                        max_output_tokens=1024,
                    )
                    logger.info(
                        "Successfully initialized Gemini API with fallback model"
                    )
                except Exception as e2:
                    logger.warning(
                        f"Failed to initialize fallback Gemini model: {str(e2)}"
                    )
        else:
            logger.warning(
                "Gemini API key not found. Insights generation will be skipped."
            )

    def get_chrome_driver(self):
        """Set up and return a Chrome driver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--enable-unsafe-swiftshader")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)

    def _parse_price_change(self, text):
        """Parse price change text that contains value and percentage"""
        try:
            # Handle the format like "33.93 (20.0%)" or "-1.24 (-12.4%)"
            match = re.match(r"([-\d.]+)\s+\(([-\d.]+)%?\)", text)
            if match:
                return float(match.group(1))
            # Try direct conversion if no pattern match
            return float(
                text.replace("INR", "").replace(",", "").replace("%", "").strip()
            )
        except Exception as e:
            logger.debug(f"Error parsing price change '{text}': {str(e)}")
            return 0.0

    def _parse_percentage_change(self, text):
        """Parse percentage change text that contains value and percentage"""
        try:
            # Handle the format like "33.93 (20.0%)" or "-1.24 (-12.4%)"
            match = re.match(r"([-\d.]+)\s+\(([-\d.]+)%?\)", text)
            if match:
                return float(match.group(2))
            # Check if it's just a percentage
            if "%" in text:
                return float(text.replace("%", "").strip())
            return float(text)
        except Exception as e:
            logger.debug(f"Error parsing percentage '{text}': {str(e)}")
            return 0.0

    def scrape_trendlyne_data(self, url):
        """Scrape stock data from a Trendlyne URL"""
        driver = self.get_chrome_driver()

        try:
            # Load the URL
            logger.info(f"Loading URL: {url}")
            driver.get(url)

            # Wait for JavaScript to load content
            time.sleep(8)  # Increased wait time

            # Get the page source
            page_source = driver.page_source

            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_source, "html.parser")

            # Find the table with stock data
            table = soup.find("table", class_="table")

            if not table:
                logger.error("Could not find table with stock data")
                return []

            # Extract headers
            headers = []
            header_row = table.find("thead").find("tr")
            for th in header_row.find_all("th"):
                headers.append(th.text.strip())

            # Extract data rows (limited to top 10)
            stocks = []
            tbody = table.find("tbody")
            if tbody:
                count = 0
                for tr in tbody.find_all("tr"):
                    if count >= 10:  # Limit to top 10
                        break

                    row_data = {}

                    # First get all the data using standard method
                    for i, td in enumerate(tr.find_all("td")):
                        if i < len(headers):
                            header_name = headers[i]
                            row_data[header_name] = td.text.strip()

                    # Now, specifically for company name, try to get full version if available
                    first_col = tr.find("td")
                    if first_col:
                        # First, try to get from data attributes which often have the full name
                        company_name = None

                        # Try link with full title
                        link = first_col.find("a")
                        if link:
                            if link.has_attr("data-title"):
                                company_name = link["data-title"].strip()
                            elif link.has_attr("data-original-title"):
                                company_name = link["data-original-title"].strip()
                            elif link.has_attr("title"):
                                company_name = link["title"].strip()

                        # If still no name, try getting from the span
                        if not company_name:
                            span = first_col.find("span")
                            if span and span.has_attr("title"):
                                company_name = span["title"].strip()

                        # If no luck with attributes, get the direct text
                        if not company_name:
                            company_name = first_col.get_text(strip=True)

                        # Save the full company name to the row data
                        if company_name:
                            # Try to get the company name key from headers - usually first column
                            company_key = headers[0] if headers else "Name"
                            row_data[company_key] = company_name

                    # Debug: log raw row data
                    logger.debug(f"Raw row data: {row_data}")

                    # Convert data to our standardized format
                    try:
                        # Get company name from first column
                        company_name = row_data.get(
                            "Name", row_data.get(headers[0], "")
                        )

                        # Find current price (LTP or Last Price)
                        price_key = next(
                            (
                                h
                                for h in row_data.keys()
                                if any(term in h for term in ["LTP", "Price", "Last"])
                            ),
                            None,
                        )
                        if not price_key and headers:
                            price_key = headers[1]  # Fallback to second column

                        price_text = row_data.get(price_key, "0")
                        current_price = float(
                            price_text.replace("INR", "").replace(",", "").strip()
                        )

                        # Find change column
                        change_key = next(
                            (
                                h
                                for h in row_data.keys()
                                if "Change(%)" in h or "Change %" in h
                            ),
                            None,
                        )
                        if not change_key:
                            change_key = next(
                                (h for h in row_data.keys() if "Change" in h), None
                            )

                        if change_key:
                            change_text = row_data.get(change_key, "0 (0%)")
                            price_change = self._parse_price_change(change_text)
                            percentage_change = self._parse_percentage_change(
                                change_text
                            )
                        else:
                            # Fallback values if we can't find change columns
                            price_change = 0.0
                            percentage_change = 0.0

                        # Add to standardized format - use original complete company name
                        stocks.append(
                            {
                                "company_name": company_name,
                                "current_price": current_price,
                                "price_change": price_change,
                                "percentage_change": percentage_change,
                            }
                        )
                        count += 1
                        logger.debug(
                            f"Processed stock: {company_name}, price: {current_price}, change: {price_change}, %: {percentage_change}"
                        )

                    except Exception as e:
                        logger.error(f"Error parsing row data: {str(e)}")
                        logger.error(f"Problematic row: {row_data}")
                        continue

            logger.info(f"Successfully scraped {len(stocks)} stocks from {url}")
            return stocks

        except Exception as e:
            logger.error(f"Error in scrape_trendlyne_data: {str(e)}")
            return []

        finally:
            driver.quit()

    def scrape_top_gainers_losers(self) -> Dict[str, List[Dict[str, Any]]]:
        """Scrape top gainers and losers from Trendlyne"""
        logger.info("Starting to scrape top gainers and losers from Trendlyne")

        # Get top gainers
        top_gainers = self.scrape_trendlyne_data(TRENDLYNE_GAINERS_URL)

        # Get top losers
        top_losers = self.scrape_trendlyne_data(TRENDLYNE_LOSERS_URL)

        # Make sure losers have negative changes
        for loser in top_losers:
            if loser["price_change"] > 0:
                loser["price_change"] = -loser["price_change"]
            if loser["percentage_change"] > 0:
                loser["percentage_change"] = -loser["percentage_change"]

        # Return combined results
        result = {"gainers": top_gainers, "losers": top_losers}

        logger.info(
            f"Completed scraping: {len(top_gainers)} gainers, {len(top_losers)} losers"
        )
        return result

    def generate_market_insights(self, market_data):
        """Generate market insights using Gemini"""
        if not self.gemini_llm:
            return {"error": "Gemini API key not configured or initialization failed"}

        try:
            # Prepare data for analysis
            gainers = market_data.get("top_gainers", [])
            losers = market_data.get("top_losers", [])

            # Create prompt for Gemini with focus on brevity
            prompt_template = PromptTemplate(
                input_variables=["gainers", "losers", "date"],
                template="""
                You are a senior stock market analyst analyzing today's top gainers and losers.
                
                Today's date: {date}
                
                Top Gainers:
                {gainers}
                
                Top Losers:
                {losers}
                
                Based on the above data, provide exactly 5 concise, professional insights formatted as bullet points.
                
                Guidelines:
                - Format each point with a dash (-) at the beginning
                - Each bullet point should be one complete, professional sentence
                - Cover both gainers and losers in your analysis
                - Mention specific company names when relevant
                - Identify potential sector or market-wide trends
                - Focus on actionable insights for investors
                - Use formal, professional financial language
                - Do not use bold, italic or any other formatting
                
                Your entire response should just be the 5 bullet points with no additional text.
                """,
            )

            # Format data for prompt
            gainers_text = (
                "\n".join(
                    [
                        f"- {g['company_name']}: Current price INR{g['current_price']:.2f}, Change: +INR{g['price_change']:.2f} (+{g['percentage_change']:.2f}%)"
                        for g in gainers
                    ]
                )
                if gainers
                else "No data available"
            )

            losers_text = (
                "\n".join(
                    [
                        f"- {l['company_name']}: Current price INR{l['current_price']:.2f}, Change: INR{l['price_change']:.2f} ({l['percentage_change']:.2f}%)"
                        for l in losers
                    ]
                )
                if losers
                else "No data available"
            )

            # Create chain
            chain = LLMChain(llm=self.gemini_llm, prompt=prompt_template)

            # Run chain
            current_date = datetime.now().strftime("%Y-%m-%d")
            raw_insights = chain.run(
                {"gainers": gainers_text, "losers": losers_text, "date": current_date}
            )

            # Process the insights to ensure proper bullet point format
            lines = raw_insights.split("\n")
            clean_insights = []

            for line in lines:
                line = line.strip()
                if line and not line.isspace():
                    # Skip header lines or empty lines
                    if any(
                        x in line.lower()
                        for x in ["insight", "here", "following", "bullet"]
                    ):
                        continue

                    # Ensure each line starts with a dash
                    if not line.startswith("-"):
                        if line.startswith("*") or line.startswith("•"):
                            line = "- " + line[1:].strip()
                        else:
                            line = "- " + line

                    clean_insights.append(line)

            # Join with newlines for better readability
            final_insights = "\n".join(clean_insights[:5])

            return {"insights": final_insights}

        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return {"error": f"Failed to generate insights: {str(e)}"}

    def run_full_scrape(self):
        """Run complete market data scraping and return combined JSON"""
        try:
            # Timestamp for data
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Scrape top gainers and losers
            logger.info("Starting market data scraping...")
            market_movers = self.scrape_top_gainers_losers()

            # Compile market data
            market_data = {
                "timestamp": timestamp,
                "top_gainers": market_movers["gainers"],
                "top_losers": market_movers["losers"],
            }

            # Generate insights if Gemini is configured
            insights_message = "No insights generated"
            if self.gemini_llm:
                logger.info("Generating market insights with Gemini...")
                insights_result = self.generate_market_insights(market_data)

                if "insights" in insights_result:
                    insights_message = insights_result["insights"]
                elif "error" in insights_result:
                    insights_message = (
                        f"Error generating insights: {insights_result['error']}"
                    )
            else:
                insights_message = (
                    "Insights generation skipped - Gemini API key not configured"
                )

            # Add insights to market data
            market_data["insights"] = insights_message

            return market_data

        except Exception as e:
            logger.error(f"Error in market scrape: {str(e)}")
            # Return partial data if available
            return {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error": str(e),
                "top_gainers": [],
                "top_losers": [],
                "insights": "Failed to generate due to error",
            }
