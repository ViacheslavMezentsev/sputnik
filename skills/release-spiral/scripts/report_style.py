"""Оформление PDF спирали (ReportLab): шрифт DejaVu из matplotlib, заголовки, таблицы, рисунки."""
import os

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Table, TableStyle

_FONTS = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
for name, file in (("DV", "DejaVuSans.ttf"), ("DV-B", "DejaVuSans-Bold.ttf"), ("DV-I", "DejaVuSans-Oblique.ttf")):
    pdfmetrics.registerFont(TTFont(name, os.path.join(_FONTS, file)))

W, H = A4
LM = RM = 18 * mm
CONTENT_W = W - LM - RM
BLUE, HEAD_BG, GRID, GREY = (colors.HexColor(c) for c in ("#1F4E79", "#DCE6F2", "#9DB3CC", "#555555"))
S = {
    "title": ParagraphStyle("title", fontName="DV-B", fontSize=19, leading=24, textColor=BLUE, spaceAfter=4),
    "sub": ParagraphStyle("sub", fontName="DV", fontSize=10.5, leading=14, spaceAfter=3),
    "date": ParagraphStyle("date", fontName="DV-B", fontSize=10.5, leading=14, textColor=BLUE, spaceAfter=4),
    "h1": ParagraphStyle("h1", fontName="DV-B", fontSize=12.5, leading=16, textColor=BLUE, spaceBefore=10,
                         spaceAfter=5, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="DV-B", fontSize=10.5, leading=14, textColor=BLUE, spaceBefore=7,
                         spaceAfter=4, keepWithNext=1),
    "body": ParagraphStyle("body", fontName="DV", fontSize=8.6, leading=11.6, spaceAfter=3, alignment=TA_LEFT),
    "bullet": ParagraphStyle("bullet", fontName="DV", fontSize=8.6, leading=11.6, leftIndent=10, spaceAfter=1.5),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=7.6, leading=9.6),
    "cellb": ParagraphStyle("cellb", fontName="DV-B", fontSize=7.6, leading=9.6),
    "cap": ParagraphStyle("cap", fontName="DV-I", fontSize=7.8, leading=10, textColor=GREY, spaceBefore=2, spaceAfter=6),
    "data": ParagraphStyle("data", fontName="DV", fontSize=7.2, leading=9.2, textColor=GREY, spaceAfter=4),
}


def P(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items):
    return [Paragraph(t, S["bullet"], bulletText="•") for t in items]


def num(x, nd=1):
    s = f"{x:.{nd}f}".replace(".", ",")
    return s.replace("-", "−")


def table(rows, widths):
    data = [[Paragraph(str(c), S["cellb" if i == 0 else "cell"]) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[CONTENT_W * w for w in widths], repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return t


def figure(path, caption, frac=1.0):
    from PIL import Image as PI
    im = PI.open(path)
    w = CONTENT_W * frac
    return KeepTogether([Image(path, width=w, height=w * im.height / im.width), Paragraph(caption, S["cap"])])


def build(path, story, footer, title):
    def on_page(canv, doc):
        canv.saveState()
        canv.setFont("DV", 7)
        canv.setFillColor(GREY)
        canv.drawString(LM, 10 * mm, footer)
        canv.drawRightString(W - RM, 10 * mm, f"Стр. {doc.page}")
        canv.restoreState()
    SimpleDocTemplate(path, pagesize=A4, leftMargin=LM, rightMargin=RM, topMargin=16 * mm, bottomMargin=18 * mm,
                      title=title, author="", creator="").build(story, onFirstPage=on_page, onLaterPages=on_page)
