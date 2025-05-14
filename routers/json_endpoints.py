from fastapi import APIRouter, HTTPException, Response, Request
from fastapi.responses import JSONResponse, FileResponse
from datetime import datetime
import logging
from typing import Dict, Any, List
from sse_starlette.sse import EventSourceResponse
import asyncio
import json


# Local imports
from data.news_highlights import NewsHighlightsGenerator
from data.macro import (
    fetch_all_financial_indicators,
    FinancialDashboard,
    fetch_all_financial_indicators_async,
)
from data.technical_snapshot import (
    get_market_technical_snapshot,
    get_market_technical_snapshot_async,
)
from data.market_overview import (
    fetch_market_data,
    generate_concise_insights,
    generate_report,
    index_names,
    fetch_market_data_async,
)
from data.top_performers import TopPerformersScraper
from data.market_analysis import MarketAnalysisGenerator
from data.sector_scraper import SectorDataScraper, generate_sector_insights
from data.fii_scraper import FIIDataScraper, generate_institutional_insights

# Set up logging with proper formatting
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("market_api")

# Add file handler to save logs to file
file_handler = logging.FileHandler("market_api.log")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)

# Create router
router = APIRouter(
    prefix="/api",
    tags=["Market Data API"],
    responses={404: {"description": "Not found"}},
)


# Helper functions for error handling and response formatting
def create_error_response(error_message: str) -> Dict:
    """Create a standardized error response"""
    logger.error(f"API Error: {error_message}")
    return {
        "timestamp": datetime.now().isoformat(),
        "status": "error",
        "message": error_message,
    }


def log_api_call(endpoint_name: str) -> None:
    """Log API call with endpoint name"""
    logger.info(f"API call: {endpoint_name}")


def log_api_success(endpoint_name: str, processing_info: str = None) -> None:
    """Log API call success with optional processing info"""
    if processing_info:
        logger.info(f"API success: {endpoint_name} - {processing_info}")
    else:
        logger.info(f"API success: {endpoint_name}")


# --------------------
# Market Overview Endpoint
# --------------------
@router.get("/market-overview")
async def get_market_overview():
    log_api_call("market-overview")
    try:
        logger.debug("Generating market report...")
        report = generate_report()
        log_api_success(
            "market-overview",
            f"Generated report with {len(report.get('market_data', {}))} market items",
        )
        return report
    except Exception as e:
        logger.error(f"Error generating market report: {str(e)}", exc_info=True)
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "market_data": {},
            "insights": "Market data is currently unavailable",
            "status": "error",
        }


# --------------------
# Sector Performance Endpoint
# --------------------
@router.get("/sector-performance")
async def get_sector_performance():
    log_api_call("sector-performance")
    try:
        logger.debug("Creating SectorDataScraper instance")
        scraper = SectorDataScraper()
        logger.debug("Scraping sector data")
        sector_data = await scraper.scrape_sector_data_async()
        logger.debug(
            f"Successfully scraped sector data with {len(sector_data)} sectors"
        )
        logger.debug("Generating sector insights")
        sector_insights = generate_sector_insights(sector_data)
        output_data = {
            "sector_movement": {
                "data": sector_data,
                "insight": sector_insights,
            },
            "timestamp": datetime.now().isoformat(),
        }
        log_api_success(
            "sector-performance", f"Generated data for {len(sector_data)} sectors"
        )
        return JSONResponse(content=output_data)
    except Exception as e:
        logger.error(
            f"Error generating sector performance data: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error generating sector performance data: {str(e)}",
        )


# --------------------
# FII Activity Endpoint
# --------------------
@router.get("/fii-activity")
async def get_fii_activity():
    log_api_call("fii-activity")
    try:
        logger.debug("Creating FIIDataScraper instance")
        scraper = FIIDataScraper()
        logger.debug("Scraping FII/DII data")
        institutional_data = await scraper.scrape_institutional_data_async()
        logger.debug("Generating institutional insights")
        institutional_insights = generate_institutional_insights(institutional_data)
        output_data = {
            "institutional_activity": {
                "data": institutional_data,
                "insight": institutional_insights,
            },
            "timestamp": datetime.now().isoformat(),
        }
        log_api_success("fii-activity", "Generated FII/DII data")
        return JSONResponse(content=output_data)
    except Exception as e:
        logger.error(f"Error generating FII activity data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error generating FII activity data: {str(e)}"
        )


