from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from fastapi.responses import FileResponse, JSONResponse
import logging
import os
import json
from datetime import datetime
import tempfile
import shutil

from pydantic import Json
from pdf_generator.financial_indicator import generate_financial_indicators_pdf
from pdf_generator.technical_snapshot import generate_technical_snapshot_pdf
from pdf_generator.top_performers import generate_top_performers_pdf
from data.sector_fii_scraper import (
    MarketDataScraper,
    generate_sector_insights,
    generate_institutional_insights,
)
from data.news_highlights import NewsHighlightsGenerator
from data.top_performers import TopPerformersScraper
from data.market_overview import (
    fetch_market_data,
    generate_concise_insights,
    index_names,
)
from data.technical_snapshot import get_market_technical_snapshot
from data.macro import fetch_all_financial_indicators
from data.market_analysis import MarketAnalysisGenerator

from data.market_overview import generate_report
from pdf_generator.market_overview import MarketOverviewPDFGenerator
from pdf_generator.sector_fii import generate_sector_fii_pdf
from pdf_generator.news_highlights import generate_pdf_from_news_highlights
from pdf_generator.comprehensive_market import ComprehensiveMarketPDFGenerator

# Configure logging with proper formatting - USING THE SAME LOG FILE AS MARKET_API
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pdf_api")

# Add file handler to save logs to the same file as market_api
file_handler = logging.FileHandler(
    "market_api.log"
)  # Changed from pdf_api.log to market_api.log
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)

# Create router
router = APIRouter(
    prefix="/api/pdf",
    tags=["PDF Generation Endpoints"],
    responses={404: {"description": "Not found"}},
)


# Helper Functions
def convert_indicators_to_dict(indicators):
    """
    Convert IndicatorData objects to dictionaries for JSON serialization
    """
    logger.debug("Converting indicators to dictionary format")
    if isinstance(indicators, dict):
        return {
            k: (convert_indicators_to_dict(v) if hasattr(v, "__dict__") else v)
            for k, v in indicators.items()
        }
    elif hasattr(indicators, "__dict__"):
        return indicators.__dict__
    return indicators


def create_temp_pdf_path(prefix="report"):
    """Create a temporary directory and return a PDF file path with timestamp"""
    logger.debug(f"Creating temporary directory for {prefix} PDF")
    temp_dir = tempfile.mkdtemp()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"Stock_Market_{timestamp}.pdf"
    pdf_path = os.path.join(temp_dir, pdf_filename)

    logger.debug(f"Created temporary path: {pdf_path}")
    return temp_dir, pdf_filename, pdf_path


def create_cleanup_task(pdf_path, temp_dir):
    """Create a cleanup function for temporary files"""

    def cleanup():
        logger.debug(f"Cleaning up temporary files at {pdf_path}")
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                logger.debug(f"Removed temporary PDF file: {pdf_path}")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.debug(f"Removed temporary directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")

    return cleanup


def log_pdf_generation_start(endpoint_name):
    """Log the start of PDF generation process"""
    logger.info(f"Starting PDF generation for: {endpoint_name}")


def log_pdf_generation_success(endpoint_name, pdf_path):
    """Log successful PDF generation"""
    logger.info(f"Successfully generated PDF for {endpoint_name}: {pdf_path}")


def log_pdf_generation_error(endpoint_name, error):
    """Log PDF generation error"""
    logger.error(
        f"Error generating PDF for {endpoint_name}: {str(error)}", exc_info=True
    )


# PDF Endpoints
@router.get("/market-overview-pdf", response_class=FileResponse)
async def get_market_overview_pdf(background_tasks: BackgroundTasks):
    log_pdf_generation_start("market-overview")
    try:
        # Generate market report
        logger.debug("Fetching market report data")
        market_report = generate_report()

        # Create temp directory for PDF
        temp_dir, pdf_filename, pdf_path = create_temp_pdf_path("market_overview")

        # Generate PDF
        logger.debug("Generating PDF with MarketOverviewPDFGenerator")
        pdf_generator = MarketOverviewPDFGenerator(market_report)
        pdf_generator.generate(pdf_path)

        # Verify PDF generation
        if not os.path.exists(pdf_path):
            logger.error("PDF file not found after generation attempt")
            raise HTTPException(
                status_code=500, detail="Failed to generate market overview PDF report"
            )

        # Add cleanup task
        background_tasks.add_task(create_cleanup_task(pdf_path, temp_dir))

        log_pdf_generation_success("market-overview", pdf_path)
        return FileResponse(
            path=pdf_path, filename=pdf_filename, media_type="application/pdf"
        )

    except Exception as e:
        log_pdf_generation_error("market-overview", e)
        raise HTTPException(
            status_code=500, detail=f"Error generating market overview PDF: {str(e)}"
        )


