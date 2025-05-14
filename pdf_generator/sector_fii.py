from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from datetime import datetime


def analyze_sentiment(text):
    """
    Analyze sentiment in stock market text with expanded financial vocabulary.
    Returns appropriate symbol and color for the bullet point only.
    """
    text_lower = text.lower()

    # Expanded positive financial terms
    positive_terms = [
        "positive",
        "gain",
        "upward",
        "buying",
        "strength",
        "optimistic",
        "favorable",
        "growth",
        "bullish",
        "rally",
        "surge",
        "outperform",
        "upgrade",
        "support",
        "rebound",
        "recovery",
        "breakthrough",
        "momentum",
        "accumulation",
        "dividend",
        "profit",
        "earnings",
        "beat",
        "high",
        "up",
    ]

    # Expanded negative financial terms
    negative_terms = [
        "decline",
        "weak",
        "negative",
        "fall",
        "sell",
        "concern",
        "downward",
        "cautious",
        "bearish",
        "drop",
        "plunge",
        "underperform",
        "downgrade",
        "resistance",
        "correction",
        "slump",
        "recession",
        "deficit",
        "loss",
        "miss",
        "shortfall",
        "low",
        "down",
        "pressure",
        "volatile",
    ]

    # Check for positive sentiment
    if any(term in text_lower for term in positive_terms):
        return "🟢", colors.green
    # Check for negative sentiment
    elif any(term in text_lower for term in negative_terms):
        return "🔴", colors.red
    # Neutral sentiment - now blue instead of black
    else:
        return "🔵", colors.blue


def create_table(c, data, headers, x, y, width, col_widths=None):
    """
    Create a visually appealing formatted table with proper rows and columns
    """
    if not col_widths:
        col_widths = [width / len(headers)] * len(headers)

    # Create table data including headers
    table_data = [headers] + data

    # Create table
    table = Table(table_data, colWidths=col_widths)

    # Style the table with more visual appeal
    style = TableStyle(
        [
            # Header styling
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.darkblue),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            # Row styling - alternating row colors for better readability
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            # Handle the case where there might not be enough rows
            # Add conditional background colors only if those rows exist
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            (
                "LINEBELOW",
                (0, 0),
                (-1, 0),
                1.5,
                colors.darkblue,
            ),  # Thicker line below header
            # Content alignment
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 1), (0, -1), "LEFT"),  # First column left aligned
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),  # Other columns centered
            # Padding for all cells
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
    )

    # Add alternating row colors only if they exist
    for row_num in [2, 4, 6]:
        if row_num < len(table_data):
            style.add("BACKGROUND", (0, row_num), (-1, row_num), colors.whitesmoke)

    # Add conditional formatting for positive/negative values with indicators
    for i in range(1, len(table_data)):
        # Sector table formatting
        if (
            col_widths and len(col_widths) > 4 and len(table_data[i]) > 4
        ):  # For sector table
            change_col = 4
            try:
                change_text = table_data[i][change_col]
                if change_text and "+" in change_text:
                    # Add green arrow for positive
                    table_data[i][change_col] = f"▲ {change_text}"
                    style.add(
                        "TEXTCOLOR", (change_col, i), (change_col, i), colors.green
                    )
                    style.add(
                        "BACKGROUND",
                        (change_col, i),
                        (change_col, i),
                        colors.lightgreen,
                    )
                elif change_text and "-" in change_text:
                    # Add red arrow for negative
                    table_data[i][change_col] = f"▼ {change_text}"
                    style.add("TEXTCOLOR", (change_col, i), (change_col, i), colors.red)
                    style.add(
                        "BACKGROUND", (change_col, i), (change_col, i), colors.mistyrose
                    )
                else:
                    # Neutral value (approximately zero)
                    table_data[i][change_col] = f"◆ {change_text}"
                    style.add(
                        "TEXTCOLOR", (change_col, i), (change_col, i), colors.blue
                    )
            except (IndexError, ValueError, TypeError):
                pass  # Skip if column doesn't exist or isn't a numeric value

        # FII/DII table formatting
        elif (
            col_widths and len(col_widths) > 3 and len(table_data[i]) > 3
        ):  # For FII/DII table
            net_col = 3
            try:
                net_text = table_data[i][net_col]
                if net_text and "-" not in str(net_text):  # Positive or zero
                    # Add green arrow for positive
                    table_data[i][net_col] = f"▲ {net_text}"
                    style.add("TEXTCOLOR", (net_col, i), (net_col, i), colors.green)
                    style.add(
                        "BACKGROUND", (net_col, i), (net_col, i), colors.lightgreen
                    )
                else:
                    # Add red arrow for negative
                    table_data[i][net_col] = f"▼ {net_text}"
                    style.add("TEXTCOLOR", (net_col, i), (net_col, i), colors.red)
                    style.add(
                        "BACKGROUND", (net_col, i), (net_col, i), colors.mistyrose
                    )
            except (IndexError, ValueError, TypeError):
                pass  # Skip if column doesn't exist or isn't a numeric value

    table.setStyle(style)

    # Draw the table
    table.wrapOn(c, width, 500)
    table.drawOn(c, x, y - table._height)

    return y - table._height - 20  # Return new y position


