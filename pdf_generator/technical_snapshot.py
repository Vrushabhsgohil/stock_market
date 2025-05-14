from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime


def generate_technical_snapshot_pdf(data: dict, pdf_path: str):
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=1 * cm,
        rightMargin=1 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    elements = []

    # Create custom styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor("#2F5597"),
        spaceAfter=0.3 * cm,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.gray,
        alignment=TA_CENTER,
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
        leftIndent=0.3 * cm,
        firstLineIndent=-0.3 * cm,
    )

    date_style = ParagraphStyle(
        "DateStyle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.gray,
        alignment=TA_LEFT,
    )

    # Title
    title = Paragraph("Technical Market Snapshot", title_style)
    elements.append(title)

    # Date
    date_para = Paragraph(
        f"Generated on: {data.get('date', datetime.now().strftime('%B %d, %Y'))}",
        date_style,
    )
    elements.append(date_para)
    elements.append(Spacer(1, 0.5 * cm))

    # Insights section (moved to top)
    insights = data.get("insights", [])
    if insights:
        insights_title = Paragraph("Insights", heading_style)
        elements.append(insights_title)

        for point in insights:
            insight_para = Paragraph(f"• {point}", insight_style)
            elements.append(insight_para)
            elements.append(Spacer(1, 0.2 * cm))

        elements.append(Spacer(1, 0.5 * cm))

    # Market data section
    market_title = Paragraph("Market Data", heading_style)
    elements.append(market_title)
    elements.append(Spacer(1, 0.3 * cm))

    snapshot = data.get("snapshot", {})

    # Table headers
    table_data = [["Index", "Close", "Support", "RSI", "MACD Line", "MACD Signal"]]

    # Populate table data
    for index_name, values in snapshot.items():
        row = [
            index_name,
            values.get("close", "N/A"),
            values.get("support", "N/A"),
            values.get("rsi", "N/A"),
            values.get("macd", {}).get("line", "N/A"),
            values.get("macd", {}).get("signal", "N/A"),
        ]
        table_data.append(row)

    # Create table with improved styling
    table = Table(table_data, colWidths=[100, 80, 80, 60, 80, 80])
    table.setStyle(
        TableStyle(
            [
                # Header styling
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2F5597")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                # Cell borders
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#2F5597")),
                # Row styling - alternating colors
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F2F6FC")],
                ),
                # Content alignment
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                # Padding
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elements.append(table)

    # Footer
    elements.append(Spacer(1, 1 * cm))
    footer_text = Paragraph(
        "This report is generated automatically using market data and AI analytics.",
        subtitle_style,
    )
    elements.append(footer_text)

    # Build PDF
    doc.build(elements)
