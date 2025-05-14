import os
import logging
from typing import Dict, Any
import time
import asyncio
from dotenv import load_dotenv
import google.generativeai as genai
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("market_api.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

gemini_api_key = os.environ.get("GEMINI_API_KEY")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables")

FII_DII_URLS = [
    "https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/index.php",
    "https://trendlyne.com/macro-data/fii-dii/latest/cash-pastmonth/",
]


class FIIDataScraper:
    def __init__(self):
        self.chrome_options = self._setup_chrome_options()

    def _setup_chrome_options(self) -> Options:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        return chrome_options

    def _create_driver(self):
        return webdriver.Chrome(options=self.chrome_options)

    def scrape_institutional_data(self) -> Dict[str, Any]:
        all_institutional_data = []
        sources_successful = []
        for url in FII_DII_URLS:
            driver = self._create_driver()
            try:
                source_name = url.split("//")[1].split(".")[1].capitalize()
                logger.info(f"Scraping institutional data from {source_name}")
                driver.get(url)
                driver.implicitly_wait(10)
                time.sleep(5)
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

    async def scrape_institutional_data_async(self) -> Dict[str, Any]:
        """Async version of scrape_institutional_data"""
        return await asyncio.to_thread(self.scrape_institutional_data)

    def _process_moneycontrol_institutional(
        self, soup, all_institutional_data, sources_successful
    ):
        selectors = [".mctable1", "table.mctable", "#fii-dii-table", ".data-table"]
        for selector in selectors:
            tables = soup.select(selector)
            if tables and len(tables) >= 1:
                table = tables[0]
                rows = table.select("tr")
                for row_idx in range(1, min(3, len(rows))):
                    try:
                        cols = rows[row_idx].select("td")
                        if len(cols) >= 6:
                            values = []
                            for col in cols:
                                text = col.text.strip().replace(",", "")
                                try:
                                    values.append(float(text))
                                except:
                                    pass
                            if len(values) >= 6:
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
                if rows and len(rows) > 0:
                    try:
                        target_row = rows[1] if len(rows) > 1 else rows[0]
                        cols = target_row.select("td")
                        values = []
                        for col in cols:
                            text = col.text.strip().replace(",", "").replace("INR", "")
                            try:
                                values.append(float(text))
                            except:
                                pass
                        if len(values) >= 6:
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


def generate_institutional_insights(institutional_data):
    if not gemini_api_key:
        logger.warning(
            "Cannot generate institutional insights: GEMINI_API_KEY not available"
        )
        return "Institutional insights not available (API key missing)"
    try:
        fii_summary = f"FII: Buy INR{institutional_data['fii']['buy_value']:.2f} Cr, Sell INR{institutional_data['fii']['sell_value']:.2f} Cr, Net INR{institutional_data['fii']['net_value']:.2f} Cr"
        dii_summary = f"DII: Buy INR{institutional_data['dii']['buy_value']:.2f} Cr, Sell INR{institutional_data['dii']['sell_value']:.2f} Cr, Net INR{institutional_data['dii']['net_value']:.2f} Cr"
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
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        insight_text = response.text.strip()
        lines = insight_text.split("\n")
        clean_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.isspace():
                if not line.startswith("-"):
                    if line.startswith("*"):
                        line = "- " + line[1:].strip()
                    else:
                        line = "- " + line
                clean_lines.append(line)
        return "\n".join(clean_lines)
    except Exception as e:
        logger.error(f"Error generating institutional insights: {str(e)}")
        return f"Institutional insights generation failed: {str(e)}"


async def generate_institutional_insights_async(institutional_data):
    """Async version of generate_institutional_insights"""
    return await asyncio.to_thread(generate_institutional_insights, institutional_data)
