from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime


def generate_top_performers_pdf(data: dict, pdf_path: str):
    # Create document
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=1 * cm,
        rightMargin=1 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    elements = []

    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor("#2F5597"),
        spaceAfter=0.3 * cm,
    )

    date_style = ParagraphStyle(
        "DateStyle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.gray,
        alignment=TA_LEFT,
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#2F5597"),
        spaceAfter=0.2 * cm,
    )

    insight_style = ParagraphStyle(
        "Insight",
        parent=styles["BodyText"],
        fontSize=11,
        leftIndent=0.5 * cm,
        firstLineIndent=-0.3 * cm,
        leading=14,  # Line spacing
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.gray,
        alignment=TA_CENTER,
    )

    # Document Title
    title = Paragraph("Top Market Performers", title_style)
    elements.append(title)

    # Current Date
    date_str = datetime.now().strftime("%B %d, %Y")
    date_para = Paragraph(f"Generated on: {date_str}", date_style)
    elements.append(date_para)
    elements.append(Spacer(1, 0.5 * cm))

    # Market Insights Section (Moved to top)
    insight_text = data["top_performers"].get("insight", "No insights available")
    if insight_text:
        insight_title = Paragraph("Market Insights", heading_style)
        elements.append(insight_title)

        # Process each insight point
        for point in insight_text.split("\n"):
            if point.strip():
                # The insight lines already start with "- ", so we'll replace with a bullet
                if point.startswith("- "):
                    point = point[2:]  # Remove existing dash
                insight_para = Paragraph(f"• {point.strip()}", insight_style)
                elements.append(insight_para)

        elements.append(Spacer(1, 0.8 * cm))

    # Top Gainers Section
    gainers_title = Paragraph("Top Gainers", heading_style)
    elements.append(gainers_title)
    elements.append(Spacer(1, 0.3 * cm))

    # Create gainers table
    gainers_data = data["top_performers"].get("top_gainers", [])
    if gainers_data:
        gainers_table_data = [
            ["Rank", "Company", "Current Price (₹)", "Change (₹)", "Change (%)"]
        ]

        for i, company in enumerate(gainers_data):
            gainers_table_data.append(
                [
                    i + 1,
                    company["company_name"],
                    f"{company['current_price']:.2f}",
                    f"+{company['price_change']:.2f}",
                    f"+{company['percentage_change']:.1f}%",
                ]
            )

        gainers_table = Table(gainers_table_data, colWidths=[30, 180, 90, 80, 80])
        gainers_table.setStyle(
            TableStyle(
                [
                    # Header styling
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#4CAF50"),
                    ),  # Green for gainers
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    # Data styling
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("ALIGN", (0, 1), (0, -1), "CENTER"),  # Rank centered
                    ("ALIGN", (2, 1), (-1, -1), "RIGHT"),  # Numbers right-aligned
                    # Cell borders and backgrounds
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        1,
                        colors.HexColor("#4CAF50"),
                    ),  # Green border
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F0FFF0")],
                    ),  # Light green alternating
                    # Padding
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        elements.append(gainers_table)
    else:
        elements.append(Paragraph("No top gainers data available", styles["Normal"]))

    elements.append(Spacer(1, 0.8 * cm))

    # Top Losers Section
    losers_title = Paragraph("Top Losers", heading_style)
    elements.append(losers_title)
    elements.append(Spacer(1, 0.3 * cm))

    # Create losers table
    losers_data = data["top_performers"].get("top_losers", [])
    if losers_data:
        losers_table_data = [
            ["Rank", "Company", "Current Price (₹)", "Change (₹)", "Change (%)"]
        ]

        for i, company in enumerate(losers_data):
            losers_table_data.append(
                [
                    i + 1,
                    company["company_name"],
                    f"{company['current_price']:.2f}",
                    f"{company['price_change']:.2f}",
                    f"{company['percentage_change']:.1f}%",
                ]
            )

        losers_table = Table(losers_table_data, colWidths=[30, 180, 90, 80, 80])
        losers_table.setStyle(
            TableStyle(
                [
                    # Header styling
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#F44336"),
                    ),  # Red for losers
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    # Data styling
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("ALIGN", (0, 1), (0, -1), "CENTER"),  # Rank centered
                    ("ALIGN", (2, 1), (-1, -1), "RIGHT"),  # Numbers right-aligned
                    # Cell borders and backgrounds
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        1,
                        colors.HexColor("#F44336"),
                    ),  # Red border
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#FFF0F0")],
                    ),  # Light red alternating
                    # Padding
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        elements.append(losers_table)
    else:
        elements.append(Paragraph("No top losers data available", styles["Normal"]))

    # Footer
    elements.append(Spacer(1, 1 * cm))
    footer_text = Paragraph(
        "This report is automatically generated using market data. For informational purposes only. Not financial advice.",
        footer_style,
    )
    elements.append(footer_text)

    # Build the PDF
    doc.build(elements)
