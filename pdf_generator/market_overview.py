from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus.tables import TableStyle
import os


class MarketOverviewPDFGenerator:
    def __init__(self, market_data):
        """
        Initialize the PDF generator with market overview data

        :param market_data: Dictionary containing market overview information
        """
        self.market_data = market_data
        self.styles = getSampleStyleSheet()

        # Create custom styles with fallback to Normal style
        self.custom_title = ParagraphStyle(
            "CustomTitle",
            parent=self.styles["Normal"],
            fontSize=16,
            textColor=colors.blue,
            alignment=1,  # Center alignment
            fontName="Helvetica-Bold",
        )

        self.custom_subtitle = ParagraphStyle(
            "CustomSubtitle",
            parent=self.styles["Normal"],
            fontSize=12,
            textColor=colors.darkgray,
            alignment=1,  # Center alignment
            fontName="Helvetica",
        )

        self.custom_insights = ParagraphStyle(
            "CustomInsights",
            parent=self.styles["Normal"],
            fontSize=10,
            leading=14,  # Line height
            spaceAfter=6,
            textColor=colors.black,
        )

        self.custom_heading = ParagraphStyle(
            "CustomHeading",
            parent=self.styles["Normal"],
            fontSize=12,
            textColor=colors.blue,
            spaceAfter=6,
            fontName="Helvetica-Bold",
        )

    def create_indices_table(self, data):
        """
        Create a table of market indices with color-coding for positive/negative changes

        :param data: Market data dictionary
        :return: Table element
        """
        # Prepare table data
        table_data = [["Index", "Open", "High", "Low", "Close", "Change", "Change %"]]

        # Exclude _meta from indices
        indices = {k: v for k, v in data.items() if k != "_meta"}

        # Store rows with positive and negative changes for color coding
        positive_rows = []
        negative_rows = []

        row_num = 1  # Start from row 1 (after header)
        for symbol, index_data in indices.items():
            table_data.append(
                [
                    str(symbol),
                    f"{index_data['Open']:.2f}",
                    f"{index_data['High']:.2f}",
                    f"{index_data['Low']:.2f}",
                    f"{index_data['Close']:.2f}",
                    f"{index_data['Change']:.2f}",
                    f"{index_data['Change%']:.2f}%",
                ]
            )

            # Record row for color coding based on change value
            if index_data["Change"] > 0:
                positive_rows.append(row_num)
            elif index_data["Change"] < 0:
                negative_rows.append(row_num)

            row_num += 1

        # Create table
        table = Table(table_data, repeatRows=1, colWidths=[1 * inch] * 7)

        # Basic table styling
        table_style = [
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.blue,
            ),  # Changed header background to blue
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
        ]

        # Add color coding for positive changes (green text for Change and Change% columns only)
        for row in positive_rows:
            # Color only the Change and Change% columns (5 and 6)
            table_style.append(("TEXTCOLOR", (5, row), (6, row), colors.green))
            table_style.append(("FONTNAME", (5, row), (6, row), "Helvetica-Bold"))

        # Add color coding for negative changes (red text for Change and Change% columns only)
        for row in negative_rows:
            # Color only the Change and Change% columns (5 and 6)
            table_style.append(("TEXTCOLOR", (5, row), (6, row), colors.red))
            table_style.append(("FONTNAME", (5, row), (6, row), "Helvetica-Bold"))

        table.setStyle(TableStyle(table_style))

        return table

    def generate(self, output_path):
        """
        Generate the market overview PDF

        :param output_path: Path to save the generated PDF
        """
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=18,
        )

        # Story to build PDF
        story = []

        # Title
        title = Paragraph(
            f"Market Overview Report - {self.market_data['date']}", self.custom_title
        )
        story.append(title)
        story.append(Spacer(1, 12))

        # Timestamp
        timestamp = Paragraph(
            f"Generated at: {self.market_data['timestamp']}", self.custom_subtitle
        )
        story.append(timestamp)
        story.append(Spacer(1, 24))  # Add more space before insights

        # Market Insights (NOW FIRST)
        insights_title = Paragraph("Market Insights", self.custom_heading)
        story.append(insights_title)

        # Split insights into paragraphs if too long
        insights_paras = self.market_data["insights"].split(". ")
        for para in insights_paras:
            if para.strip():  # Ensure non-empty paragraphs
                insights_para = Paragraph(para.strip() + ".", self.custom_insights)
                story.append(insights_para)

        story.append(Spacer(1, 18))  # Add space after insights

        # Indices Table (NOW SECOND)
        table_title = Paragraph("Market Indices", self.custom_heading)
        story.append(table_title)
        story.append(Spacer(1, 6))

        indices_table = self.create_indices_table(self.market_data["market_data"])
        story.append(indices_table)

        # Build PDF
        doc.build(story)