@router.get("/sector-fii-data-pdf", response_class=FileResponse)
async def download_sector_fii_data_pdf(background_tasks: BackgroundTasks):
    log_pdf_generation_start("sector-fii-data")
    try:
        # Create temp directory and PDF path
        temp_dir, pdf_filename, pdf_path = create_temp_pdf_path("sector_fii_report")

        # Scrape data
        logger.debug("Creating MarketDataScraper instance")
        scraper = MarketDataScraper()

        logger.debug("Scraping sector data")
        sector_data = scraper.scrape_sector_data()
        logger.debug(f"Successfully scraped {len(sector_data)} sectors")

        logger.debug("Scraping institutional data")
        institutional_data = scraper.scrape_institutional_data()

        logger.debug("Generating sector insights")
        sector_insights = generate_sector_insights(sector_data)

        logger.debug("Generating institutional insights")
        institutional_insights = generate_institutional_insights(institutional_data)

        output_data = {
            "sector_movement": {
                "data": sector_data,
                "insight": sector_insights,
            },
            "institutional_activity": {
                "data": institutional_data,
                "insight": institutional_insights,
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Generate the PDF
        logger.debug(f"Generating sector-fii PDF at {pdf_path}")
        generate_sector_fii_pdf(output_data, pdf_path)

        if not os.path.exists(pdf_path):
            logger.error("PDF file not found after generation attempt")
            raise HTTPException(status_code=500, detail="PDF generation failed.")

        # Add cleanup task
        background_tasks.add_task(create_cleanup_task(pdf_path, temp_dir))

        log_pdf_generation_success("sector-fii-data", pdf_path)
        return FileResponse(
            path=pdf_path,
            filename=pdf_filename,
            media_type="application/pdf",
        )

    except Exception as e:
        log_pdf_generation_error("sector-fii-data", e)
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")


@router.get("/news-highlights-pdf", response_class=FileResponse)
async def generate_news_highlights_pdf(background_tasks: BackgroundTasks):
    log_pdf_generation_start("news-highlights")
    try:
        # Create temp directory and PDF path
        temp_dir, pdf_filename, pdf_path = create_temp_pdf_path(
            "news_highlights_report"
        )

        # Fetch news highlights data
        logger.debug("Initializing NewsHighlightsGenerator")
        generator = NewsHighlightsGenerator()

        logger.debug("Fetching news highlights")
        news_highlights = generator.get_news_highlights()
        logger.debug(
            f"Retrieved {len(news_highlights.get('india_news', []))} India news and "
            f"{len(news_highlights.get('global_news', []))} global news items"
        )

        # Rename market_impact to news_impact in the response
        if "market_impact" in news_highlights:
            logger.debug("Renaming market_impact to news_impact")
            news_highlights["news_impact"] = news_highlights.pop("market_impact")

        # Generate the PDF
        logger.debug(f"Generating news highlights PDF at {pdf_path}")
        generate_pdf_from_news_highlights(news_highlights, pdf_path)

        if not os.path.exists(pdf_path):
            logger.error("PDF file not found after generation attempt")
            raise HTTPException(status_code=500, detail="PDF generation failed.")

        # Add cleanup task
        background_tasks.add_task(create_cleanup_task(pdf_path, temp_dir))

        log_pdf_generation_success("news-highlights", pdf_path)
        return FileResponse(
            path=pdf_path,
            filename=pdf_filename,
            media_type="application/pdf",
        )

    except Exception as e:
        log_pdf_generation_error("news-highlights", e)
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")


@router.get("/indicators-pdf", response_class=FileResponse)
async def download_indicators_pdf(background_tasks: BackgroundTasks):
    log_pdf_generation_start("financial-indicators")
    try:
        # Create temp directory and PDF path
        temp_dir, pdf_filename, pdf_path = create_temp_pdf_path("financial_indicators")

        # Get data
        logger.debug("Fetching financial indicators")
        indicators = fetch_all_financial_indicators()
        logger.debug(f"Retrieved {len(indicators)} financial indicators")

        data = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "indicators": indicators,
        }

        # Generate PDF
        logger.debug(f"Generating financial indicators PDF at {pdf_path}")
        generate_financial_indicators_pdf(data, pdf_path)

        if not os.path.exists(pdf_path):
            logger.error("PDF file not found after generation attempt")
            raise HTTPException(status_code=500, detail="PDF generation failed.")

        # Add cleanup task
        background_tasks.add_task(create_cleanup_task(pdf_path, temp_dir))

        log_pdf_generation_success("financial-indicators", pdf_path)
        return FileResponse(
            path=pdf_path, filename=pdf_filename, media_type="application/pdf"
        )

    except Exception as e:
        log_pdf_generation_error("financial-indicators", e)
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")


@router.get("/technical-snapshot-pdf", response_class=FileResponse)
async def generate_technical_snapshot_pdf_endpoint(background_tasks: BackgroundTasks):
    log_pdf_generation_start("technical-snapshot")
    try:
        # Create temp directory and PDF path
        temp_dir, pdf_filename, pdf_path = create_temp_pdf_path("technical_snapshot")

        # Get data
        logger.debug("Fetching technical snapshot data")
        data = get_market_technical_snapshot()

        # Generate PDF
        logger.debug(f"Generating technical snapshot PDF at {pdf_path}")
        generate_technical_snapshot_pdf(data, pdf_path)

        if not os.path.exists(pdf_path):
            logger.error("PDF file not found after generation attempt")
            raise HTTPException(status_code=500, detail="PDF generation failed.")

        # Add cleanup task
        background_tasks.add_task(create_cleanup_task(pdf_path, temp_dir))

        log_pdf_generation_success("technical-snapshot", pdf_path)
        return FileResponse(
            path=pdf_path, filename=pdf_filename, media_type="application/pdf"
        )

    except Exception as e:
        log_pdf_generation_error("technical-snapshot", e)
        return JSONResponse(
            content={"error": f"Error generating PDF: {str(e)}"},
            status_code=500,
        )


@router.get("/top-performers-pdf", response_class=FileResponse)
async def get_top_performers_pdf(background_tasks: BackgroundTasks):
    log_pdf_generation_start("top-performers")
    try:
        # Create temp directory and PDF path
        temp_dir, pdf_filename, pdf_path = create_temp_pdf_path("top_performers")

        # Get data
        logger.debug("Initializing TopPerformersScraper")
        scraper = TopPerformersScraper()

        logger.debug("Scraping top performers data")
        performers_data = scraper.run_full_scrape()
        logger.debug(
            f"Retrieved {len(performers_data.get('top_gainers', []))} gainers and "
            f"{len(performers_data.get('top_losers', []))} losers"
        )

        data = {"top_performers": performers_data}

        # Generate PDF
        logger.debug(f"Generating top performers PDF at {pdf_path}")
        generate_top_performers_pdf(data, pdf_path)

        if not os.path.exists(pdf_path):
            logger.error("PDF file not found after generation attempt")
            raise HTTPException(status_code=500, detail="PDF generation failed.")

        # Add cleanup task
        background_tasks.add_task(create_cleanup_task(pdf_path, temp_dir))

        log_pdf_generation_success("top-performers", pdf_path)
        return FileResponse(
            path=pdf_path, filename=pdf_filename, media_type="application/pdf"
        )

    except Exception as e:
        log_pdf_generation_error("top-performers", e)
        return JSONResponse(
            content={"error": f"Error generating PDF: {str(e)}"},
            status_code=500,
        )


@router.get("/comprehensive-market-data-pdf", response_class=FileResponse)
async def get_comprehensive_market_pdf(background_tasks: BackgroundTasks):
    log_pdf_generation_start("comprehensive-market-analysis")
    try:
        # Create temp directory and PDF path
        temp_dir, pdf_filename, pdf_path = create_temp_pdf_path(
            "comprehensive_market_analysis"
        )

        logger.info("Starting data collection for comprehensive market PDF")

        # Initialize data collectors
        logger.debug("Initializing data collector objects")
        market_data_scraper = MarketDataScraper()
        news_generator = NewsHighlightsGenerator()
        top_performers_scraper = TopPerformersScraper()
        market_analyzer = MarketAnalysisGenerator()

        # Fetch all required data with detailed logging
        logger.debug("Fetching market overview data")
        market_overview_data = fetch_market_data()
        logger.debug(
            f"Retrieved market data for {len([k for k in market_overview_data if k != '_meta'])} indices"
        )

        logger.debug("Scraping sector data")
        sector_data = market_data_scraper.scrape_sector_data()
        logger.debug(f"Retrieved data for {len(sector_data)} sectors")

        logger.debug("Scraping institutional data")
        institutional_data = market_data_scraper.scrape_institutional_data()

        logger.debug("Fetching top performers data")
        top_performers_data = top_performers_scraper.run_full_scrape()
        logger.debug(
            f"Retrieved {len(top_performers_data.get('top_gainers', []))} gainers and "
            f"{len(top_performers_data.get('top_losers', []))} losers"
        )

        logger.debug("Generating news highlights")
        news_data = news_generator.get_news_highlights()

        logger.debug("Generating technical snapshot")
        technical_data = get_market_technical_snapshot()

        logger.debug("Fetching financial indicators")
        financial_indicators = fetch_all_financial_indicators()

        # Convert indicators to a JSON-serializable format
        logger.debug("Converting financial indicators to serializable format")
        serializable_indicators = convert_indicators_to_dict(financial_indicators)

        # Log indicator count for debugging
        logger.debug(f"Processed {len(serializable_indicators)} financial indicators")

        # Format indices data
        logger.debug("Formatting indices data")
        indices = [
            {
                "name": index_names.get(symbol, symbol),
                "ltp": str(data["Close"]),
                "day_change_percent": f"{data['Change%']}%",
                "day_change": str(data["Change"]),
                "num_companies": "N/A",
            }
            for symbol, data in market_overview_data.items()
            if symbol != "_meta" and isinstance(data, dict) and "Close" in data
        ]
        logger.debug(f"Formatted {len(indices)} indices")

        # Prepare combined data
        logger.debug("Building combined market data structure")
        combined_data = {
            "market_overview": {
                "indices": indices,
                "insights": generate_concise_insights(market_overview_data),
            },
            "sector_movement": {
                "data": sector_data,
                "insights": generate_sector_insights(sector_data),
            },
            "top_performers": {
                "top_gainers": top_performers_data.get("top_gainers", []),
                "top_losers": top_performers_data.get("top_losers", []),
                "insights": top_performers_data.get("insights", ""),
            },
            "news_highlights": news_data,
            "technical_snapshot": technical_data,
            "institutional_activity": {
                "data": institutional_data,
                "insights": generate_institutional_insights(institutional_data),
            },
            "financial_indicators": serializable_indicators,
        }

        # Generate analysis, summary and predictions
        logger.debug("Generating market analysis")
        market_analysis = market_analyzer.generate_market_analysis(combined_data)

        logger.debug("Generating market summary")
        market_summary = market_analyzer.generate_market_summary(
            combined_data, market_analysis
        )

        logger.debug("Generating market predictions")
        market_predictions = market_analyzer.generate_market_prediction(
            combined_data, market_analysis
        )

        # Add analysis, summary and predictions
        logger.debug("Combining all data into final structure")
        ordered_data = {
            "market_analysis": market_analysis,
            **combined_data,
            "market_summary": market_summary,
            "market_predictions": market_predictions,
        }

        # Generate PDF
        logger.debug(f"Generating comprehensive market PDF at {pdf_path}")
        pdf_generator = ComprehensiveMarketPDFGenerator(ordered_data)
        pdf_generator.generate(pdf_path)

        if not os.path.exists(pdf_path):
            logger.error("PDF file not found after generation attempt")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate comprehensive market PDF report",
            )

        # Add cleanup task
        background_tasks.add_task(create_cleanup_task(pdf_path, temp_dir))

        log_pdf_generation_success("comprehensive-market-analysis", pdf_path)
        return FileResponse(
            path=pdf_path,
            filename=pdf_filename,
            media_type="application/pdf",
        )

    except Exception as e:
        log_pdf_generation_error("comprehensive-market-analysis", e)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating comprehensive market PDF: {str(e)}",
        )
