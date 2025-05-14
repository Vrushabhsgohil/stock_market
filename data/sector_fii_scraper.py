import os
import logging
from typing import Dict, List, Any
from datetime import datetime
import time

# Third party imports
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import google.generativeai as genai
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

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

# Set up Gemini API for insights generation
gemini_api_key = os.environ.get("GEMINI_API_KEY")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables")

# Define URLs for scraping - Only using Trendlyne for sector data
SECTOR_URLS = [
    "https://trendlyne.com/equity/sector-industry-analysis/sector/day/",
]

# FII/DII URLs
FII_DII_URLS = [
    "https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/index.php",
    "https://trendlyne.com/macro-data/fii-dii/latest/cash-pastmonth/",
]

# Standard sector classification
STANDARD_SECTORS = [
    "Information Technology",
    "Banking & Financial Services",
    "Pharmaceuticals & Healthcare",
    "Energy",
    "FMCG",
    "Automobiles",
    "Realty",
    "Infrastructure",
    "Metals and Mining",
    "Telecom",
    "Agriculture and Chemicals",
]


class MarketDataScraper:
    """Class to scrape market data from various financial websites"""

    def __init__(self):
        """Initialize the scraper with Chrome options"""
        self.chrome_options = self._setup_chrome_options()

    def _setup_chrome_options(self) -> Options:
        """Set up Chrome options for Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # Use new headless mode
        chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
        chrome_options.add_argument(
            "--disable-dev-shm-usage"
        )  # Overcome limited resource problems
        chrome_options.add_argument(
            "--disable-gpu"
        )  # Disable GPU hardware acceleration
        chrome_options.add_argument(
            "--disable-software-rasterizer"
        )  # Disable software rasterizer
        chrome_options.add_argument("--disable-webgl")  # Disable WebGL
        chrome_options.add_argument("--disable-webgl2")  # Disable WebGL 2.0
        chrome_options.add_argument("--disable-gpu-sandbox")  # Disable GPU sandbox
        chrome_options.add_argument("--window-size=1920,1080")  # Set window size
        chrome_options.add_argument("--disable-notifications")  # Disable notifications
        chrome_options.add_argument("--disable-extensions")  # Disable extensions
        chrome_options.add_argument("--disable-infobars")  # Disable infobars
        chrome_options.add_argument("--disable-web-security")  # Disable web security
        chrome_options.add_argument(
            "--disable-features=IsolateOrigins,site-per-process"
        )  # Disable site isolation
        chrome_options.add_argument(
            "--disable-site-isolation-trials"
        )  # Disable site isolation trials
        chrome_options.add_argument(
            "--disable-background-networking"
        )  # Disable background networking
        chrome_options.add_argument(
            "--disable-background-timer-throttling"
        )  # Disable background timer throttling
        chrome_options.add_argument(
            "--disable-backgrounding-occluded-windows"
        )  # Disable backgrounding of occluded windows
        chrome_options.add_argument("--disable-breakpad")  # Disable crash reporting
        chrome_options.add_argument(
            "--disable-component-extensions-with-background-pages"
        )  # Disable component extensions
        chrome_options.add_argument(
            "--disable-features=TranslateUI"
        )  # Disable translate UI
        chrome_options.add_argument(
            "--disable-ipc-flooding-protection"
        )  # Disable IPC flooding protection
        chrome_options.add_argument(
            "--disable-renderer-backgrounding"
        )  # Disable renderer backgrounding
        chrome_options.add_argument(
            "--enable-features=NetworkService,NetworkServiceInProcess"
        )  # Enable network service
        chrome_options.add_argument("--force-color-profile=srgb")  # Force color profile
        chrome_options.add_argument("--metrics-recording-only")  # Only record metrics
        chrome_options.add_argument("--mute-audio")  # Mute audio
        chrome_options.add_argument(
            "--disable-popup-blocking"
        )  # Disable popup blocking
        chrome_options.add_argument(
            "--ignore-certificate-errors"
        )  # Ignore certificate errors
        chrome_options.add_argument(
            "--allow-running-insecure-content"
        )  # Allow running insecure content
        chrome_options.add_argument(
            "--disable-blink-features=AutomationControlled"
        )  # Disable automation control
        chrome_options.add_argument("--disable-shared-images")  # Disable shared images
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        return chrome_options

    def _create_driver(self):
        """Create and return a new WebDriver instance"""
        return webdriver.Chrome(options=self.chrome_options)

    def _map_to_standard_sector(self, sector_name: str) -> str:
        """Map scraped sector names to standard sector names"""
        sector_name = sector_name.lower()

        # Map sector names to standard sectors
        if any(
            term in sector_name for term in ["it", "software", "tech", "information"]
        ):
            return "Information Technology"
        elif any(
            term in sector_name for term in ["bank", "finance", "financial", "nbfc"]
        ):
            return "Banking & Financial Services"
        elif any(
            term in sector_name for term in ["pharma", "health", "medical", "drug"]
        ):
            return "Pharmaceuticals & Healthcare"
        elif any(
            term in sector_name for term in ["energy", "oil", "gas", "petrol", "power"]
        ):
            return "Energy"
        elif any(term in sector_name for term in ["fmcg", "consumer goods"]):
            return "FMCG"
        elif any(term in sector_name for term in ["auto", "automobile", "vehicle"]):
            return "Automobiles"
        elif any(term in sector_name for term in ["real estate", "realty", "property"]):
            return "Realty"
        elif any(term in sector_name for term in ["infra", "construction", "cement"]):
            return "Infrastructure"
        elif any(
            term in sector_name for term in ["metal", "steel", "mining", "mineral"]
        ):
            return "Metals and Mining"
        elif any(term in sector_name for term in ["telecom", "communication"]):
            return "Telecom"
        elif any(term in sector_name for term in ["agri", "chemical", "fertilizer"]):
            return "Agriculture and Chemicals"

        # If no mapping found, return the original name
        return sector_name.title()

    def scrape_sector_data(self) -> List[Dict[str, Any]]:
        """Scrape sector-wise movement data from Trendlyne"""
        sector_dict = {}  # To track unique sectors
        sources_successful = []

        # Use Trendlyne URL
        url = SECTOR_URLS[0]
        driver = self._create_driver()

        try:
            logger.info(f"Scraping sector data from Trendlyne")
            driver.get(url)
            driver.implicitly_wait(10)

            # Add a longer sleep for initial page load
            time.sleep(5)  # Give the page time to fully load

            # Extract table data
            soup = BeautifulSoup(driver.page_source, "html.parser")

            self._process_trendlyne_sector(soup, sector_dict, sources_successful)

        except Exception as e:
            logger.error(f"Error in sector scraping for {url}: {str(e)}")
        finally:
            driver.quit()

        # Convert dictionary to list
        sector_data = list(sector_dict.values())

        # Sort sectors by change percentage (from highest to lowest)
        sector_data.sort(key=lambda x: x["change_percentage"], reverse=True)

        # Limit to top 11 sectors
        sector_data = sector_data[:11]

        logger.info(f"Scraped sector data from Trendlyne: {len(sector_data)} sectors")
        logger.info(f"Successful sources: {sources_successful}")

        return sector_data

    def _process_trendlyne_sector(self, soup, sector_dict, sources_successful):
        """Process sector data from Trendlyne"""
        # Try various selectors
        selectors = [
            ".table-responsive table",
            ".dataTables_wrapper table",
            ".table",
            "#sectors-table",
        ]

        for selector in selectors:
            table = soup.select_one(selector)

            if table:
                rows = (
                    table.select("tbody tr")
                    if table.select_one("tbody")
                    else table.select("tr")
                )
                sectors_found = 0

                for row in rows:
                    try:
                        cols = row.select("td")
                        if len(cols) >= 5:
                            sector_name = cols[0].text.strip()
                            mapped_sector = self._map_to_standard_sector(sector_name)

                            # Extract data
                            try:
                                change_pct = float(
                                    cols[1].text.strip().replace("%", "")
                                )
                                advances = int(cols[3].text.strip())
                                declines = int(cols[4].text.strip())
                                num_companies = advances + declines

                                sector_dict[mapped_sector] = {
                                    "sector_name": mapped_sector,
                                    "num_companies": num_companies,
                                    "advances": advances,
                                    "declines": declines,
                                    "change_percentage": change_pct,
                                    "source": "Trendlyne",
                                }
                                sectors_found += 1
                            except Exception as e:
                                logger.error(f"Error parsing Trendlyne row: {str(e)}")
                                continue
                    except Exception as e:
                        logger.error(f"Error processing Trendlyne row: {str(e)}")
                        continue

                if sectors_found > 0:
                    sources_successful.append("Trendlyne")
                    logger.info(
                        f"Successfully scraped {sectors_found} sectors from Trendlyne using selector {selector}"
                    )
                    return True

        return False

    def scrape_institutional_data(self) -> Dict[str, Any]:
        """Scrape FII/DII activity data from multiple sources"""
        all_institutional_data = []
        sources_successful = []

        # Try all institutional data URLs
        for url in FII_DII_URLS:
            driver = self._create_driver()
            try:
                source_name = url.split("//")[1].split(".")[1].capitalize()
                logger.info(f"Scraping institutional data from {source_name}")
                driver.get(url)
                driver.implicitly_wait(10)

                # Add a longer sleep for initial page load
                time.sleep(5)  # Give the page time to fully load

                # Extract data
                soup = BeautifulSoup(driver.page_source, "html.parser")

                if "moneycontrol.com" in url:
                    self._process_moneycontrol_institutional(
                        soup, all_institutional_data, sources_successful
                    )
                elif "trendlyne.com" in url:
                    self._process_trendlyne_institutional(
                        soup, all_institutional_data, sources_successful
                    )

            except Exception as e:
                logger.error(
                    f"Error in institutional data scraping for {url}: {str(e)}"
                )
            finally:
                driver.quit()

        # Combine/average institutional data from multiple sources if available
        if all_institutional_data:
            combined_data = {
                "fii": {"buy_value": 0, "sell_value": 0, "net_value": 0},
                "dii": {"buy_value": 0, "sell_value": 0, "net_value": 0},
                "source": ", ".join(sources_successful),
            }

            for data in all_institutional_data:
                combined_data["fii"]["buy_value"] += data["fii"]["buy_value"]
                combined_data["fii"]["sell_value"] += data["fii"]["sell_value"]
                combined_data["fii"]["net_value"] += data["fii"]["net_value"]
                combined_data["dii"]["buy_value"] += data["dii"]["buy_value"]
                combined_data["dii"]["sell_value"] += data["dii"]["sell_value"]
                combined_data["dii"]["net_value"] += data["dii"]["net_value"]

            # Average the values
            num_sources = len(all_institutional_data)
            combined_data["fii"]["buy_value"] /= num_sources
            combined_data["fii"]["sell_value"] /= num_sources
            combined_data["fii"]["net_value"] /= num_sources
            combined_data["dii"]["buy_value"] /= num_sources
            combined_data["dii"]["sell_value"] /= num_sources
            combined_data["dii"]["net_value"] /= num_sources

            logger.info(f"Combined institutional data from {num_sources} sources")
            return combined_data
        else:
            logger.warning("No institutional data could be scraped from any source")
            return {
                "fii": {"buy_value": 0, "sell_value": 0, "net_value": 0},
                "dii": {"buy_value": 0, "sell_value": 0, "net_value": 0},
                "source": "No data available",
            }

    def _process_moneycontrol_institutional(
        self, soup, all_institutional_data, sources_successful
    ):
        """Process institutional data from MoneyControl"""
        # Try various selectors
        selectors = [".mctable1", "table.mctable", "#fii-dii-table", ".data-table"]

        for selector in selectors:
            tables = soup.select(selector)

            if tables and len(tables) >= 1:
                table = tables[0]
                rows = table.select("tr")

                # Extract latest data (typically first or second row)
                for row_idx in range(1, min(3, len(rows))):
                    try:
                        cols = rows[row_idx].select("td")
                        if len(cols) >= 6:  # Minimum columns needed
                            # Extract values
                            values = []
                            for col in cols:
                                text = col.text.strip().replace(",", "")
                                try:
                                    values.append(float(text))
                                except:
                                    pass

                            if len(values) >= 6:  # Need at least 6 numeric values
                                institutional_data = {
                                    "fii": {
                                        "buy_value": values[0],
                                        "sell_value": values[1],
                                        "net_value": (
                                            values[2]
                                            if len(values) > 2
                                            else values[0] - values[1]
                                        ),
                                    },
                                    "dii": {
                                        "buy_value": values[3],
                                        "sell_value": values[4],
                                        "net_value": (
                                            values[5]
                                            if len(values) > 5
                                            else values[3] - values[4]
                                        ),
                                    },
                                    "source": "MoneyControl",
                                }
                                all_institutional_data.append(institutional_data)
                                sources_successful.append("MoneyControl")
                                logger.info(
                                    f"Successfully scraped institutional data from MoneyControl using selector {selector}"
                                )
                                return True
                    except Exception as e:
                        logger.error(
                            f"Error extracting MoneyControl institutional data row: {str(e)}"
                        )
                        continue

        return False

    def _process_trendlyne_institutional(
        self, soup, all_institutional_data, sources_successful
    ):
        """Process institutional data from Trendlyne"""
        # Try various selectors
        selectors = [
            ".table",
            ".data-table",
            "#fii-dii-data",
            ".table-responsive table",
        ]

        for selector in selectors:
            table = soup.select_one(selector)

            if table:
                rows = (
                    table.select("tbody tr")
                    if table.select_one("tbody")
                    else table.select("tr")
                )

                # First row should have latest data
                if rows and len(rows) > 0:
                    try:
                        # Target first data row (skip header if exists)
                        target_row = rows[1] if len(rows) > 1 else rows[0]
                        cols = target_row.select("td")

                        # Look for numeric values
                        values = []
                        for col in cols:
                            text = col.text.strip().replace(",", "").replace("INR", "")
                            try:
                                values.append(float(text))
                            except:
                                pass

                        if len(values) >= 6:  # Need at least 6 numeric values
                            institutional_data = {
                                "fii": {
                                    "buy_value": values[0],
                                    "sell_value": values[1],
                                    "net_value": (
                                        values[2]
                                        if len(values) > 2
                                        else values[0] - values[1]
                                    ),
                                },
                                "dii": {
                                    "buy_value": values[3],
                                    "sell_value": values[4],
                                    "net_value": (
                                        values[5]
                                        if len(values) > 5
                                        else values[3] - values[4]
                                    ),
                                },
                                "source": "Trendlyne",
                            }
                            all_institutional_data.append(institutional_data)
                            sources_successful.append("Trendlyne")
                            logger.info(
                                f"Successfully scraped institutional data from Trendlyne using selector {selector}"
                            )
                            return True
                    except Exception as e:
                        logger.error(
                            f"Error extracting Trendlyne institutional data: {str(e)}"
                        )

        return False


def generate_market_insights(sector_data, institutional_data):
    """Generate market insights using Gemini AI based on scraped data"""
    if not gemini_api_key:
        logger.warning("Cannot generate insights: GEMINI_API_KEY not available")
        return "Market insights not available (API key missing)"

    try:
        # Format sector data for prompt
        sector_summary = "\n".join(
            [
                f"- {s['sector_name']}: {s['change_percentage']:.2f}% change, {s['advances']} advances, {s['declines']} declines"
                for s in sector_data[:5]
            ]
        )

        # Format institutional data for prompt
        fii_summary = f"FII: Buy INR{institutional_data['fii']['buy_value']:.2f} Cr, Sell INR{institutional_data['fii']['sell_value']:.2f} Cr, Net INR{institutional_data['fii']['net_value']:.2f} Cr"
        dii_summary = f"DII: Buy INR{institutional_data['dii']['buy_value']:.2f} Cr, Sell INR{institutional_data['dii']['sell_value']:.2f} Cr, Net INR{institutional_data['dii']['net_value']:.2f} Cr"

        # Create the prompt
        prompt = f"""
        Based on the following market data, provide a concise market insight:
        
        Top 5 Sector Movements:
        {sector_summary}
        
        Institutional Activity:
        {fii_summary}
        {dii_summary}
        
        Please analyze this data and provide exactly 6-7 bullet points that cover:
        1. Overall market sentiment and trend
        2. Key sector performance and implications
        3. Institutional activity analysis
        4. Market breadth and participation
        5. Potential catalysts or risks
        6. Short-term market outlook
        7. Key takeaways for investors
        
        Guidelines:
        - Each point must be one sentence maximum
        - Focus on actionable insights
        - Use professional, formal tone
        - Avoid generic statements
        - Highlight key market implications
        """

        # Generate insights using Gemini
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

        return response.text

    except Exception as e:
        logger.error(f"Error generating market insights: {str(e)}")
        return f"Market insights generation failed: {str(e)}"


def generate_sector_insights(sector_data):
    """Generate concise bullet-point insights for sector performance"""
    if not gemini_api_key:
        logger.warning("Cannot generate sector insights: GEMINI_API_KEY not available")
        return "Sector insights not available (API key missing)"

    try:
        # Format sector data for prompt
        sector_summary = "\n".join(
            [
                f"- {s['sector_name']}: {s['change_percentage']:.2f}% change, {s['advances']} advances, {s['declines']} declines"
                for s in sector_data[:5]
            ]
        )

        # Create a targeted prompt for sector bullet-point insights
        prompt = f"""
        Based on the following sector data, provide 6-7 concise bullet-point insights:

        Top 5 Sector Movements:
        {sector_summary}

        Please provide exactly 6-7 bullet points that answer these questions:
        - Which sectors are showing strength/weakness and why?
        - What broader economic trends do these movements indicate?
        - What sectors present opportunities or risks?
        - How does sector rotation impact market dynamics?
        - What are the key takeaways for sector investors?
        - What's the outlook for sector performance?
        - What should investors watch in coming sessions?

        Guidelines:
        - Format each bullet point with a simple dash (-) at the beginning
        - Each point must be one sentence maximum
        - Focus on actionable insights
        - Use professional, formal tone
        - Avoid generic statements
        - Highlight key implications
        - Do not include any asterisks or markdown formatting
        - Return the bullet points as a clean list with one point per line
        """

        # Generate insights using Gemini
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

        # Clean up the response to ensure consistent bullet point formatting
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
        logger.error(f"Error generating sector insights: {str(e)}")
        return f"Sector insights generation failed: {str(e)}"


def generate_institutional_insights(institutional_data):
    """Generate concise bullet-point insights for FII/DII activity"""
    if not gemini_api_key:
        logger.warning(
            "Cannot generate institutional insights: GEMINI_API_KEY not available"
        )
        return "Institutional insights not available (API key missing)"

    try:
        # Format institutional data for prompt
        fii_summary = f"FII: Buy INR{institutional_data['fii']['buy_value']:.2f} Cr, Sell INR{institutional_data['fii']['sell_value']:.2f} Cr, Net INR{institutional_data['fii']['net_value']:.2f} Cr"
        dii_summary = f"DII: Buy INR{institutional_data['dii']['buy_value']:.2f} Cr, Sell INR{institutional_data['dii']['sell_value']:.2f} Cr, Net INR{institutional_data['dii']['net_value']:.2f} Cr"

        # Create a targeted prompt for FII/DII bullet-point insights
        prompt = f"""
        Based on the following institutional investment data, provide 6-7 concise bullet-point insights:
        
        Institutional Activity:
        {fii_summary}
        {dii_summary}
        
        Please provide exactly 6-7 bullet points that answer these questions:
        - What's the FII/DII buying/selling pattern indicating?
        - What could be driving these institutional flows?
        - How might this impact the broader market?
        - What's the outlook for institutional activity?
        - What are the key takeaways for retail investors?
        - How does this compare to historical patterns?
        - What should investors watch in coming sessions?
        
        Guidelines:
        - Format each bullet point with a simple dash (-) at the beginning
        - Each point must be one sentence maximum
        - Focus on actionable insights
        - Use professional, formal tone
        - Avoid generic statements
        - Highlight key implications
        - Do not include any asterisks or markdown formatting
        - Return the bullet points as a clean list with one point per line
        """

        # Generate insights using Gemini
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

        # Clean up the response to ensure consistent bullet point formatting
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
        logger.error(f"Error generating institutional insights: {str(e)}")
        return f"Institutional insights generation failed: {str(e)}"
