import os
import logging
from typing import Dict, List, Any
import time
import asyncio
import pandas as pd
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

SECTOR_URLS = [
    "https://trendlyne.com/equity/sector-industry-analysis/sector/day/",
]

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


class SectorDataScraper:
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

    def _map_to_standard_sector(self, sector_name: str) -> str:
        sector_name = sector_name.lower()
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
        return sector_name.title()

    def scrape_sector_data(self) -> List[Dict[str, Any]]:
        sector_dict = {}
        url = SECTOR_URLS[0]
        driver = self._create_driver()
        try:
            logger.info(f"Scraping sector data from Trendlyne")
            driver.get(url)
            driver.implicitly_wait(10)
            time.sleep(5)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            self._process_trendlyne_sector(soup, sector_dict)
        except Exception as e:
            logger.error(f"Error in sector scraping for {url}: {str(e)}")
        finally:
            driver.quit()
        sector_data = list(sector_dict.values())
        sector_data.sort(key=lambda x: x["change_percentage"], reverse=True)
        sector_data = sector_data[:11]
        logger.info(f"Scraped sector data from Trendlyne: {len(sector_data)} sectors")
        return sector_data

    async def scrape_sector_data_async(self) -> List[Dict[str, Any]]:
        """Async version of scrape_sector_data"""
        return await asyncio.to_thread(self.scrape_sector_data)

    def _process_trendlyne_sector(self, soup, sector_dict):
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
                for row in rows:
                    try:
                        cols = row.select("td")
                        if len(cols) >= 5:
                            sector_name = cols[0].text.strip()
                            mapped_sector = self._map_to_standard_sector(sector_name)
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
                            except Exception as e:
                                logger.error(f"Error parsing Trendlyne row: {str(e)}")
                                continue
                    except Exception as e:
                        logger.error(f"Error processing Trendlyne row: {str(e)}")
                        continue
                return True
        return False


def generate_sector_insights(sector_data):
    if not gemini_api_key:
        logger.warning("Cannot generate sector insights: GEMINI_API_KEY not available")
        return "Sector insights not available (API key missing)"
    try:
        sector_summary = "\n".join(
            [
                f"- {s['sector_name']}: {s['change_percentage']:.2f}% change, {s['advances']} advances, {s['declines']} declines"
                for s in sector_data[:5]
            ]
        )
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
        logger.error(f"Error generating sector insights: {str(e)}")
        return f"Sector insights generation failed: {str(e)}"


async def generate_sector_insights_async(sector_data):
    """Async version of generate_sector_insights"""
    return await asyncio.to_thread(generate_sector_insights, sector_data)
