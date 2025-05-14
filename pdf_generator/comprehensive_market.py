from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ComprehensiveMarketPDFGenerator:
    def __init__(self, data):
        self.data = data
        self.styles = getSampleStyleSheet()

        # Colors
        self.positive_color = colors.HexColor("#2e7d32")  # Green
        self.negative_color = colors.HexColor("#c62828")  # Red
        self.neutral_color = colors.HexColor("#1565c0")  # Blue
        self.header_color = colors.HexColor("#1a237e")  # Deep Blue

        # Reduced font sizes and spacing for more compact layout
        self.title_size = 16  # Reduced from 20
        self.heading_size = 11  # Reduced from 13
        self.subheading_size = 10  # Reduced from 11
        self.body_size = 8  # Reduced from 9
        self.table_header_size = 8  # Reduced from 9
        self.table_body_size = 7  # Reduced from 8

        # Minimal spacing
        self.section_spacing = 4  # Reduced from 8
        self.subsection_spacing = 2  # Reduced from 4
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Setup styles
        self._create_custom_styles()

    def _create_custom_styles(self):
        """Create custom styles with unique names and optimized spacing"""
        # Title Style
        self.styles.add(
            ParagraphStyle(
                "MarketTitleStyle",
                parent=self.styles["Heading1"],
                fontSize=self.title_size,
                spaceAfter=8,  # Reduced from 15
                textColor=self.header_color,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )

        # Section Header Style
        self.styles.add(
            ParagraphStyle(
                "MarketSectionHeader",
                parent=self.styles["Heading1"],
                fontSize=self.heading_size,
                textColor=self.header_color,
                spaceBefore=6,  # Reduced from 10
                spaceAfter=4,  # Reduced from 6
                fontName="Helvetica-Bold",
            )
        )

        # Sub Header Style
        self.styles.add(
            ParagraphStyle(
                "MarketSubHeader",
                parent=self.styles["Heading2"],
                fontSize=self.subheading_size,
                textColor=self.header_color,
                spaceBefore=4,  # Reduced from 6
                spaceAfter=2,  # Reduced from 3
                fontName="Helvetica-Bold",
            )
        )

        # Body Text Style
        self.styles.add(
            ParagraphStyle(
                "MarketBodyText",
                parent=self.styles["Normal"],
                fontSize=self.body_size,
                spaceBefore=1,
                spaceAfter=1,
                leading=9,  # Reduced from 10
            )
        )

        # Bullet Point Style
        self.styles.add(
            ParagraphStyle(
                "MarketBulletPoint",
                parent=self.styles["Normal"],
                fontSize=self.body_size,
                spaceBefore=1,
                spaceAfter=1,
                leftIndent=8,  # Reduced from 10
                leading=9,  # Reduced from 10
            )
        )

        # Table Header Style
        self.styles.add(
            ParagraphStyle(
                "MarketTableHeader",
                parent=self.styles["Normal"],
                fontSize=self.table_header_size,
                textColor=colors.white,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )

        # Table Cell Style
        self.styles.add(
            ParagraphStyle(
                "MarketTableCell",
                parent=self.styles["Normal"],
                fontSize=self.table_body_size,
                alignment=TA_CENTER,
            )
        )

    def _format_currency(self, value, include_symbol=True):
        """Format currency values with INR symbol"""
        try:
            num = float(str(value).replace(",", "").replace("₹", "").replace("$", ""))
            formatted = f"{abs(num):,.2f}"

            if include_symbol:
                if "$" in str(value):
                    formatted = f"${formatted}"
                else:
                    formatted = f"INR {formatted}"

            if num > 0:
                return f"+{formatted}", self.positive_color
            elif num < 0:
                return f"-{formatted}", self.negative_color
            return formatted, self.neutral_color
        except:
            return str(value), self.neutral_color

    def _format_percentage(self, value):
        """Format percentage values"""
        try:
            num = float(str(value).replace("%", ""))
            formatted = f"{abs(num):.2f}%"
            if num > 0:
                return f"+{formatted}", self.positive_color
            elif num < 0:
                return f"-{formatted}", self.negative_color
            return formatted, self.neutral_color
        except:
            return str(value), self.neutral_color

    def _create_table_style(self, has_header=True, alternating=True):
        """Create optimized table style with reduced padding"""
        style = [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), self.table_header_size),
            ("BACKGROUND", (0, 0), (-1, 0), self.header_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), self.table_body_size),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 2),  # Reduced from 4
        ]

        if alternating:
            style.append(
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            )

        return TableStyle(style)

    def _get_sentiment_color(self, text):
        """Determine color based on sentiment in text"""
        text_lower = text.lower()
        positive_words = [
            "positive",
            "gain",
            "up",
            "bullish",
            "rise",
            "advance",
            "surge",
            "growth",
            "high",
            "outperform",
            "strength",
        ]
        negative_words = [
            "negative",
            "decline",
            "down",
            "bearish",
            "drop",
            "fall",
            "loss",
            "underperform",
            "weak",
            "risk",
            "caution",
        ]

        for word in positive_words:
            if word in text_lower:
                return self.positive_color
        for word in negative_words:
            if word in text_lower:
                return self.negative_color
        return self.neutral_color

    def _add_title(self, story):
        """Add title with minimal spacing"""
        story.append(
            Paragraph(
                '<para alignment="center"><font color="#1a237e">═══════════════════════</font></para>',
                self.styles["Normal"],
            )
        )
        story.append(Paragraph("PRE MARKET REPORT", self.styles["MarketTitleStyle"]))
        story.append(
            Paragraph(
                '<para alignment="center"><font color="#1a237e">═══════════════════════</font></para>',
                self.styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                f'<para alignment="center"><font color="#666666">Generated on: {self.timestamp}</font></para>',
                self.styles["MarketBodyText"],
            )
        )

    def _add_market_analysis(self, story):
        """Add market analysis section"""
        story.append(Paragraph("Market Analysis", self.styles["MarketSectionHeader"]))

        if "market_analysis" in self.data and self.data["market_analysis"]:
            points = self.data["market_analysis"].split("\n")
            for point in points:
                if point.strip():
                    color = self._get_sentiment_color(point)
                    story.append(
                        Paragraph(
                            f'<para alignment="left"><font color="{color.hexval()}">►</font> {point.strip()}</para>',
                            self.styles["MarketBulletPoint"],
                        )
                    )

    def _add_market_overview(self, story):
        """Add market overview section"""
        story.append(Paragraph("Market Overview", self.styles["MarketSectionHeader"]))

        if "market_overview" in self.data:
            # Add insights first
            if "insights" in self.data["market_overview"]:
                story.append(
                    Paragraph("Market Insights", self.styles["MarketSubHeader"])
                )
                story.append(
                    Paragraph(
                        self.data["market_overview"]["insights"],
                        self.styles["MarketBodyText"],
                    )
                )
                story.append(Spacer(1, 3))  # Reduced spacing

            # Add indices table with more compact column widths
            if "indices" in self.data["market_overview"]:
                story.append(
                    Paragraph("Index Performance", self.styles["MarketSubHeader"])
                )

                table_data = [["Index", "LTP", "Chg %", "Chg"]]
                for idx in self.data["market_overview"]["indices"]:
                    ltp_val, ltp_color = self._format_currency(idx["ltp"])
                    change_pct, pct_color = self._format_percentage(
                        idx["day_change_percent"]
                    )
                    change_val, change_color = self._format_currency(idx["day_change"])

                    table_data.append(
                        [
                            idx["name"],
                            Paragraph(
                                f'<font color="{ltp_color.hexval()}">{ltp_val}</font>',
                                self.styles["MarketTableCell"],
                            ),
                            Paragraph(
                                f'<font color="{pct_color.hexval()}">{change_pct}</font>',
                                self.styles["MarketTableCell"],
                            ),
                            Paragraph(
                                f'<font color="{change_color.hexval()}">{change_val}</font>',
                                self.styles["MarketTableCell"],
                            ),
                        ]
                    )

                # Reduced column widths
                table = Table(
                    table_data, colWidths=[2 * inch, 1.2 * inch, 1 * inch, 1 * inch]
                )
                table.setStyle(self._create_table_style())
                story.append(table)

    def _add_sector_movement(self, story):
        """Add sector movement section"""
        story.append(Paragraph("Sector Movement", self.styles["MarketSectionHeader"]))

        if "sector_movement" in self.data:
            # Add insights first
            if "insights" in self.data["sector_movement"]:
                story.append(
                    Paragraph("Sector Insights", self.styles["MarketSubHeader"])
                )
                self._add_insights(story, self.data["sector_movement"]["insights"])
                story.append(Spacer(1, 3))

            # Add sector data table
            if "data" in self.data["sector_movement"]:
                story.append(
                    Paragraph("Sector Performance", self.styles["MarketSubHeader"])
                )

                table_data = [["Sector", "Chg %", "Adv", "Dec", "Total"]]
                for sector in self.data["sector_movement"]["data"]:
                    change_pct, color = self._format_percentage(
                        sector["change_percentage"]
                    )
                    table_data.append(
                        [
                            (
                                sector["sector_name"][:20] + "..."
                                if len(sector["sector_name"]) > 20
                                else sector["sector_name"]
                            ),
                            Paragraph(
                                f'<font color="{color.hexval()}">{change_pct}</font>',
                                self.styles["MarketTableCell"],
                            ),
                            str(sector["advances"]),
                            str(sector["declines"]),
                            str(sector["num_companies"]),
                        ]
                    )

                # More compact column widths
                table = Table(
                    table_data,
                    colWidths=[
                        1.8 * inch,
                        0.8 * inch,
                        0.8 * inch,
                        0.8 * inch,
                        0.8 * inch,
                    ],
                )
                table.setStyle(self._create_table_style())
                story.append(table)

    def _add_top_performers(self, story):
        """Add top performers section with separated tables"""
        story.append(Paragraph("Top Performers", self.styles["MarketSectionHeader"]))

        if "top_performers" in self.data:
            # Add insights first
            if "insights" in self.data["top_performers"]:
                story.append(
                    Paragraph("Market Movers Insights", self.styles["MarketSubHeader"])
                )
                self._add_insights(story, self.data["top_performers"]["insights"])
                story.append(Spacer(1, 3))

            # Add gainers table
            story.append(Paragraph("Top Gainers", self.styles["MarketSubHeader"]))
            gainers_data = [["Company", "Price", "Chg", "Chg %"]]
            for gainer in self.data["top_performers"].get("top_gainers", []):
                price, price_color = self._format_currency(gainer["current_price"])
                change, change_color = self._format_currency(gainer["price_change"])
                pct, pct_color = self._format_percentage(gainer["percentage_change"])

                gainers_data.append(
                    [
                        (
                            gainer["company_name"][:20] + "..."
                            if len(gainer["company_name"]) > 20
                            else gainer["company_name"]
                        ),
                        Paragraph(
                            f'<font color="{price_color.hexval()}">{price}</font>',
                            self.styles["MarketTableCell"],
                        ),
                        Paragraph(
                            f'<font color="{change_color.hexval()}">{change}</font>',
                            self.styles["MarketTableCell"],
                        ),
                        Paragraph(
                            f'<font color="{pct_color.hexval()}">{pct}</font>',
                            self.styles["MarketTableCell"],
                        ),
                    ]
                )

            # More compact column widths
            gainers_table = Table(
                gainers_data, colWidths=[1.8 * inch, 1 * inch, 1 * inch, 1 * inch]
            )
            gainers_table.setStyle(self._create_table_style())
            story.append(gainers_table)
            story.append(Spacer(1, 3))

            # Add losers table
            story.append(Paragraph("Top Losers", self.styles["MarketSubHeader"]))
            losers_data = [["Company", "Price", "Chg", "Chg %"]]
            for loser in self.data["top_performers"].get("top_losers", []):
                price, price_color = self._format_currency(loser["current_price"])
                change, change_color = self._format_currency(loser["price_change"])
                pct, pct_color = self._format_percentage(loser["percentage_change"])

                losers_data.append(
                    [
                        (
                            loser["company_name"][:20] + "..."
                            if len(loser["company_name"]) > 20
                            else loser["company_name"]
                        ),
                        Paragraph(
                            f'<font color="{price_color.hexval()}">{price}</font>',
                            self.styles["MarketTableCell"],
                        ),
                        Paragraph(
                            f'<font color="{change_color.hexval()}">{change}</font>',
                            self.styles["MarketTableCell"],
                        ),
                        Paragraph(
                            f'<font color="{pct_color.hexval()}">{pct}</font>',
                            self.styles["MarketTableCell"],
                        ),
                    ]
                )

            # More compact column widths
            losers_table = Table(
                losers_data, colWidths=[1.8 * inch, 1 * inch, 1 * inch, 1 * inch]
            )
            losers_table.setStyle(self._create_table_style())
            story.append(losers_table)

    def _add_news_highlights(self, story):
        """Add news highlights section with improved layout"""
        story.append(Paragraph("News Highlights", self.styles["MarketSectionHeader"]))

        if "news_highlights" in self.data:
            # Add market impact first
            if (
                "news_impact" in self.data["news_highlights"]
                and self.data["news_highlights"]["news_impact"]
            ):
                story.append(Paragraph("Market Impact", self.styles["MarketSubHeader"]))
                for impact in self.data["news_highlights"]["news_impact"]:
                    color = self._get_sentiment_color(impact)
                    story.append(
                        Paragraph(
                            f'<para alignment="left"><font color="{color.hexval()}">►</font> {impact}</para>',
                            self.styles["MarketBulletPoint"],
                        )
                    )
                story.append(Spacer(1, 3))

            # Create combined news table
            india_news = self.data["news_highlights"].get("india_news", [])
            global_news = self.data["news_highlights"].get("global_news", [])

            if india_news or global_news:
                # Prepare data for two-column table
                max_rows = max(len(india_news), len(global_news))
                table_data = [["India News", "Global News"]]

                for i in range(max_rows):
                    row = [
                        Paragraph(
                            india_news[i] if i < len(india_news) else "",
                            self.styles["MarketBodyText"],
                        ),
                        Paragraph(
                            global_news[i] if i < len(global_news) else "",
                            self.styles["MarketBodyText"],
                        ),
                    ]
                    table_data.append(row)

                # Compact column widths
                table = Table(table_data, colWidths=[3 * inch, 3 * inch])
                table.setStyle(self._create_table_style())
                story.append(table)

    def _add_technical_snapshot(self, story):
        """Add technical snapshot section"""
        story.append(
            Paragraph("Technical Snapshot", self.styles["MarketSectionHeader"])
        )

        if "technical_snapshot" in self.data:
            snapshot = self.data["technical_snapshot"]

            # Add insights first
            if "insights" in snapshot:
                story.append(
                    Paragraph("Technical Insights", self.styles["MarketSubHeader"])
                )
                for insight in snapshot["insights"]:
                    color = self._get_sentiment_color(insight)
                    story.append(
                        Paragraph(
                            f'<para alignment="left"><font color="{color.hexval()}">•</font> {insight}</para>',
                            self.styles["MarketBulletPoint"],
                        )
                    )
                story.append(Spacer(1, 3))

            # Add technical data table
            if "snapshot" in snapshot:
                story.append(
                    Paragraph("Technical Indicators", self.styles["MarketSubHeader"])
                )
                table_data = [["Index", "Close", "Supp", "RSI", "MACD", "Sig"]]

                for index, data in snapshot["snapshot"].items():
                    close_val, close_color = self._format_currency(data["close"])
                    support_val, _ = self._format_currency(data["support"])

                    table_data.append(
                        [
                            index,
                            Paragraph(
                                f'<font color="{close_color.hexval()}">{close_val}</font>',
                                self.styles["MarketTableCell"],
                            ),
                            support_val,
                            f"{data['rsi']:.2f}",
                            f"{data['macd']['line']:.2f}",
                            f"{data['macd']['signal']:.2f}",
                        ]
                    )

                # More compact column widths
                table = Table(
                    table_data,
                    colWidths=[
                        1.2 * inch,
                        1.2 * inch,
                        1 * inch,
                        0.8 * inch,
                        1 * inch,
                        0.8 * inch,
                    ],
                )
                table.setStyle(self._create_table_style())
                story.append(table)

    def _add_institutional_activity(self, story):
        """Add institutional activity section"""
        story.append(
            Paragraph("Institutional Activity", self.styles["MarketSectionHeader"])
        )

        if "institutional_activity" in self.data:
            activity = self.data["institutional_activity"]

            # Add insights first
            if "insights" in activity:
                story.append(
                    Paragraph("Institutional Insights", self.styles["MarketSubHeader"])
                )
                self._add_insights(story, activity["insights"])
                story.append(Spacer(1, 3))

            # Add activity data table
            if "data" in activity:
                story.append(
                    Paragraph("FII/DII Activity", self.styles["MarketSubHeader"])
                )
                data = activity["data"]

                table_data = [["Category", "Buy", "Sell", "Net"]]

                for category, values in [("FII", data["fii"]), ("DII", data["dii"])]:
                    buy_val, _ = self._format_currency(
                        values["buy_value"], include_symbol=False
                    )
                    sell_val, _ = self._format_currency(
                        values["sell_value"], include_symbol=False
                    )
                    net_val, net_color = self._format_currency(
                        values["net_value"], include_symbol=False
                    )

                    table_data.append(
                        [
                            category,
                            buy_val,
                            sell_val,
                            Paragraph(
                                f'<font color="{net_color.hexval()}">{net_val}</font>',
                                self.styles["MarketTableCell"],
                            ),
                        ]
                    )

                # More compact column widths
                table = Table(
                    table_data,
                    colWidths=[1.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch],
                )
                table.setStyle(self._create_table_style())
                story.append(table)

    def _add_financial_indicators(self, story):
        """Add financial indicators section"""
        story.append(
            Paragraph("Financial Indicators", self.styles["MarketSectionHeader"])
        )

        if "financial_indicators" in self.data:
            indicators = self.data["financial_indicators"]

            # Add insights first if available
            if "_insights" in indicators:
                story.append(
                    Paragraph(
                        "Market Indicators Insights", self.styles["MarketSubHeader"]
                    )
                )
                self._add_insights(story, indicators["_insights"]["value"].split("\n"))
                story.append(Spacer(1, 3))

            # Add indicators table
            table_data = [["Indicator", "Value", "Chg", "Status"]]

            # Exclude the insights entry
            indicator_items = [
                (name, data) for name, data in indicators.items() if name != "_insights"
            ]

            for name, data in indicator_items:
                value = data.get("value", "N/A")
                change = data.get("percent_change", "N/A")
                status = data.get("remarks", "N/A")

                # Format value based on type
                if "₹" in str(value) or "$" in str(value):
                    value_txt, value_color = self._format_currency(value)
                else:
                    value_txt, value_color = str(value), self.neutral_color

                # Format change percentage
                change_txt, change_color = (
                    self._format_percentage(change)
                    if change != "N/A"
                    else ("N/A", self.neutral_color)
                )

                table_data.append(
                    [
                        name,
                        Paragraph(
                            f'<font color="{value_color.hexval()}">{value_txt}</font>',
                            self.styles["MarketTableCell"],
                        ),
                        Paragraph(
                            f'<font color="{change_color.hexval()}">{change_txt}</font>',
                            self.styles["MarketTableCell"],
                        ),
                        status,
                    ]
                )

            # More compact column widths
            table = Table(
                table_data, colWidths=[1.5 * inch, 1.5 * inch, 1 * inch, 1.5 * inch]
            )
            table.setStyle(self._create_table_style())
            story.append(table)

    def _add_summary_and_predictions(self, story):
        """Add market summary and predictions section"""
        # Add predictions
        if "market_predictions" in self.data:
            story.append(
                Paragraph("Market Predictions", self.styles["MarketSubHeader"])
            )
            for point in self.data["market_predictions"].split("\n"):
                if point.strip():
                    color = self._get_sentiment_color(point)
                    story.append(
                        Paragraph(
                            f'<para alignment="left"><font color="{color.hexval()}">►</font> {point.strip()}</para>',
                            self.styles["MarketBulletPoint"],
                        )
                    )

        # Add summary
        if "market_summary" in self.data:
            story.append(Paragraph("Market Summary", self.styles["MarketSubHeader"]))
            for point in self.data["market_summary"].split("\n"):
                if point.strip():
                    color = self._get_sentiment_color(point)
                    story.append(
                        Paragraph(
                            f'<para alignment="left"><font color="{color.hexval()}">•</font> {point.strip()}</para>',
                            self.styles["MarketBulletPoint"],
                        )
                    )
            story.append(Spacer(1, 3))


    def _add_disclaimer(self, story):
        """Add disclaimer at the end of the report"""
        disclaimer_text = """
        DISCLAIMER: This report is for informational purposes only and should not be considered as investment advice. 
        The data and analysis provided are based on publicly available information and may not be complete or accurate. 
        Past performance is not indicative of future results. Please consult with a qualified financial advisor before 
        making any investment decisions.
        """
        story.append(Spacer(1, 3))
        story.append(
            Paragraph(
                f'<para alignment="center"><font color="#666666" size="{self.body_size-1}">{disclaimer_text}</font></para>',
                self.styles["MarketBodyText"],
            )
        )

    def _add_insights(self, story, insights, bullet="•"):
        """Add insights with consistent styling"""
        if isinstance(insights, str):
            insights = insights.split("\n")

        for insight in insights:
            if insight.strip():
                color = self._get_sentiment_color(insight)
                story.append(
                    Paragraph(
                        f'<para alignment="left"><font color="{color.hexval()}">{bullet}</font> {insight.strip()}</para>',
                        self.styles["MarketBulletPoint"],
                    )
                )

    def generate(self, output_path):
        """Generate the comprehensive market report PDF"""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        story = []

        try:
            # Add title
            self._add_title(story)
            story.append(Spacer(1, 3))

            # Add all sections in sequence without page breaks
            sections = [
                self._add_summary_and_predictions,
                self._add_market_analysis,
                self._add_market_overview,
                self._add_sector_movement,
                self._add_top_performers,
                self._add_news_highlights,
                self._add_technical_snapshot,
                self._add_institutional_activity,
                self._add_financial_indicators,
            ]

            for section in sections:
                try:
                    section(story)
                    # Add a small spacer between sections
                    story.append(Spacer(1, 3))
                except Exception as e:
                    logger.error(f"Error in section {section.__name__}: {str(e)}")
                    story.append(
                        Paragraph(
                            f"Error generating {section.__name__.replace('_add_', '').replace('_', ' ').title()}",
                            self.styles["MarketBodyText"],
                        )
                    )

            # Add disclaimer
            self._add_disclaimer(story)

            # Build the PDF
            doc.build(story)

        except Exception as e:
            logger.error(f"Error generating comprehensive PDF: {str(e)}")
            raise
