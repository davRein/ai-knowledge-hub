"""Rebuild the original CC0 portfolio PDF. Needs pip install -e '.[portfolio]'."""

import json
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    source = json.loads((ROOT / "examples/atlas-handbook.json").read_text(encoding="utf-8"))
    output = ROOT / "examples/atlas-handbook.pdf"
    width, height = A4
    ink, accent = colors.HexColor("#17263C"), colors.HexColor("#6352CC")
    style = ParagraphStyle("body", fontName="Helvetica", fontSize=12, leading=19, textColor=ink)
    pdf = Canvas(str(output), pagesize=A4, invariant=1)
    pdf.setTitle(source["title"])
    pdf.setAuthor("AI Knowledge Hub - synthetic CC0 example")
    for number, page in enumerate(source["pages"], 1):
        pdf.setFillColor(accent)
        pdf.rect(0, height - 14, width, 14, fill=1, stroke=0)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, height - 57, "AI KNOWLEDGE HUB / SYNTHETIC DEMO")
        pdf.setFillColor(ink)
        pdf.setFont("Helvetica-Bold", 28)
        pdf.drawString(50, height - 115, page["title"])
        pdf.setFont("Helvetica", 13)
        pdf.drawString(50, height - 143, page["subtitle"])
        pdf.setFillColor(colors.HexColor("#F2F0FC"))
        pdf.roundRect(50, height - 209, width - 100, 38, 7, fill=1, stroke=0)
        pdf.setFillColor(accent)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(64, height - 194, "FICTIONAL SAMPLE - no real people or company policies")
        y = height - 260
        for fact in page["facts"]:
            pdf.setFillColor(accent)
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(50, y, fact["label"].upper())
            paragraph = Paragraph(escape(fact["text"]), style)
            _, text_height = paragraph.wrap(width - 100, 140)
            paragraph.drawOn(pdf, 50, y - 17 - text_height)
            y -= text_height + 67
        if y <= 100:
            raise ValueError("Content would overlap the footer")
        pdf.setStrokeColor(colors.HexColor("#DCE2EB"))
        pdf.line(50, 74, width - 50, 74)
        pdf.setFillColor(ink)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(50, 53, "CC0 1.0 / creativecommons.org/publicdomain/zero/1.0/")
        pdf.drawRightString(width - 50, 53, f"Page {number} of 3")
        pdf.showPage()
    pdf.save()
    print(f"Created {output}")


if __name__ == "__main__":
    main()
