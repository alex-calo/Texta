import logging
import os
from fpdf import FPDF
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class PDFGenerator:
    """
    Generates PDFs from OCR text or image snapshots, including structured output.
    """

    def __init__(self):
        logger.debug("PDFGenerator initialized.")

    def generate_pdf(self, content, output_path):
        """
        Save OCR text or image as a PDF file.
        Supports structured OCR text (tables, blocks) or image frames.
        :param content: str (OCR text with table/block annotations) or np.ndarray (image frame)
        :param output_path: output PDF file path
        """
        try:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)

            if isinstance(content, str):
                # Structured text OCR output
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                for line in content.split("\n"):
                    safe_line = line.encode("latin-1", errors="replace").decode("latin-1")
                    if "[TABLE CELL]" in safe_line:
                        # Optional: style table cells differently
                        pdf.set_font("Arial", style="B", size=12)
                        safe_line = safe_line.replace("[TABLE CELL]", "Cell: ")
                    else:
                        pdf.set_font("Arial", size=12)
                    pdf.multi_cell(0, 8, safe_line)
                pdf.output(output_path)
                logger.info(f"PDF with structured text saved: {output_path}")

            elif isinstance(content, np.ndarray):
                # Image snapshot
                image_path = os.path.splitext(output_path)[0] + "_temp.jpg"
                img = Image.fromarray(content)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(image_path)

                pdf.add_page()
                pdf.image(image_path, x=10, y=10, w=190)
                pdf.output(output_path)
                os.remove(image_path)
                logger.info(f"PDF with image snapshot saved: {output_path}")

            else:
                raise TypeError("Unsupported content type for PDF generation.")

        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
