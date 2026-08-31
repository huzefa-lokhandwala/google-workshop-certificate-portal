import io
import os
from typing import Optional
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from backend.app.config import get_settings

settings = get_settings()

_registered_fonts = set()


def register_custom_font_if_needed(font_name: str, font_path: Optional[str] = None):
    if font_path and os.path.exists(font_path) and font_name not in _registered_fonts:
        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            _registered_fonts.add(font_name)
        except Exception as e:
            pass


class CertificateGenerationError(Exception):
    pass


def calculate_optimal_font_size(
    text: str,
    font_name: str,
    base_font_size: int,
    max_allowed_width: float
) -> int:
    """
    Calculates the best font size so that the name never overflows the certificate placeholder line.
    """
    try:
        current_width = stringWidth(text, font_name, base_font_size)
    except Exception:
        # If font calculation fails, fallback to Helvetica-Bold
        current_width = stringWidth(text, "Helvetica-Bold", base_font_size)
    
    if current_width <= max_allowed_width:
        return base_font_size

    scale_factor = max_allowed_width / current_width
    scaled_size = int(base_font_size * scale_factor)
    return max(scaled_size, 14)  # Ensure minimum readable size


def create_name_overlay(
    name: str,
    page_width: float,
    page_height: float,
    x: Optional[float] = None,
    y: Optional[float] = None,
    font_name: Optional[str] = None,
    font_size: Optional[int] = None,
    text_color_hex: Optional[str] = None,
    text_align: Optional[str] = None
) -> io.BytesIO:
    """
    Creates a single-page transparent PDF in memory with the participant's name
    positioned at (x, y).
    """
    if settings.CERTIFICATE_CUSTOM_FONT_PATH:
        register_custom_font_if_needed(
            settings.CERTIFICATE_NAME_FONT,
            settings.CERTIFICATE_CUSTOM_FONT_PATH
        )

    x = x if x is not None else settings.CERTIFICATE_NAME_X
    y = y if y is not None else settings.CERTIFICATE_NAME_Y
    font_name = font_name or settings.CERTIFICATE_NAME_FONT
    base_font_size = font_size or settings.CERTIFICATE_NAME_FONT_SIZE
    text_color_hex = text_color_hex or settings.CERTIFICATE_NAME_COLOR
    text_align = (text_align or settings.CERTIFICATE_TEXT_ALIGN).lower()

    # Automatically scale font size if the name is too long for the allocated width
    active_font_size = calculate_optimal_font_size(
        text=name,
        font_name=font_name,
        base_font_size=base_font_size,
        max_allowed_width=settings.CERTIFICATE_NAME_MAX_WIDTH
    )

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))
    
    # Set font & color
    try:
        can.setFont(font_name, active_font_size)
    except Exception:
        can.setFont("Helvetica-Bold", active_font_size)

    try:
        text_color = colors.HexColor(text_color_hex)
    except Exception:
        text_color = colors.HexColor("#1e293b")
    
    can.setFillColor(text_color)

    # Draw text according to alignment
    if text_align == "center":
        can.drawCentredString(x, y, name)
    elif text_align == "right":
        can.drawRightString(x, y, name)
    else:
        can.drawString(x, y, name)

    can.save()
    packet.seek(0)
    return packet


def generate_certificate_pdf(
    participant_name: str,
    template_path: Optional[str] = None,
    x: Optional[float] = None,
    y: Optional[float] = None,
    font_size: Optional[int] = None
) -> bytes:
    """
    Overlays participant_name onto the template PDF and returns the merged PDF bytes.
    Does not write temporary files to disk.
    """
    path = template_path or settings.CERTIFICATE_TEMPLATE_PATH
    if not os.path.isabs(path):
        base_dir = os.getcwd()
        resolved_path = os.path.join(base_dir, path)
        if not os.path.exists(resolved_path):
            this_dir = os.path.dirname(os.path.abspath(__file__))
            candidate = os.path.normpath(os.path.join(this_dir, "..", "..", "..", path))
            if os.path.exists(candidate):
                resolved_path = candidate
        path = resolved_path

    if not os.path.exists(path):
        raise CertificateGenerationError(f"Certificate template not found at '{path}'")

    try:
        reader = PdfReader(path)
        if len(reader.pages) == 0:
            raise CertificateGenerationError("Certificate template has no pages.")

        page_index = min(settings.CERTIFICATE_PAGE, len(reader.pages) - 1)
        template_page = reader.pages[page_index]

        page_width = float(template_page.mediabox.width)
        page_height = float(template_page.mediabox.height)

        overlay_stream = create_name_overlay(
            name=participant_name,
            page_width=page_width,
            page_height=page_height,
            x=x,
            y=y,
            font_size=font_size
        )

        overlay_reader = PdfReader(overlay_stream)
        overlay_page = overlay_reader.pages[0]

        writer = PdfWriter()
        for idx, page in enumerate(reader.pages):
            if idx == page_index:
                page.merge_page(overlay_page)
            writer.add_page(page)

        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)
        return output_stream.getvalue()

    except Exception as e:
        if isinstance(e, CertificateGenerationError):
            raise
        raise CertificateGenerationError(f"Failed to generate certificate PDF: {str(e)}") from e