def format_currency(value):
    """Format currency values with commas and prefix"""
    try:
        if isinstance(value, str):
            value = float(value.replace(",", ""))

        abs_value = abs(value)
        prefix = "" if value >= 0 else "-"

        if abs_value >= 10000000000:  # Billion+
            return f"{prefix}₹{abs_value/10000000000:.2f}B"
        elif abs_value >= 10000000:  # Crore+
            return f"{prefix}₹{abs_value/10000000:.2f}Cr"
        elif abs_value >= 100000:  # Lakh+
            return f"{prefix}₹{abs_value/100000:.2f}L"
        else:
            return f"{prefix}₹{abs_value:,.2f}"
    except (ValueError, TypeError):
        return str(value)


def generate_sector_fii_pdf(data, pdf_file_path):
    """Generate a well-formatted PDF report with properly styled tables and colored bullet points"""
    c = canvas.Canvas(pdf_file_path, pagesize=letter)
    width, height = letter
    margin = 50
    available_width = width - 2 * margin
    y_position = height - 50

    # Title with box
    c.setFillColor(colors.lightgrey)
    c.rect(margin - 10, y_position - 10, available_width + 20, 40, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y_position, "Sector & FII/DII Report")
    y_position -= 25

    # Timestamp with formatting
    c.setFont("Helvetica-Oblique", 10)
    timestamp = datetime.fromisoformat(data["timestamp"]).strftime("%d %B %Y, %I:%M %p")
    c.drawString(margin, y_position, f"Generated on: {timestamp}")
    y_position -= 30

    # 1. Sector Insights with colored bullets
    c.setFillColor(colors.blue)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y_position, "📌 Sector Insights:")
    y_position -= 20
    c.setFillColor(colors.black)

    # Parse insights with colored bullets (only bullet is colored, not text)
    c.setFont("Helvetica", 10)
    # Check if sector_movement exists and has insight
    if "sector_movement" in data and "insight" in data["sector_movement"]:
        for line in data["sector_movement"]["insight"].split("\n"):
            if not line.strip():
                continue
            bullet, bullet_color = analyze_sentiment(line)

            # Draw colored bullet first
            c.setFillColor(bullet_color)
            c.drawString(margin, y_position, bullet)

            # Then draw the text in black
            c.setFillColor(colors.black)
            c.drawString(margin + 15, y_position, line.strip())
            y_position -= 15
    else:
        c.drawString(margin, y_position, "No sector insights available.")
        y_position -= 15
    c.setFillColor(colors.black)

    # 2. Sector Movement Table
    y_position -= 20
    c.setFillColor(colors.blue)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y_position, "📊 Sector Movement Summary:")
    y_position -= 20
    c.setFillColor(colors.black)

    # Create sector table data
    headers = ["Sector", "Companies", "Advances", "Declines", "Change (%)"]
    col_widths = [
        available_width * 0.4,
        available_width * 0.15,
        available_width * 0.15,
        available_width * 0.15,
        available_width * 0.15,
    ]

    table_data = []
    # Check if sector_movement exists and has data
    if "sector_movement" in data and "data" in data["sector_movement"]:
        for sector in data["sector_movement"]["data"]:
            # Safely access data fields
            sector_name = sector.get("sector_name", "Unknown")
            num_companies = sector.get("num_companies", 0)
            advances = sector.get("advances", 0)
            declines = sector.get("declines", 0)
            change = sector.get("change_percentage", 0)

            table_data.append(
                [
                    sector_name,
                    str(num_companies),
                    str(advances),
                    str(declines),
                    f"{change:+.2f}%" if isinstance(change, (int, float)) else "0.00%",
                ]
            )

    if not table_data:
        table_data = [["No data available", "-", "-", "-", "0.00%"]]

    # Draw sector table
    y_position = create_table(
        c, table_data, headers, margin, y_position, available_width, col_widths
    )

    # Check if we need a new page for FII/DII section
    if y_position < 250:
        c.showPage()
        y_position = height - 50

    # 3. FII/DII Insights with colored bullets
    c.setFillColor(colors.blue)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y_position, "📌 FII/DII Insights:")
    y_position -= 20
    c.setFillColor(colors.black)

    c.setFont("Helvetica", 10)
    # Check if institutional_activity exists and has insight
    if "institutional_activity" in data and "insight" in data["institutional_activity"]:
        for line in data["institutional_activity"]["insight"].split("\n"):
            if not line.strip():
                continue
            bullet, bullet_color = analyze_sentiment(line)

            # Draw colored bullet first
            c.setFillColor(bullet_color)
            c.drawString(margin, y_position, bullet)

            # Then draw the text in black
            c.setFillColor(colors.black)
            c.drawString(margin + 15, y_position, line.strip())
            y_position -= 15
    else:
        c.drawString(
            margin, y_position, "No institutional activity insights available."
        )
        y_position -= 15
    c.setFillColor(colors.black)

    # 4. FII/DII Table
    y_position -= 20
    c.setFillColor(colors.blue)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y_position, "📊 Institutional Activity Summary:")
    y_position -= 20
    c.setFillColor(colors.black)

    headers = ["Entity", "Buy Value", "Sell Value", "Net Value"]
    table_data = []

    # Check if institutional_activity exists and has data
    if (
        "institutional_activity" in data
        and "data" in data["institutional_activity"]
        and "fii" in data["institutional_activity"]["data"]
        and "dii" in data["institutional_activity"]["data"]
    ):

        fii = data["institutional_activity"]["data"]["fii"]
        dii = data["institutional_activity"]["data"]["dii"]

        # Safely access data with defaults
        fii_buy = format_currency(fii.get("buy_value", 0))
        fii_sell = format_currency(fii.get("sell_value", 0))
        fii_net = format_currency(fii.get("net_value", 0))
        dii_buy = format_currency(dii.get("buy_value", 0))
        dii_sell = format_currency(dii.get("sell_value", 0))
        dii_net = format_currency(dii.get("net_value", 0))

        table_data = [
            ["FII", fii_buy, fii_sell, fii_net],
            ["DII", dii_buy, dii_sell, dii_net],
        ]
    else:
        table_data = [
            ["FII", "₹0.00", "₹0.00", "₹0.00"],
            ["DII", "₹0.00", "₹0.00", "₹0.00"],
        ]

    col_widths = [
        available_width * 0.25,
        available_width * 0.25,
        available_width * 0.25,
        available_width * 0.25,
    ]

    # Draw FII/DII table
    y_position = create_table(
        c, table_data, headers, margin, y_position, available_width, col_widths
    )

    # Footer with source and disclaimer
    y_position -= 20
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(margin, y_position, "Source: Trendlyne, MoneyControl")
    y_position -= 15
    c.drawString(
        margin,
        y_position,
        "Disclaimer: This report is for informational purposes only and should not be considered as investment advice.",
    )

    c.save()