# --------------------
# News Highlights Endpoint
# --------------------
@router.get("/news-highlights")
async def get_news_highlights():
    log_api_call("news-highlights")
    try:
        logger.debug("Initializing NewsHighlightsGenerator")
        generator = NewsHighlightsGenerator()
        logger.debug("Fetching news highlights")
        news_highlights = await generator.get_news_highlights()
        # Rename market_impact to news_impact in the response
        if "market_impact" in news_highlights:
            logger.debug("Renaming market_impact to news_impact in response")
            news_highlights["news_impact"] = news_highlights.pop("market_impact")
        log_api_success(
            "news-highlights",
            f"Retrieved {len(news_highlights.get('india_news', []))} India news and "
            f"{len(news_highlights.get('global_news', []))} global news items",
        )
        return JSONResponse(content=news_highlights)
    except Exception as e:
        logger.error(f"Error serving news highlights: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "news_impact": ["News impact analysis unavailable"],
                "india_news": ["India news unavailable"],
                "global_news": ["Global news unavailable"],
                "timestamp": datetime.now().isoformat(),
                "status": "error",
            },
        )


# --------------------
# Financial Indicators Endpoint
# --------------------
@router.get("/indicators", response_model=FinancialDashboard)
async def get_all_indicators():
    log_api_call("indicators")
    try:
        logger.debug("Fetching all financial indicators")
        indicators = await fetch_all_financial_indicators()
        log_api_success(
            "indicators", f"Retrieved {len(indicators)} financial indicators"
        )
        return FinancialDashboard(
            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            indicators=indicators,
        )
    except Exception as e:
        logger.error(f"Error fetching financial indicators: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error fetching indicators: {str(e)}"
        )


# --------------------
# Technical Snapshot Endpoint
# --------------------
@router.get("/technical-snapshot")
async def technical_snapshot():
    """
    Get a technical snapshot of the Indian market indices with Gemini-powered insights.
    """
    log_api_call("technical-snapshot")
    try:
        logger.debug("Generating technical snapshot")
        data = await get_market_technical_snapshot()
        log_api_success(
            "technical-snapshot",
            f"Generated snapshot with {len(data.get('snapshot', {}))} market indices",
        )
        return data
    except Exception as e:
        logger.error(f"Error generating technical snapshot: {str(e)}", exc_info=True)
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "snapshot": {},
            "insights": ["Technical snapshot is currently unavailable."],
            "status": "error",
        }


