from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import datetime
import os


def generate_pdf_from_news_highlights(data, pdf_file_path):
    """
    Generate a visually appealing PDF from news highlights data.
    Uses only standard ReportLab fonts to avoid font-related errors.
    """
    # Initialize canvas and set up dimensions
    c = canvas.Canvas(pdf_file_path, pagesize=letter)
    width, height = letter
    margin = 50
    content_width = width - (2 * margin)

    # Define colors for a professional look
    header_color = colors.HexColor("#1A5276")  # Deep blue
    subtitle_color = colors.HexColor("#2874A6")  # Medium blue
    text_color = colors.HexColor("#333333")  # Dark gray for main text
    highlight_color = colors.HexColor("#F39C12")  # Orange for highlights

    # Draw decorative header
    c.setFillColor(header_color)
    c.rect(0, height - 100, width, 100, fill=1)

    # Draw a decorative accent
    c.setFillColor(highlight_color)
    c.rect(margin, height - 110, content_width, 10, fill=1)

    # Add title
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(margin, height - 60, "NEWS HIGHLIGHTS REPORT")

    # Set up content area
    y_position = height - 130

    # Add timestamp
    c.setFillColor(text_color)
    timestamp = datetime.fromisoformat(data["timestamp"]).strftime("%d %B %Y, %I:%M %p")
    c.setFont("Helvetica", 11)  # Using standard Helvetica
    c.drawString(margin, y_position, f"Generated on: {timestamp}")
    y_position -= 30

    # Function to draw a section
    def draw_section(title, emoji, items, y_pos):
        # Section header with emoji
        c.setFillColor(header_color)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y_pos, f"{emoji} {title}")
        y_pos -= 8

        # Decorative underline
        c.setStrokeColor(subtitle_color)
        c.setLineWidth(1)
        c.line(margin, y_pos, margin + content_width, y_pos)
        y_pos -= 20

        # Draw items
        c.setFillColor(text_color)
        c.setFont("Helvetica", 10)

        for item in items:
            # Remove leading "- " if present
            if item.startswith("- "):
                item = item[2:]

            # Create text object for wrapping
            text = c.beginText(margin + 15, y_pos)
            text.setFont("Helvetica", 10)

            # Set up text with bullet point
            wrapped_lines = wrap_text(item, "Helvetica", 10, content_width - 15)

            # Add bullet point
            c.setFont("Helvetica-Bold", 12)
            c.drawString(margin, y_pos, "•")
            c.setFont("Helvetica", 10)

            # Draw first line
            if wrapped_lines:
                c.drawString(margin + 15, y_pos, wrapped_lines[0])
                line_height = 14

                # Draw remaining lines
                for i in range(1, len(wrapped_lines)):
                    y_pos -= line_height
                    c.drawString(margin + 15, y_pos, wrapped_lines[i])

            y_pos -= 20

        return y_pos

    # Helper function to wrap text
    def wrap_text(text, font_name, font_size, max_width):
        c.setFont(font_name, font_size)
        words = text.split()
        lines = []
        line = ""

        for word in words:
            test_line = f"{line} {word}".strip()
            width = c.stringWidth(test_line, font_name, font_size)

            if width <= max_width:
                line = test_line
            else:
                lines.append(line)
                line = word

        if line:
            lines.append(line)

        return lines

    # Draw sections
    y_position = draw_section("NEWS IMPACT", "📰", data["news_impact"], y_position)
    y_position -= 20

    # Check if we need a new page
    if y_position < 300:
        c.showPage()

        # Reset position and add header to new page
        y_position = height - 50

        # Add a smaller header on subsequent pages
        c.setFillColor(header_color)
        c.rect(0, height - 50, width, 50, fill=1)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, height - 30, "NEWS HIGHLIGHTS REPORT (CONTINUED)")

        y_position -= 60

    y_position = draw_section("INDIA NEWS", "🇮🇳", data["india_news"], y_position)
    y_position -= 20

    # Check if we need another new page
    if y_position < 300:
        c.showPage()

        # Reset position and add header to new page
        y_position = height - 50

        # Add a smaller header on subsequent pages
        c.setFillColor(header_color)
        c.rect(0, height - 50, width, 50, fill=1)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, height - 30, "NEWS HIGHLIGHTS REPORT (CONTINUED)")

        y_position -= 60

    y_position = draw_section("GLOBAL NEWS", "🌍", data["global_news"], y_position)

    # Add decorative footer
    c.setFillColor(header_color)
    c.rect(0, 0, width, 20, fill=1)

    # Add page numbers
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.white)
    page_num = c.getPageNumber()
    c.drawCentredString(width / 2, 7, f"Page {page_num}")

    # Save the PDF
    c.save()
