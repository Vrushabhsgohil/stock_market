from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER


def generate_financial_indicators_pdf(data: dict, pdf_path: str):
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor("#2F5597"),
    )

    header_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#2F5597"),
    )

    # Title
    title = Paragraph("Financial Indicators Report", title_style)
    elements.append(title)
    elements.append(Spacer(1, 6))

    # Timestamp
    timestamp = Paragraph(
        f"Last Updated: {data.get('last_updated', '')}", styles["Normal"]
    )
    elements.append(timestamp)
    elements.append(Spacer(1, 12))

    indicators = data.get("indicators", {}).copy()
    insights_block = indicators.pop("_insights", None)

    # Add insights section first (string only)
    if insights_block and hasattr(insights_block, "value"):
        insights_header = Paragraph("Insights", header_style)
        elements.append(insights_header)
        elements.append(Spacer(1, 6))

        # Process insights text to ensure proper bullet points
        insights_text = insights_block.value

        # Split by lines that start with dash
        insight_lines = insights_text.split("\n")

        # Create a bullet style
        bullet_style = ParagraphStyle(
            "BulletPoint",
            parent=styles["BodyText"],
            leftIndent=20,
            spaceBefore=3,
            spaceAfter=3,
        )

        for line in insight_lines:
            line = line.strip()
            if line:
                # Check if line starts with a dash and remove it
                if line.startswith("- "):
                    line = line[2:]
                # Add bullet point
                bullet_point = Paragraph(f"• {line}", bullet_style)
                elements.append(bullet_point)

        elements.append(Spacer(1, 15))

    # Market Indicators header
    indicators_header = Paragraph("Market Indicators", header_style)
    elements.append(indicators_header)
    elements.append(Spacer(1, 6))

    # Table headers
    table_data = [["Indicator", "Value", "% Change", "Remarks"]]

    # Add indicator rows (handling Pydantic model objects)
    for name, item in indicators.items():
        row = [
            name,
            getattr(item, "value", "N/A"),
            getattr(item, "percent_change", "N/A"),
            getattr(item, "remarks", "N/A"),
        ]
        table_data.append(row)

    # Enhanced table styling
    table = Table(table_data, colWidths=[150, 100, 100, 150])
    table.setStyle(
        TableStyle(
            [
                # Header styling
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2F5597")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                # Cell styling
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                (
                    "TEXTCOLOR",
                    (0, 1),
                    (0, -1),
                    colors.HexColor("#2F5597"),
                ),  # Blue indicator names
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                # Alternating row colors
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F2F2F2")),
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#F2F2F2")),
                ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#F2F2F2")),
                ("BACKGROUND", (0, 7), (-1, 7), colors.HexColor("#F2F2F2")),
                # Cell padding
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(table)

    # Build the PDF
    doc.build(elements)
