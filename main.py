import sys
import os

from data.news_highlights import NewsHighlightsGenerator

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("market_api.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Market Data API",
    description="API for market data analysis and reports",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a temporary directory for PDFs if it doesn't exist
PDF_DIR = os.path.join(os.path.dirname(__file__), "temp_pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

# Import routers
from routers.json_endpoints import router as json_router
from routers.pdf_endpoints import router as pdf_router

# Include routers
app.include_router(json_router)
app.include_router(pdf_router)


# Add this to your main application file where FastAPI is initialized


@app.on_event("startup")
async def initialize_news_cache():
    """Pre-warm the NewsHighlightsGenerator cache on application startup."""
    try:
        logger.info("Pre-warming news cache during application startup")
        news_generator = NewsHighlightsGenerator()

        # Force cache initialization - this call will populate the cache
        news_data = news_generator.get_news_highlights()

        # Log success with data counts to verify it worked
        logger.info(
            f"Successfully pre-warmed news cache with "
            f"{len(news_data.get('india_news', []))} India news and "
            f"{len(news_data.get('global_news', []))} global news items"
        )
    except Exception as e:
        logger.error(f"Failed to pre-warm news cache during startup: {str(e)}")
        # Don't raise the exception - we want the app to start even if this fails
        # The first user request will still try to initialize the cache


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8009)