# --------------------
# Top Performers Endpoint
# --------------------
@router.get("/top-performers")
async def get_market_report():
    log_api_call("top-performers")
    try:
        logger.debug("Initializing TopPerformersScraper")
        scraper = TopPerformersScraper()
        logger.info("Scraping market data for top performers...")
        market_data = await scraper.run_full_scrape()
        output_data = {
            "top_performers": {
                "top_gainers": market_data.get("top_gainers", []),
                "top_losers": market_data.get("top_losers", []),
                "insight": market_data.get("insights", "No insights available"),
            }
        }
        log_api_success(
            "top-performers",
            f"Retrieved {len(market_data.get('top_gainers', []))} gainers and "
            f"{len(market_data.get('top_losers', []))} losers",
        )
        return output_data
    except Exception as e:
        logger.error(f"Error generating top performers report: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


# --------------------
# Comprehensive Market Data Endpoint
# --------------------
@router.get("/comprehensive-market-data")
async def get_combined_market_data_stream(request: Request):
    """
    Server-side events endpoint that streams market data as it becomes available.
    Each section is sent to the client immediately after it's processed.
    """
    log_api_call("comprehensive-market-data-stream")

    async def event_generator():
        market_overview = {}
        sector_movement = {}
        institutional_activity = {}
        top_performers = {}
        technical_data = {}
        financial_indicators = {}
        news_data = {}
        market_analysis = {}

        try:
            # Initial message to let client know we've started
            yield {
                "event": "start",
                "data": json.dumps(
                    {"message": "Starting comprehensive market data collection"}
                ),
            }

            # 1. Market Overview Data
            try:
                logger.debug("Fetching market overview data")
                market_overview_data = await fetch_market_data_async()
                logger.debug(
                    f"Received market overview data for {len([k for k in market_overview_data if k != '_meta'])} indices"
                )
                # Format indices
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

                market_overview = {
                    "indices": indices,
                    "insights": generate_concise_insights(market_overview_data),
                }

                yield {
                    "event": "market_overview",
                    "data": json.dumps({"market_overview": market_overview}),
                }
            except Exception as e:
                logger.error(
                    f"Error collecting market overview data: {str(e)}", exc_info=True
                )
                yield {
                    "event": "error",
                    "data": json.dumps({"section": "market_overview", "error": str(e)}),
                }

            # 2. Sector Data
            try:
                logger.debug("Scraping sector data")
                sector_scraper = SectorDataScraper()
                sector_data = await sector_scraper.scrape_sector_data_async()
                logger.debug(f"Received sector data for {len(sector_data)} sectors")

                sector_movement = {
                    "data": sector_data,
                    "insights": generate_sector_insights(sector_data),
                }

                yield {
                    "event": "sector_movement",
                    "data": json.dumps({"sector_movement": sector_movement}),
                }
            except Exception as e:
                logger.error(f"Error collecting sector data: {str(e)}", exc_info=True)
                yield {
                    "event": "error",
                    "data": json.dumps({"section": "sector_movement", "error": str(e)}),
                }

            # 3. Institutional Data
            try:
                logger.debug("Scraping institutional data")
                fii_scraper = FIIDataScraper()
                institutional_data = await fii_scraper.scrape_institutional_data_async()

                institutional_activity = {
                    "data": institutional_data,
                    "insights": generate_institutional_insights(institutional_data),
                }

                yield {
                    "event": "institutional_activity",
                    "data": json.dumps(
                        {"institutional_activity": institutional_activity}
                    ),
                }
            except Exception as e:
                logger.error(
                    f"Error collecting institutional data: {str(e)}", exc_info=True
                )
                yield {
                    "event": "error",
                    "data": json.dumps(
                        {"section": "institutional_activity", "error": str(e)}
                    ),
                }

            # 4. Top Performers Data
            try:
                logger.debug("Fetching top performers data")
                top_performers_scraper = TopPerformersScraper()
                top_performers_data = await asyncio.to_thread(top_performers_scraper.run_full_scrape)
                logger.debug(
                    f"Received data for {len(top_performers_data.get('top_gainers', []))} gainers and "
                    f"{len(top_performers_data.get('top_losers', []))} losers"
                )

                top_performers = {
                    "top_gainers": top_performers_data.get("top_gainers", []),
                    "top_losers": top_performers_data.get("top_losers", []),
                    "insights": top_performers_data.get("insights", ""),
                }

                yield {
                    "event": "top_performers",
                    "data": json.dumps({"top_performers": top_performers}),
                }
            except Exception as e:
                logger.error(
                    f"Error collecting top performers data: {str(e)}", exc_info=True
                )
                yield {
                    "event": "error",
                    "data": json.dumps({"section": "top_performers", "error": str(e)}),
                }

            # 5. Technical Snapshot
            try:
                logger.debug("Generating technical snapshot")
                technical_data = await get_market_technical_snapshot_async()

                yield {
                    "event": "technical_snapshot",
                    "data": json.dumps({"technical_snapshot": technical_data}),
                }
            except Exception as e:
                logger.error(
                    f"Error generating technical snapshot: {str(e)}", exc_info=True
                )
                yield {
                    "event": "error",
                    "data": json.dumps(
                        {"section": "technical_snapshot", "error": str(e)}
                    ),
                }

            # 6. Financial Indicators
            try:
                logger.debug("Fetching financial indicators")
                financial_indicators = await fetch_all_financial_indicators_async()
                logger.debug(
                    f"Received {len(financial_indicators)} financial indicators"
                )

                # Convert IndicatorData objects to dictionaries for JSON serialization
                financial_indicators_dict = {k: v.dict() for k, v in financial_indicators.items()}

                yield {
                    "event": "financial_indicators",
                    "data": json.dumps({"financial_indicators": financial_indicators_dict}),
                }
            except Exception as e:
                logger.error(
                    f"Error collecting financial indicators: {str(e)}", exc_info=True
                )
                yield {
                    "event": "error",
                    "data": json.dumps(
                        {"section": "financial_indicators", "error": str(e)}
                    ),
                }

            # 7. News Highlights
            try:
                logger.debug("Generating news highlights")
                news_generator = NewsHighlightsGenerator()
                news_data = await news_generator.get_news_highlights_async()

                if not news_data:
                    logger.warning("No news data available")
                    news_data = {
                        "india_news": [],
                        "global_news": [],
                        "impact_news": "No news data available",
                    }

                yield {
                    "event": "news_highlights",
                    "data": json.dumps({"news_highlights": news_data}),
                }
            except Exception as e:
                logger.error(
                    f"Error generating news highlights: {str(e)}", exc_info=True
                )
                yield {
                    "event": "error",
                    "data": json.dumps({"section": "news_highlights", "error": str(e)}),
                }

            # Collect all the data for analysis
            initial_data = {
                "market_overview": (
                    market_overview if "market_overview" in locals() else {}
                ),
                "sector_movement": (
                    sector_movement if "sector_movement" in locals() else {}
                ),
                "institutional_activity": (
                    institutional_activity
                    if "institutional_activity" in locals()
                    else {}
                ),
                "top_performers": (
                    top_performers if "top_performers" in locals() else {}
                ),
                "technical_snapshot": (
                    technical_data if "technical_data" in locals() else {}
                ),
                "financial_indicators": (
                    financial_indicators if "financial_indicators" in locals() else {}
                ),
                "news_highlights": news_data if "news_data" in locals() else {},
            }

            # 8. Market Analysis - needs most of the data to be meaningful
            try:
                logger.debug("Generating market analysis based on collected data")
                market_analyzer = MarketAnalysisGenerator()
                market_analysis = await asyncio.to_thread(market_analyzer.generate_market_analysis, initial_data)

                yield {
                    "event": "market_analysis",
                    "data": json.dumps({"market_analysis": market_analysis}),
                }
            except Exception as e:
                logger.error(
                    f"Error generating market analysis: {str(e)}", exc_info=True
                )
                yield {
                    "event": "error",
                    "data": json.dumps({"section": "market_analysis", "error": str(e)}),
                }

            # 9. Market Summary
            try:
                logger.debug("Generating market summary")
                market_summary = await asyncio.to_thread(market_analyzer.generate_market_summary, initial_data, market_analysis)

                yield {
                    "event": "market_summary",
                    "data": json.dumps({"market_summary": market_summary}),
                }
            except Exception as e:
                logger.error(
                    f"Error generating market summary: {str(e)}", exc_info=True
                )
                yield {
                    "event": "error",
                    "data": json.dumps({"section": "market_summary", "error": str(e)}),
                }

            # 10. Market Predictions
            try:
                logger.debug("Generating market prediction")
                market_prediction = await asyncio.to_thread(market_analyzer.generate_market_prediction, initial_data, market_analysis)

                yield {
                    "event": "market_predictions",
                    "data": json.dumps({"market_predictions": market_prediction}),
                }
            except Exception as e:
                logger.error(
                    f"Error generating market prediction: {str(e)}", exc_info=True
                )
                yield {
                    "event": "error",
                    "data": json.dumps(
                        {"section": "market_predictions", "error": str(e)}
                    ),
                }

            # Final complete message
            yield {
                "event": "complete",
                "data": json.dumps({"message": "Market data collection complete"}),
            }

            log_api_success(
                "comprehensive-market-data-stream",
                "Successfully streamed comprehensive market report",
            )

        except Exception as e:
            logger.error(f"Error in event stream: {str(e)}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"section": "global", "error": str(e)}),
            }

        # Check if client disconnected
        if await request.is_disconnected():
            logger.debug("Client disconnected from SSE stream")
            return

    return EventSourceResponse(event_generator())
