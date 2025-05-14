import json
import time
import logging
import traceback
import re
import os
import asyncio
import aiohttp
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)
from webdriver_manager.chrome import ChromeDriverManager
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add Gemini integration for news impact analysis
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
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


class FinancialNewsScraper:
    def __init__(self, headless=True, timeout=30):
        """Initialize the scraper with browser options."""
        self.timeout = timeout
        self.setup_driver(headless)
        self.site_selectors = {
            "cnbc": {
                "container": "div.Card-standardBreakerCard, div.Card, div.SearchResult-searchResult",
                "title": "a.Card-title, div.Card-titleContainer, div.SearchResult-searchResultTitle",
                "link": "a.Card-title, a.resultlink, a",
                "article_content": "div.ArticleBody-articleBody, div.group, div.ArticleBody-wrapper",
                "accept_cookies": "button#onetrust-accept-btn-handler, button.acceptAllButton",
            },
            "financial_express": {
                "container": "div.stories-card, div.ie-stories, div.article-list, article",
                "title": "h3.title, h4.entry-title a, h2 a, h3 a",
                "link": "a.stories-card-heading-link, a",
                "article_content": "div.main-cont-left, div.article-content, div.custom-post-content",
                "accept_cookies": "button.consent-btn, button.accept-cookie",
            },
            "default": {
                "container": "article, div.article, div.card, div.post, div.item, div.story, div.news-item, .story-card, .news-card",
                "title": "h1, h2, h3, h4, a.title, div.title, a.headline",
                "link": "a, a.readmore, a.title-link",
                "article_content": "article, div.article-body, div.content, div.article-content, div.story-content",
                "accept_cookies": "button#accept-cookies, button.accept-cookies, button.agree, button.accept, button[aria-label='Accept cookies']",
            },
        }

    def setup_driver(self, headless):
        """Set up the Chrome WebDriver with appropriate options."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")

        # Optimize GPU and rendering settings
        chrome_options.add_argument(
            "--disable-gpu"
        )  # Disable GPU hardware acceleration
        chrome_options.add_argument(
            "--disable-software-rasterizer"
        )  # Disable software rasterizer
        chrome_options.add_argument(
            "--disable-dev-shm-usage"
        )  # Overcome limited resource problems
        chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
        chrome_options.add_argument("--disable-web-security")  # Disable web security
        chrome_options.add_argument(
            "--disable-features=IsolateOrigins,site-per-process"
        )  # Disable site isolation
        chrome_options.add_argument(
            "--disable-site-isolation-trials"
        )  # Disable site isolation trials
        chrome_options.add_argument("--disable-webgl")  # Disable WebGL
        chrome_options.add_argument("--disable-webgl2")  # Disable WebGL 2.0
        chrome_options.add_argument("--disable-gpu-sandbox")  # Disable GPU sandbox
        chrome_options.add_argument(
            "--disable-software-rasterizer"
        )  # Disable software rasterizer
        chrome_options.add_argument(
            "--disable-dev-shm-usage"
        )  # Overcome limited resource problems
        chrome_options.add_argument("--no-first-run")  # Skip first run tasks
        chrome_options.add_argument(
            "--no-default-browser-check"
        )  # Skip default browser check
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
        )  # Disable component extensions with background pages
        chrome_options.add_argument("--disable-extensions")  # Disable extensions
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
        chrome_options.add_argument("--window-size=1920,1080")  # Set window size
        chrome_options.add_argument("--disable-notifications")  # Disable notifications
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

        try:
            # Use ChromeDriverManager with specific version
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
            self.driver.set_script_timeout(self.timeout)
            logger.info("WebDriver initiated successfully")
        except Exception as e:
            logger.error(f"Error setting up WebDriver: {e}")
            logger.error(traceback.format_exc())
            raise

    def get_site_config(self, url):
        """Determine which site configuration to use based on URL."""
        if "cnbc.com" in url:
            return self.site_selectors["cnbc"]
        elif "financialexpress.com" in url:
            return self.site_selectors["financial_express"]
        else:
            return self.site_selectors["default"]

    def find_article_containers(self, url):
        """Find all article containers on a listing page."""
        site_config = self.get_site_config(url)
        site_name = self.get_source_name_from_url(url)
        article_containers = []

        # Try to load the page
        try:
            self.driver.get(url)
            logger.info(f"Page loaded: {site_name}")

            # Accept cookies if prompted
            try:
                cookie_selectors = site_config["accept_cookies"].split(", ")
                for selector in cookie_selectors:
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        cookie_button = self.driver.find_element(
                            By.CSS_SELECTOR, selector
                        )
                        if cookie_button.is_displayed():
                            cookie_button.click()
                            logger.info(f"Accepted cookies on {site_name}")
                            time.sleep(1)
                            break
                    except:
                        continue
            except Exception as e:
                logger.info(f"No cookie consent found or error handling cookies: {e}")

            # Scroll to load more content
            for i in range(3):  # Scroll a few times to load more content
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                time.sleep(1)

            # Find article containers
            container_selectors = site_config["container"].split(", ")
            for selector in container_selectors:
                try:
                    containers = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if containers:
                        article_containers.extend(containers)
                        logger.info(
                            f"Found {len(containers)} containers with selector '{selector}'"
                        )
                except Exception as e:
                    logger.warning(
                        f"Error finding containers with selector '{selector}': {e}"
                    )

            if not article_containers:
                # Try default selectors if specific selectors didn't work
                default_selectors = self.site_selectors["default"]["container"].split(
                    ", "
                )
                for selector in default_selectors:
                    try:
                        containers = self.driver.find_elements(
                            By.CSS_SELECTOR, selector
                        )
                        if containers:
                            article_containers.extend(containers)
                    except:
                        continue

            logger.info(f"Found total of {len(article_containers)} article containers")
            return article_containers

        except Exception as e:
            logger.error(f"Error finding article containers: {e}")
            return []

    def extract_title(self, container, site_config):
        """Extract title from an article container."""
        title = ""
        title_selectors = site_config["title"].split(", ")

        for selector in title_selectors:
            try:
                title_elem = container.find_element(By.CSS_SELECTOR, selector)
                title = title_elem.text.strip()
                if title:
                    return title
            except:
                continue

        # If we couldn't find a title, try getting it from any link text
        try:
            links = container.find_elements(By.TAG_NAME, "a")
            for link in links:
                text = link.text.strip()
                if text and len(text) > 15:  # Reasonably sized title
                    return text
        except:
            pass

        return title

    def extract_article_link(self, container, site_config):
        """Extract link to the full article from container."""
        # Try using specific link selectors
        link_selectors = site_config["link"].split(", ")
        for selector in link_selectors:
            try:
                link_elem = container.find_element(By.CSS_SELECTOR, selector)
                href = link_elem.get_attribute("href")
                if href and href.startswith("http"):
                    return href
            except:
                continue

        # Fallback to finding any link in the container
        try:
            links = container.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href")
                if href and href.startswith("http"):
                    return href
        except:
            pass

        return None

    def scrape_articles(self, url, num_articles=15):
        """
        Scrape titles from the listing page, then visit each article to extract content.
        """
        articles = []
        site_config = self.get_site_config(url)
        site_name = self.get_source_name_from_url(url)

        logger.info(f"Starting to scrape {site_name} from {url}")

        try:
            # First find article containers on the listing page
            article_containers = self.find_article_containers(url)

            # Extract links and titles from containers
            article_data = []
            for container in article_containers[:num_articles]:
                try:
                    title = self.extract_title(container, site_config)
                    if not title:
                        continue

                    link = self.extract_article_link(container, site_config)
                    if link:
                        article_data.append(
                            {"title": title, "link": link, "source": site_name}
                        )
                except Exception as e:
                    logger.warning(f"Error extracting article info: {e}")

            logger.info(f"Found {len(article_data)} article links on {site_name}")

            # Now visit each article to get the full content
            for data in article_data:
                try:
                    # Visit the article page
                    self.driver.get(data["link"])
                    logger.info(f"Visiting article: {data['title'][:30]}...")

                    # Wait for content to load (up to 10 seconds)
                    time.sleep(2)

                    # Extract the full article content
                    content = self.extract_article_content(site_config)

                    # Generate a meaningful summary from the content
                    summary = self.generate_content_summary(content)

                    if summary and summary != "No content available":
                        # We'll replace the title with our content summary
                        # This maintains compatibility with the existing code structure
                        articles.append(
                            {
                                "title": summary,  # Use the content summary as the title
                                "source": site_name,
                            }
                        )
                    else:
                        # Fallback to using the original title
                        articles.append({"title": data["title"], "source": site_name})

                except Exception as e:
                    logger.error(f"Error processing article {data['title'][:30]}: {e}")
                    # Add with original title if content extraction failed
                    articles.append({"title": data["title"], "source": site_name})

                # Brief pause between article visits
                time.sleep(1)

            logger.info(
                f"Successfully processed {len(articles)} articles from {site_name}"
            )
            return articles

        except Exception as e:
            logger.error(f"Error scraping {site_name}: {e}")
            logger.error(traceback.format_exc())
            return articles

    async def scrape_articles_async(self, url, num_articles=15):
        """Async version of scrape_articles"""
        return await asyncio.to_thread(self.scrape_articles, url, num_articles)

    def extract_article_content(self, site_config):
        """Extract the full content text from an article page."""
        try:
            # Try site-specific article content selectors
            content_selectors = site_config["article_content"].split(", ")

            for selector in content_selectors:
                try:
                    content_element = self.driver.find_element(
                        By.CSS_SELECTOR, selector
                    )
                    content = content_element.text
                    if content and len(content) > 200:  # We got substantial content
                        return content
                except:
                    continue

            # Try common content selectors if site-specific ones failed
            common_selectors = [
                "article",
                "main",
                "div.article-body",
                "div.content",
                "div.article-content",
                "div.story-body",
                ".post-content",
                "div[itemprop='articleBody']",
            ]

            for selector in common_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    content = element.text
                    if content and len(content) > 200:
                        return content
                except:
                    continue

            # Try getting all paragraphs
            paragraphs = []
            try:
                p_elements = self.driver.find_elements(By.TAG_NAME, "p")
                for p in p_elements:
                    text = p.text.strip()
                    if len(text) > 30:  # Only include substantial paragraphs
                        paragraphs.append(text)

                if paragraphs:
                    return "\n".join(paragraphs)
            except:
                pass

            # Last resort - just get the body text
            try:
                return self.driver.find_element(By.TAG_NAME, "body").text
            except:
                return "No content available"

        except Exception as e:
            logger.error(f"Error extracting article content: {e}")
            return "No content available"

    def generate_content_summary(self, article_text):
        """Generate a meaningful one-sentence summary from article content."""
        if (
            not article_text
            or article_text == "No content available"
            or len(article_text) < 100
        ):
            return None

        try:
            # Split text into sentences using regex to handle various punctuation
            sentences = re.split(r"(?<=[.!?])\s+", article_text)

            # Filter out short or invalid sentences
            valid_sentences = [s for s in sentences if len(s) > 40 and len(s) < 200]

            if not valid_sentences:
                return None

            # Find sentences that contain financial keywords
            financial_keywords = [
                "market",
                "stock",
                "index",
                "share",
                "invest",
                "price",
                "rate",
                "growth",
                "economy",
                "financial",
                "dollar",
                "percent",
                "bond",
                "trading",
                "investor",
                "earning",
                "revenue",
                "profit",
                "loss",
            ]

            # Try to find a sentence in the first 5 that has financial keywords
            for sentence in valid_sentences[:5]:
                if any(keyword in sentence.lower() for keyword in financial_keywords):
                    # Ensure sentence ends with proper punctuation
                    if not sentence.rstrip().endswith((".", "!", "?")):
                        sentence += "."
                    return sentence

            # If no good sentence in first 5, use the first valid sentence
            first_sentence = valid_sentences[0]
            if not first_sentence.rstrip().endswith((".", "!", "?")):
                first_sentence += "."
            return first_sentence

        except Exception as e:
            logger.error(f"Error generating content summary: {e}")
            return None

    def get_source_name_from_url(self, url):
        """Extract a readable source name from URL."""
        if "cnbc.com" in url:
            return "CNBC"
        elif "financialexpress.com" in url:
            return "Financial Express"
        else:
            return "Unknown Source"

    def close(self):
        """Close the WebDriver session."""
        if hasattr(self, "driver"):
            try:
                self.driver.quit()
                logger.info("WebDriver session closed")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")


class SimpleNewsClassifier:
    """A simple classifier that relies on keyword matching"""

    def __init__(self):
        # Keep the keywords lists for impact, but we'll use them differently
        self.impact_keywords = [
            "policy",
            "regulation",
            "economy",
            "inflation",
            "recession",
            "central bank",
            "fed",
            "federal reserve",
            "interest rate",
            "gdp",
            "treasury",
            "economic growth",
            "fiscal",
            "monetary",
            "budget",
            "minister",
            "government",
            "tax",
            "deficit",
            "stimulus",
            "debt",
            "tariff",
            "market crash",
            "rally",
            "volatility",
            "crisis",
            "emergency",
            "warning",
            "alert",
            "critical",
            "major",
            "significant",
            "breakthrough",
            "disruption",
            "transformation",
            "revolution",
        ]

        self.india_keywords = [
            "india",
            "indian",
            "mumbai",
            "delhi",
            "bse",
            "nse",
            "sensex",
            "nifty",
            "rupee",
            "rbi",
            "sebi",
            "finance minister",
            "pm modi",
            "government of india",
            "indian economy",
            "indian market",
            "indian stock",
            "indian rupee",
            "indian banks",
            "indian companies",
        ]

        self.global_keywords = [
            "global",
            "world",
            "international",
            "foreign",
            "overseas",
            "europe",
            "asia",
            "america",
            "china",
            "japan",
            "uk",
            "us",
            "european",
            "asian",
            "american",
            "foreign exchange",
            "forex",
            "global market",
            "world economy",
            "international trade",
            "global economy",
            "world market",
        ]

    def categorize_news(self, articles):
        india_news = []
        global_news = []

        for article in articles:
            title = article["title"].lower()  # Content is now in the title field
            source = article["source"]

            # Create bullet point
            bullet = f"{article['title']} (Source: {source})"

            # Check for India keywords first
            is_india = any(keyword in title for keyword in self.india_keywords)

            # Check for Global keywords
            is_global = any(keyword in title for keyword in self.global_keywords)

            # Categorize the news into just India or Global
            if is_india or source == "Financial Express":
                # If it contains India keywords or is from an Indian source
                india_news.append(bullet)
            else:
                # All other news goes into global category
                global_news.append(bullet)

        # Limit to 10 articles per category (since we now have only 2 categories, we can show more per category)
        return {
            "india": india_news[:10],
            "global": global_news[:10],
        }

    async def categorize_news_async(self, articles):
        """Async version of categorize_news"""
        return await asyncio.to_thread(self.categorize_news, articles)


class NewsHighlightsGenerator:
    def __init__(self):
        """Initialize the news highlights generator."""
        self.scraper = FinancialNewsScraper(headless=True, timeout=45)
        self.classifier = SimpleNewsClassifier()

        # Initialize Gemini for news analysis
        self.gemini_model = None
        if GEMINI_API_KEY:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")
                logger.info("Successfully initialized Gemini API for news analysis")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {str(e)}")
        else:
            logger.warning("Gemini API key not found. News analysis will be limited.")

        # Configure session with better retry strategy and SSL handling
        self.session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504, 429],
            allowed_methods=["GET", "POST"],
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Configure session defaults
        self.session.verify = False
        self.session.timeout = (30, 180)
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        # Suppress only the single InsecureRequestWarning
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def analyze_news_with_gemini(self, articles):
        """Use Gemini to analyze and categorize news articles."""
        if not self.gemini_model:
            return None

        try:
            # Format articles for the prompt
            articles_text = "\n".join(
                [
                    f"- {article['title']} (Source: {article['source']})"
                    for article in articles
                ]
            )

            prompt = f"""
            As a financial news analyst, analyze these news headlines and provide:
            1. A concise news impact analysis (6-7 bullet points)
            2. Categorize the news into India-specific and Global news (6-7 points each)

            News Headlines:
            {articles_text}

            Guidelines:
            - Each bullet point must be one clear, informative sentence
            - Focus on market implications and actionable insights
            - Include specific data points where available
            - Use professional financial language
            - Keep each point under 20 words
            - Start each point with a dash (-)

            Format your response as:
            NEWS IMPACT:
            [6-7 bullet points about overall news impact]

            INDIA NEWS:
            [6-7 bullet points about India-specific news]

            GLOBAL NEWS:
            [6-7 bullet points about global news]
            """

            response = self.gemini_model.generate_content(prompt)
            analysis = response.text.strip()

            # Parse the response into sections
            sections = {"news_impact": [], "india_news": [], "global_news": []}

            current_section = None
            for line in analysis.split("\n"):
                line = line.strip()
                if not line:
                    continue

                if "NEWS IMPACT:" in line:
                    current_section = "news_impact"
                elif "INDIA NEWS:" in line:
                    current_section = "india_news"
                elif "GLOBAL NEWS:" in line:
                    current_section = "global_news"
                elif line.startswith("-") and current_section:
                    sections[current_section].append(line)

            return sections

        except Exception as e:
            logger.error(f"Error analyzing news with Gemini: {str(e)}")
            return None

    async def analyze_news_with_gemini_async(self, articles):
        """Async version of analyze_news_with_gemini"""
        return await asyncio.to_thread(self.analyze_news_with_gemini, articles)

    def get_news_highlights(self) -> Dict:
        """Get news highlights from multiple sources with Gemini-powered analysis."""
        try:
            # Scrape news from different sources
            cnbc_articles = self.scrape_cnbc()
            financial_express_articles = self.scrape_financial_express()

            # Combine all articles
            all_articles = cnbc_articles + financial_express_articles

            # Get Gemini analysis
            analysis = self.analyze_news_with_gemini(all_articles)

            if analysis:
                return {
                    "news_impact": analysis["news_impact"],
                    "india_news": analysis["india_news"],
                    "global_news": analysis["global_news"],
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                }
            else:
                # Fallback to simple categorization if Gemini analysis fails
                categorized_news = self.classifier.categorize_news(all_articles)

                return {
                    "news_impact": ["News impact analysis unavailable"],
                    "india_news": categorized_news["india"],
                    "global_news": categorized_news["global"],
                    "timestamp": datetime.now().isoformat(),
                    "status": "partial",
                }

        except Exception as e:
            logger.error(f"Error getting news highlights: {str(e)}")
            return {
                "news_impact": ["News analysis unavailable"],
                "india_news": ["India news unavailable"],
                "global_news": ["Global news unavailable"],
                "timestamp": datetime.now().isoformat(),
                "status": "error",
            }
        finally:
            # Close the scraper
            try:
                self.scraper.close()
            except Exception as e:
                logger.error(f"Error closing scraper: {e}")

    async def get_news_highlights_async(self) -> Dict:
        """Async version of get_news_highlights"""
        try:
            # Scrape news from different sources in parallel
            cnbc_task = self.scrape_cnbc_async()
            financial_express_task = self.scrape_financial_express_async()

            # Await results
            cnbc_articles, financial_express_articles = await asyncio.gather(
                cnbc_task, financial_express_task
            )

            # Combine all articles
            all_articles = cnbc_articles + financial_express_articles

            # Get Gemini analysis asynchronously
            analysis = await self.analyze_news_with_gemini_async(all_articles)

            if analysis:
                return {
                    "news_impact": analysis["news_impact"],
                    "india_news": analysis["india_news"],
                    "global_news": analysis["global_news"],
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                }
            else:
                # Fallback to simple categorization if Gemini analysis fails
                categorized_news = await self.classifier.categorize_news_async(
                    all_articles
                )

                return {
                    "news_impact": ["News impact analysis unavailable"],
                    "india_news": categorized_news["india"],
                    "global_news": categorized_news["global"],
                    "timestamp": datetime.now().isoformat(),
                    "status": "partial",
                }

        except Exception as e:
            logger.error(f"Error getting news highlights asynchronously: {str(e)}")
            return {
                "news_impact": ["News analysis unavailable"],
                "india_news": ["India news unavailable"],
                "global_news": ["Global news unavailable"],
                "timestamp": datetime.now().isoformat(),
                "status": "error",
            }
        finally:
            # Close the scraper
            try:
                self.scraper.close()
            except Exception as e:
                logger.error(f"Error closing scraper: {e}")

    def scrape_cnbc(self) -> List[Dict]:
        """Scrape CNBC for market news"""
        articles = []
        try:
            response = self._get_with_retry("https://www.cnbc.com/markets/")
            if not response:
                return articles

            soup = BeautifulSoup(response.text, "html.parser")
            article_containers = soup.select("div.Card-standardBreakerCard")

            for container in article_containers[:10]:  # Limit to 10 articles
                try:
                    title_elem = container.select_one("a.Card-title")
                    if not title_elem:
                        continue

                    title = title_elem.text.strip()
                    link = title_elem.get("href", "")
                    if not link.startswith("http"):
                        link = "https://www.cnbc.com" + link

                    articles.append({"title": title, "link": link, "source": "CNBC"})
                except Exception as e:
                    logger.error(f"Error processing CNBC article: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error scraping CNBC: {str(e)}")

        return articles

    async def scrape_cnbc_async(self) -> List[Dict]:
        """Async version of scrape_cnbc"""
        return await asyncio.to_thread(self.scrape_cnbc)

    def scrape_financial_express(self) -> List[Dict]:
        """Scrape Financial Express for market news with improved error handling"""
        articles = []
        max_retries = 3
        base_url = "https://www.financialexpress.com/market/"

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Attempting to scrape Financial Express (attempt {attempt + 1}/{max_retries})"
                )

                # Try direct requests first
                response = self._get_with_retry(base_url)
                if not response:
                    logger.warning(
                        f"Failed to fetch Financial Express on attempt {attempt + 1}"
                    )
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                article_containers = soup.select(
                    "div.article-list, div.stories-card, article"
                )

                if not article_containers:
                    logger.warning(
                        f"No article containers found on attempt {attempt + 1}"
                    )
                    continue

                for container in article_containers[:10]:  # Limit to 10 articles
                    try:
                        title_elem = container.select_one(
                            "h3.title, h4.entry-title a, h2 a, h3 a"
                        )
                        if not title_elem:
                            continue

                        title = title_elem.text.strip()
                        link_elem = container.select_one("a")
                        link = link_elem.get("href", "") if link_elem else ""

                        if not link.startswith("http"):
                            link = "https://www.financialexpress.com" + link

                        articles.append(
                            {
                                "title": title,
                                "link": link,
                                "source": "Financial Express",
                            }
                        )
                    except Exception as e:
                        logger.error(
                            f"Error processing Financial Express article: {str(e)}"
                        )
                        continue

                if articles:
                    logger.info(
                        f"Successfully scraped {len(articles)} articles from Financial Express"
                    )
                    break
                else:
                    logger.warning(f"No articles extracted on attempt {attempt + 1}")

            except Exception as e:
                logger.error(
                    f"Error scraping Financial Express on attempt {attempt + 1}: {str(e)}"
                )
                if attempt < max_retries - 1:
                    wait_time = (2**attempt) + random.uniform(0, 1)
                    logger.info(f"Waiting {wait_time:.2f} seconds before retry...")
                    time.sleep(wait_time)
                continue

        return articles

    async def scrape_financial_express_async(self) -> List[Dict]:
        """Async version of scrape_financial_express"""
        return await asyncio.to_thread(self.scrape_financial_express)

    def _get_with_retry(
        self, url: str, max_retries: int = 3
    ) -> Optional[requests.Response]:
        """Get URL with retry logic and exponential backoff"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    url,
                    timeout=(30, 180),
                    verify=False,  # Disable SSL verification
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    },
                )
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    logger.error(
                        f"Failed to fetch {url} after {max_retries} attempts: {str(e)}"
                    )
                    return None
                wait_time = (2**attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {wait_time:.2f} seconds..."
                )
                time.sleep(wait_time)
        return None

    async def _get_with_retry_async(
        self, url: str, max_retries: int = 3
    ) -> Optional[str]:
        """Async version of _get_with_retry using aiohttp"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            for attempt in range(max_retries):
                try:
                    async with session.get(
                        url, headers=headers, timeout=30, ssl=False
                    ) as response:
                        if response.status == 200:
                            return await response.text()

                        if attempt < max_retries - 1:
                            wait_time = (2**attempt) + random.uniform(0, 1)
                            logger.warning(
                                f"Attempt {attempt + 1} failed with status {response.status}, retrying in {wait_time:.2f} seconds..."
                            )
                            await asyncio.sleep(wait_time)
                            continue
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = (2**attempt) + random.uniform(0, 1)
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {str(e)}, retrying in {wait_time:.2f} seconds..."
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    logger.error(
                        f"Failed to fetch {url} after {max_retries} attempts: {str(e)}"
                    )

            return None
