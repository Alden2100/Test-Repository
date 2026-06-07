"""
PDF Dashboard Builder
Generates a professional 2-page investment research brief.
Page 1: Cover — company header, verdict, key metrics scorecard
Page 2: Full analysis — financial details, valuation, risk, macro
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import Flowable
import os
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# COLOR PALETTE
# ─────────────────────────────────────────────────────────────────────────────
NAVY       = colors.HexColor("#0D1B2A")
DARK_BLUE  = colors.HexColor("#1B3A5C")
MID_BLUE   = colors.HexColor("#2E6DA4")
LIGHT_BLUE = colors.HexColor("#D6E8F7")
ACCENT     = colors.HexColor("#1B7FE0")
GREEN      = colors.HexColor("#1A7F4F")
GREEN_BG   = colors.HexColor("#E6F4EC")
RED        = colors.HexColor("#C0392B")
RED_BG     = colors.HexColor("#FDECEA")
ORANGE     = colors.HexColor("#D97706")
ORANGE_BG  = colors.HexColor("#FEF3C7")
GRAY_DARK  = colors.HexColor("#374151")
GRAY_MID   = colors.HexColor("#6B7280")
GRAY_LIGHT = colors.HexColor("#F3F4F6")
GRAY_LINE  = colors.HexColor("#E5E7EB")
WHITE      = colors.white
BLACK      = colors.black


# ─────────────────────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────────────────────
def make_styles():
    return {
        "cover_ticker": ParagraphStyle("cover_ticker",
            fontName="Helvetica-Bold", fontSize=42, textColor=WHITE,
            leading=48, alignment=TA_LEFT),
        "cover_company": ParagraphStyle("cover_company",
            fontName="Helvetica", fontSize=16, textColor=colors.HexColor("#A8C8E8"),
            leading=22, alignment=TA_LEFT),
        "cover_date": ParagraphStyle("cover_date",
            fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#A8C8E8"),
            leading=14, alignment=TA_LEFT),
        "verdict_label": ParagraphStyle("verdict_label",
            fontName="Helvetica-Bold", fontSize=11, textColor=GRAY_MID,
            leading=14, alignment=TA_CENTER, spaceAfter=2),
        "verdict_value": ParagraphStyle("verdict_value",
            fontName="Helvetica-Bold", fontSize=22, textColor=NAVY,
            leading=26, alignment=TA_CENTER),
        "section_header": ParagraphStyle("section_header",
            fontName="Helvetica-Bold", fontSize=11, textColor=DARK_BLUE,
            leading=16, spaceBefore=14, spaceAfter=6,
            borderPadding=(0, 0, 4, 0)),
        "body": ParagraphStyle("body",
            fontName="Helvetica", fontSize=9, textColor=GRAY_DARK,
            leading=14, spaceAfter=4),
        "body_small": ParagraphStyle("body_small",
            fontName="Helvetica", fontSize=8, textColor=GRAY_MID,
            leading=12),
        "bullet": ParagraphStyle("bullet",
            fontName="Helvetica", fontSize=9, textColor=GRAY_DARK,
            leading=13, leftIndent=10, firstLineIndent=-10, spaceAfter=3),
        "metric_label": ParagraphStyle("metric_label",
            fontName="Helvetica", fontSize=8, textColor=GRAY_MID,
            leading=11, alignment=TA_LEFT),
        "metric_value": ParagraphStyle("metric_value",
            fontName="Helvetica-Bold", fontSize=11, textColor=NAVY,
            leading=14, alignment=TA_LEFT),
        "tag": ParagraphStyle("tag",
            fontName="Helvetica-Bold", fontSize=8, textColor=WHITE,
            leading=11, alignment=TA_CENTER),
        "footer": ParagraphStyle("footer",
            fontName="Helvetica", fontSize=7, textColor=GRAY_MID,
            leading=10, alignment=TA_CENTER),
        "page2_title": ParagraphStyle("page2_title",
            fontName="Helvetica-Bold", fontSize=13, textColor=NAVY,
            leading=18, spaceAfter=8),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM FLOWABLES
# ─────────────────────────────────────────────────────────────────────────────
class ColorRect(Flowable):
    """A filled rectangle with optional text."""
    def __init__(self, width, height, fill_color, radius=4):
        super().__init__()
        self.width = width
        self.height = height
        self.fill_color = fill_color
        self.radius = radius

    def draw(self):
        self.canv.setFillColor(self.fill_color)
        self.canv.roundRect(0, 0, self.width, self.height, self.radius, fill=1, stroke=0)


class ScoreBar(Flowable):
    """A visual score bar (1-10)."""
    def __init__(self, score, width=120, height=8, label=""):
        super().__init__()
        self.score = score
        self.width = width
        self.height = height
        self.label = label

    def draw(self):
        c = self.canv
        # Background
        c.setFillColor(GRAY_LIGHT)
        c.roundRect(0, 0, self.width, self.height, 3, fill=1, stroke=0)
        # Fill
        pct = min(max(self.score / 10.0, 0), 1)
        if pct > 0.7:
            bar_color = GREEN
        elif pct > 0.4:
            bar_color = ACCENT
        else:
            bar_color = RED
        c.setFillColor(bar_color)
        c.roundRect(0, 0, self.width * pct, self.height, 3, fill=1, stroke=0)


class CoverCanvas:
    """Handles background drawing for cover page."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def risk_color(level: str):
    if level == "High":
        return RED, RED_BG
    elif level == "Moderate":
        return ORANGE, ORANGE_BG
    else:
        return GREEN, GREEN_BG


def verdict_color(verdict: str):
    v = verdict.lower()
    if "attractive" in v or "undervalued" in v:
        return GREEN, GREEN_BG
    elif "expensive" in v or "elevated" in v:
        return RED, RED_BG
    else:
        return ACCENT, LIGHT_BLUE


def score_to_color(score: float):
    if score >= 7:
        return GREEN
    elif score >= 4.5:
        return ACCENT
    else:
        return RED


def bullet_para(text: str, styles, color=None) -> Paragraph:
    prefix = "• " if not text.startswith("•") else ""
    style = styles["bullet"]
    if color:
        return Paragraph(f'<font color="{color.hexval() if hasattr(color, "hexval") else color}">{prefix}{text}</font>', style)
    return Paragraph(f"{prefix}{text}", style)


def section_divider():
    return HRFlowable(width="100%", thickness=0.5, color=GRAY_LINE, spaceAfter=6, spaceBefore=2)


def metric_row(label: str, value: str, styles, value_color=None) -> Table:
    label_p = Paragraph(label, styles["metric_label"])
    val_style = ParagraphStyle("mv_custom", parent=styles["metric_value"],
        textColor=value_color if value_color else NAVY)
    value_p = Paragraph(str(value), val_style)
    t = Table([[label_p, value_p]], colWidths=[2.2*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


# ─────────────────────────────────────────────────────────────────────────────
# PAGE BACKGROUND CANVAS
# ─────────────────────────────────────────────────────────────────────────────
class PageBackground:
    def __init__(self, ticker, company_name, as_of, total_pages=2):
        self.ticker = ticker
        self.company_name = company_name
        self.as_of = as_of
        self.total_pages = total_pages
        self._page_num = [0]

    def on_first_page(self, c, doc):
        self._page_num[0] = 1
        w, h = letter
        # Dark navy header band
        c.setFillColor(NAVY)
        c.rect(0, h - 2.2*inch, w, 2.2*inch, fill=1, stroke=0)
        # Accent stripe
        c.setFillColor(ACCENT)
        c.rect(0, h - 2.2*inch - 0.06*inch, w, 0.06*inch, fill=1, stroke=0)
        # Ticker
        c.setFont("Helvetica-Bold", 44)
        c.setFillColor(WHITE)
        c.drawString(0.6*inch, h - 1.05*inch, self.ticker)
        # Company name
        c.setFont("Helvetica", 15)
        c.setFillColor(colors.HexColor("#A8C8E8"))
        c.drawString(0.6*inch, h - 1.45*inch, self.company_name)
        # Date
        c.setFont("Helvetica", 9)
        c.drawString(0.6*inch, h - 1.75*inch, f"Research Brief  ·  {self.as_of}")
        # Report label top-right
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#6B9CC8"))
        c.drawRightString(w - 0.6*inch, h - 0.9*inch, "INVESTMENT RESEARCH")
        c.setFont("Helvetica", 8)
        c.drawRightString(w - 0.6*inch, h - 1.1*inch, "Confidential · Internal Use Only")
        # Footer
        c.setFillColor(GRAY_LINE)
        c.rect(0, 0, w, 0.4*inch, fill=1, stroke=0)
        c.setFont("Helvetica", 7)
        c.setFillColor(GRAY_MID)
        c.drawString(0.6*inch, 0.15*inch, "For internal use only. Not investment advice. Source data: SEC EDGAR, Yahoo Finance.")
        c.drawRightString(w - 0.6*inch, 0.15*inch, f"Page 1 of {self.total_pages}")

    def on_later_pages(self, c, doc):
        self._page_num[0] += 1
        w, h = letter
        # Slim header band
        c.setFillColor(NAVY)
        c.rect(0, h - 0.55*inch, w, 0.55*inch, fill=1, stroke=0)
        c.setFillColor(ACCENT)
        c.rect(0, h - 0.55*inch - 0.04*inch, w, 0.04*inch, fill=1, stroke=0)
        # Header text
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(WHITE)
        c.drawString(0.6*inch, h - 0.37*inch, f"{self.ticker}  —  Full Analysis")
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#A8C8E8"))
        c.drawRightString(w - 0.6*inch, h - 0.37*inch, self.as_of)
        # Footer
        c.setFillColor(GRAY_LINE)
        c.rect(0, 0, w, 0.4*inch, fill=1, stroke=0)
        c.setFont("Helvetica", 7)
        c.setFillColor(GRAY_MID)
        c.drawString(0.6*inch, 0.15*inch, "For internal use only. Not investment advice. Source data: SEC EDGAR, Yahoo Finance.")
        c.drawRightString(w - 0.6*inch, 0.15*inch, f"Page {self._page_num[0]} of {self.total_pages}")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1: COVER CONTENT
# ─────────────────────────────────────────────────────────────────────────────
def build_cover(financial: dict, return_data: dict, risk: dict, macro: dict, styles: dict, ai: dict = None) -> list:
    story = []
    w, h = letter
    col_w = (w - 1.2*inch) / 3  # For 3-column scorecard

    # Space below header band
    story.append(Spacer(1, 2.4*inch))

    # ── VERDICT SCORECARD (3 columns) ──────────────────────────────────────
    val_verdict = return_data.get("valuation", {}).get("verdict", "N/A")
    val_c, val_bg = verdict_color(val_verdict)
    
    risk_level = risk.get("overall_risk", "N/A")
    risk_c, risk_bg = risk_color(risk_level)
    
    fin_assessment = financial.get("health_assessment", "N/A")
    fin_score = financial.get("health_score", 5)
    fin_c = score_to_color(fin_score)
    fin_bg = GREEN_BG if fin_score >= 7 else (ORANGE_BG if fin_score >= 4.5 else RED_BG)

    def verdict_cell(label, value, bg_color, text_color):
        label_p = Paragraph(label.upper(), ParagraphStyle("vl",
            fontName="Helvetica", fontSize=8, textColor=GRAY_MID,
            leading=11, alignment=TA_CENTER))
        value_p = Paragraph(value, ParagraphStyle("vv",
            fontName="Helvetica-Bold", fontSize=18, textColor=text_color,
            leading=22, alignment=TA_CENTER))
        inner = Table([[label_p], [value_p]], colWidths=[col_w - 0.3*inch])
        inner.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        cell_table = Table([[inner]], colWidths=[col_w - 0.1*inch])
        cell_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_color),
            ("ROUNDEDCORNERS", [6]),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return cell_table

    scorecard = Table(
        [[
            verdict_cell("Valuation", val_verdict, val_bg, val_c),
            verdict_cell("Risk Profile", risk_level, risk_bg, risk_c),
            verdict_cell("Financial Health", fin_assessment, fin_bg, fin_c),
        ]],
        colWidths=[col_w, col_w, col_w],
        hAlign="LEFT"
    )
    scorecard.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(scorecard)
    story.append(Spacer(1, 0.25*inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LINE))
    story.append(Spacer(1, 0.15*inch))

    # ── KEY METRICS (2-column grid) ─────────────────────────────────────────
    story.append(Paragraph("KEY METRICS", ParagraphStyle("km_hdr",
        fontName="Helvetica-Bold", fontSize=9, textColor=GRAY_MID,
        leading=12, spaceAfter=8)))

    half_w = (w - 1.2*inch) / 2

    def metric_cell(label, value, val_color=NAVY):
        lp = Paragraph(label, ParagraphStyle("ml", fontName="Helvetica",
            fontSize=8, textColor=GRAY_MID, leading=11))
        vp = Paragraph(str(value), ParagraphStyle("mv", fontName="Helvetica-Bold",
            fontSize=13, textColor=val_color, leading=17))
        return [lp, vp]

    price = return_data.get("current_price_fmt", "N/A")
    mkt_cap_raw = return_data.get("market_cap")
    if mkt_cap_raw:
        try:
            mc = float(mkt_cap_raw)
            if mc >= 1e12:
                mkt_cap_fmt = f"${mc/1e12:.2f}T"
            elif mc >= 1e9:
                mkt_cap_fmt = f"${mc/1e9:.1f}B"
            else:
                mkt_cap_fmt = f"${mc/1e6:.0f}M"
        except Exception:
            mkt_cap_fmt = "N/A"
    else:
        mkt_cap_fmt = "N/A"

    pe = return_data.get("pe_ratio_fmt", "N/A")
    fwd_pe = return_data.get("forward_pe_fmt", "N/A")
    ev_ebitda = return_data.get("ev_ebitda_fmt", "N/A")
    rev_ttm = financial.get("revenue_ttm_fmt", "N/A")
    op_margin = financial.get("operating_margin_fmt", "N/A")
    fcf = financial.get("free_cashflow_fmt", "N/A")
    roe = financial.get("roe_fmt", "N/A")
    beta = risk.get("beta_fmt", "N/A")
    div_yield = return_data.get("dividend_yield_fmt", "N/A")
    positioning = return_data.get("positioning_52w", {})
    pos_label = positioning.get("label", "N/A")

    metrics_data = [
        [metric_cell("Current Price", price), metric_cell("Market Cap", mkt_cap_fmt)],
        [metric_cell("Trailing P/E", pe), metric_cell("Forward P/E", fwd_pe)],
        [metric_cell("EV / EBITDA", ev_ebitda), metric_cell("Revenue (TTM)", rev_ttm)],
        [metric_cell("Operating Margin", op_margin), metric_cell("Free Cash Flow (TTM)", fcf)],
        [metric_cell("Return on Equity", roe), metric_cell("Beta", beta)],
        [metric_cell("Dividend Yield", div_yield), metric_cell("52-Week Position", pos_label)],
    ]

    # Flatten into table rows
    flat_rows = []
    for row in metrics_data:
        flat_rows.append([row[0][0], row[0][1], row[1][0], row[1][1]])
        flat_rows.append([Spacer(1, 4), "", Spacer(1, 4), ""])

    metrics_table = Table(flat_rows, colWidths=[1.5*inch, 1.2*inch, 1.5*inch, 1.2*inch])
    metrics_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LINEAFTER", (1, 0), (1, -1), 0.5, GRAY_LINE),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 0.2*inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LINE))
    story.append(Spacer(1, 0.12*inch))

    # ── EXECUTIVE SUMMARY (AI-generated) ────────────────────────────────────
    if ai and ai.get("executive_summary"):
        story.append(Paragraph("EXECUTIVE SUMMARY", ParagraphStyle("es_hdr",
            fontName="Helvetica-Bold", fontSize=9, textColor=GRAY_MID,
            leading=12, spaceAfter=6)))
        story.append(Paragraph(ai["executive_summary"], ParagraphStyle("es_body",
            fontName="Helvetica", fontSize=9.5, textColor=GRAY_DARK,
            leading=15, spaceAfter=0)))
        story.append(Spacer(1, 0.15*inch))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LINE))
        story.append(Spacer(1, 0.12*inch))

    # ── QUICK TAKE ──────────────────────────────────────────────────────────
    story.append(Paragraph("QUICK TAKE", ParagraphStyle("qt_hdr",
        fontName="Helvetica-Bold", fontSize=9, textColor=GRAY_MID,
        leading=12, spaceAfter=8)))

    # Use AI quick take bullets if available, otherwise fall back to structured data
    if ai and ai.get("quick_take_bullets"):
        color_map = {
            "val": val_c, "risk": risk_c, "fin": GREEN, "macro": ACCENT
        }
        quick_bullets = [
            (tag, text, color_map.get(color_hint, ACCENT))
            for tag, text, color_hint in ai["quick_take_bullets"]
        ]
    else:
        quick_bullets = []
        val_signals = return_data.get("valuation", {}).get("signals", [])
        if val_signals:
            quick_bullets.append(("Valuation", val_signals[0], val_c))
        top_risks = risk.get("top_risks", [])
        if top_risks:
            quick_bullets.append(("Risk", top_risks[0], risk_c))
        health_pos = financial.get("health_positives", [])
        if health_pos:
            quick_bullets.append(("Financials", health_pos[0], GREEN))
        tailwinds = macro.get("tailwinds", [])
        if tailwinds:
            quick_bullets.append(("Macro", tailwinds[0], ACCENT))

    for tag_label, text, tag_color in quick_bullets:
        tag_p = Paragraph(tag_label, ParagraphStyle("tag_inner",
            fontName="Helvetica-Bold", fontSize=7, textColor=WHITE,
            leading=9, alignment=TA_CENTER))
        text_p = Paragraph(text, ParagraphStyle("qt_body",
            fontName="Helvetica", fontSize=9, textColor=GRAY_DARK, leading=13))
        row_t = Table([[tag_p, text_p]], colWidths=[0.7*inch, w - 1.2*inch - 0.7*inch - 0.15*inch])
        row_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), tag_color),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (0, 0), 4),
            ("RIGHTPADDING", (0, 0), (0, 0), 4),
            ("LEFTPADDING", (1, 0), (1, 0), 8),
            ("ROUNDEDCORNERS", [4]),
        ]))
        story.append(row_t)
        story.append(Spacer(1, 5))

    return story


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2: FULL ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
def build_analysis_page(financial: dict, return_data: dict, risk: dict, macro: dict, styles: dict, ai: dict = None) -> list:
    story = []
    story.append(PageBreak())
    story.append(Spacer(1, 0.65*inch))

    w, h = letter
    col_w = (w - 1.2*inch - 0.2*inch) / 2  # Two-column layout

    # ── LEFT COLUMN content
    left_col = []

    # FINANCIAL ANALYSIS
    left_col.append(Paragraph("FINANCIAL ANALYSIS", styles["section_header"]))
    left_col.append(section_divider())

    fin_rows = [
        ["Revenue (TTM)", financial.get("revenue_ttm_fmt", "N/A")],
        ["EBITDA", financial.get("ebitda_fmt", "N/A")],
        ["Free Cash Flow", financial.get("free_cashflow_fmt", "N/A")],
        ["Gross Margin", financial.get("gross_margin_fmt", "N/A")],
        ["Operating Margin", financial.get("operating_margin_fmt", "N/A")],
        ["Net Profit Margin", financial.get("profit_margin_fmt", "N/A")],
        ["Return on Equity", financial.get("roe_fmt", "N/A")],
        ["Return on Assets", financial.get("roa_fmt", "N/A")],
        ["Revenue Growth YoY", financial.get("revenue_growth_yoy_fmt", "N/A")],
        ["Earnings Growth YoY", financial.get("earnings_growth_yoy_fmt", "N/A")],
        ["Total Debt", financial.get("total_debt_fmt", "N/A")],
        ["Net Cash / (Debt)", financial.get("net_cash_fmt", "N/A")],
    ]

    fin_table_data = []
    for label, val in fin_rows:
        lp = Paragraph(label, ParagraphStyle("fin_label", fontName="Helvetica",
            fontSize=8.5, textColor=GRAY_DARK, leading=12))
        vp = Paragraph(str(val), ParagraphStyle("fin_val", fontName="Helvetica-Bold",
            fontSize=8.5, textColor=NAVY, leading=12, alignment=TA_RIGHT))
        fin_table_data.append([lp, vp])

    fin_table = Table(fin_table_data, colWidths=[col_w * 0.62, col_w * 0.38])
    fin_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, GRAY_LINE),
        ("BACKGROUND", (0, 0), (-1, 0), GRAY_LIGHT),
        ("BACKGROUND", (0, 2), (-1, 2), GRAY_LIGHT),
        ("BACKGROUND", (0, 4), (-1, 4), GRAY_LIGHT),
        ("BACKGROUND", (0, 6), (-1, 6), GRAY_LIGHT),
        ("BACKGROUND", (0, 8), (-1, 8), GRAY_LIGHT),
        ("BACKGROUND", (0, 10), (-1, 10), GRAY_LIGHT),
    ]))
    left_col.append(fin_table)

    # FINANCIAL HEALTH HIGHLIGHTS
    left_col.append(Spacer(1, 10))
    health_score = financial.get("health_score", 5)
    health_color = score_to_color(health_score)
    
    left_col.append(Paragraph("FINANCIAL HEALTH SIGNALS", ParagraphStyle("fh_hdr",
        fontName="Helvetica-Bold", fontSize=9, textColor=GRAY_MID,
        leading=12, spaceBefore=10, spaceAfter=6)))

    for pos in financial.get("health_positives", []):
        left_col.append(Paragraph(f'<font color="#1A7F4F">✓</font>  {pos}',
            styles["bullet"]))
    for flag in financial.get("health_flags", []):
        left_col.append(Paragraph(f'<font color="#C0392B">!</font>  {flag}',
            styles["bullet"]))

    # ── RIGHT COLUMN content
    right_col = []

    # VALUATION & RETURN ANALYSIS
    right_col.append(Paragraph("VALUATION & RETURN ANALYSIS", styles["section_header"]))
    right_col.append(section_divider())

    val = return_data.get("valuation", {})
    val_verdict = val.get("verdict", "N/A")
    val_c, val_bg = verdict_color(val_verdict)

    # Verdict box
    verdict_box = Table(
        [[Paragraph(f'Verdict: <font color="{val_c.hexval() if hasattr(val_c, "hexval") else "#000"}">{val_verdict}</font>',
            ParagraphStyle("verd", fontName="Helvetica-Bold", fontSize=11,
            textColor=NAVY, leading=14))]],
        colWidths=[col_w]
    )
    verdict_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), val_bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [5]),
    ]))
    right_col.append(verdict_box)
    right_col.append(Spacer(1, 6))

    val_rows = [
        ["Metric", "Value", "Sector Avg"],
        ["Trailing P/E", return_data.get("pe_ratio_fmt", "N/A"),
         f"{val.get('benchmarks_used', {}).get('pe', 'N/A')}x"],
        ["Forward P/E", return_data.get("forward_pe_fmt", "N/A"), "—"],
        ["EV/EBITDA", return_data.get("ev_ebitda_fmt", "N/A"),
         f"{val.get('benchmarks_used', {}).get('ev_ebitda', 'N/A')}x"],
        ["EV/Revenue", return_data.get("ev_revenue_fmt", "N/A"),
         f"{val.get('benchmarks_used', {}).get('ev_rev', 'N/A')}x"],
        ["P/Book", return_data.get("price_to_book_fmt", "N/A"), "—"],
        ["PEG Ratio", return_data.get("peg_ratio_fmt", "N/A"), "< 1.0 favorable"],
    ]

    header_style = ParagraphStyle("val_hdr", fontName="Helvetica-Bold",
        fontSize=8, textColor=GRAY_MID, leading=11)
    cell_style = ParagraphStyle("val_cell", fontName="Helvetica",
        fontSize=8.5, textColor=GRAY_DARK, leading=12)
    bold_cell = ParagraphStyle("val_bold", fontName="Helvetica-Bold",
        fontSize=8.5, textColor=NAVY, leading=12)

    val_table_data = []
    for i, row in enumerate(val_rows):
        if i == 0:
            val_table_data.append([Paragraph(c, header_style) for c in row])
        else:
            val_table_data.append([
                Paragraph(row[0], cell_style),
                Paragraph(row[1], bold_cell),
                Paragraph(row[2], ParagraphStyle("bench", fontName="Helvetica",
                    fontSize=8, textColor=GRAY_MID, leading=12))
            ])

    val_table = Table(val_table_data, colWidths=[col_w*0.42, col_w*0.28, col_w*0.30])
    val_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, ACCENT),
    ]))
    right_col.append(val_table)
    right_col.append(Spacer(1, 8))

    # Valuation signals
    for sig in val.get("signals", [])[:3]:
        right_col.append(Paragraph(f"• {sig}", styles["bullet"]))

    right_col.append(Spacer(1, 8))

    # AI valuation commentary
    if ai and ai.get("valuation_commentary"):
        right_col.append(Paragraph("ANALYST VIEW", ParagraphStyle("av_hdr",
            fontName="Helvetica-Bold", fontSize=8.5, textColor=ACCENT,
            leading=12, spaceAfter=3)))
        right_col.append(Paragraph(ai["valuation_commentary"], ParagraphStyle("av_body",
            fontName="Helvetica-Oblique", fontSize=8.5, textColor=GRAY_DARK,
            leading=13, spaceAfter=0)))

    right_col.append(Spacer(1, 8))
    pos = return_data.get("positioning_52w", {})
    right_col.append(Paragraph("52-WEEK POSITIONING", ParagraphStyle("pos_hdr",
        fontName="Helvetica-Bold", fontSize=9, textColor=GRAY_MID,
        leading=12, spaceAfter=5)))

    pos_row = [
        Paragraph(f'Low: {pos.get("low_fmt", "N/A")}', styles["body_small"]),
        Paragraph(f'Current: {return_data.get("current_price_fmt", "N/A")}  ({pos.get("position_pct_fmt", "")})',
            ParagraphStyle("pos_cur", fontName="Helvetica-Bold", fontSize=8,
            textColor=NAVY, leading=11, alignment=TA_CENTER)),
        Paragraph(f'High: {pos.get("high_fmt", "N/A")}', ParagraphStyle("pos_right",
            fontName="Helvetica", fontSize=8, textColor=GRAY_MID,
            leading=11, alignment=TA_RIGHT)),
    ]
    pos_table = Table([pos_row], colWidths=[col_w*0.25, col_w*0.5, col_w*0.25])
    pos_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    right_col.append(pos_table)
    right_col.append(Spacer(1, 4))

    # Progress bar (visual approximation)
    pos_pct = pos.get("position_pct", 0.5) or 0.5
    bar_data = [[
        Paragraph("", styles["body_small"]),
    ]]
    right_col.append(ScoreBar(pos_pct * 10, width=col_w, height=7))
    right_col.append(Spacer(1, 8))

    # RISK ANALYSIS
    right_col.append(Paragraph("RISK ANALYSIS", styles["section_header"]))
    right_col.append(section_divider())

    overall_risk = risk.get("overall_risk", "N/A")
    risk_c, risk_bg = risk_color(overall_risk)

    risk_header = Table([[
        Paragraph("Overall Risk:", ParagraphStyle("rh", fontName="Helvetica",
            fontSize=9, textColor=GRAY_DARK, leading=12)),
        Paragraph(overall_risk, ParagraphStyle("rv", fontName="Helvetica-Bold",
            fontSize=11, textColor=risk_c, leading=14)),
        Paragraph(f"Score: {risk.get('risk_score', 'N/A')}/10",
            ParagraphStyle("rs", fontName="Helvetica", fontSize=9,
            textColor=GRAY_MID, leading=12, alignment=TA_RIGHT)),
    ]], colWidths=[0.8*inch, 1.0*inch, col_w - 1.8*inch])
    risk_header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), risk_bg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4]),
    ]))
    right_col.append(risk_header)
    right_col.append(Spacer(1, 6))

    risk_dims = [
        ("Leverage", risk.get("leverage", {}).get("risk_level", "N/A"),
         risk.get("leverage", {}).get("details", ["N/A"])[0] if risk.get("leverage", {}).get("details") else "N/A"),
        ("Volatility", risk.get("volatility", {}).get("risk_level", "N/A"),
         risk.get("volatility", {}).get("details", ["N/A"])[0] if risk.get("volatility", {}).get("details") else "N/A"),
        ("Profitability", risk.get("profitability_risk", {}).get("risk_level", "N/A"),
         risk.get("profitability_risk", {}).get("details", ["N/A"])[0] if risk.get("profitability_risk", {}).get("details") else "N/A"),
        ("Short Interest", risk.get("short_interest", {}).get("risk_level", "N/A"),
         risk.get("short_interest", {}).get("details", ["N/A"])[0] if risk.get("short_interest", {}).get("details") else "N/A"),
    ]

    for dim_label, dim_risk, dim_detail in risk_dims:
        rc, rb = risk_color(dim_risk)
        dim_table = Table([[
            Paragraph(dim_label, ParagraphStyle("dl", fontName="Helvetica-Bold",
                fontSize=8, textColor=GRAY_DARK, leading=11)),
            Paragraph(dim_risk, ParagraphStyle("dr", fontName="Helvetica-Bold",
                fontSize=8, textColor=rc, leading=11, alignment=TA_CENTER)),
            Paragraph(dim_detail[:70] + ("..." if len(dim_detail) > 70 else ""),
                ParagraphStyle("dd", fontName="Helvetica", fontSize=7.5,
                textColor=GRAY_MID, leading=11)),
        ]], colWidths=[0.8*inch, 0.55*inch, col_w - 1.35*inch - 0.1*inch])
        dim_table.setStyle(TableStyle([
            ("BACKGROUND", (1, 0), (1, 0), rb),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRAY_LINE),
        ]))
        right_col.append(dim_table)

    right_col.append(Spacer(1, 6))

    # AI risk narrative
    if ai and ai.get("risk_narrative"):
        right_col.append(Paragraph("ANALYST VIEW", ParagraphStyle("rv_hdr",
            fontName="Helvetica-Bold", fontSize=8.5, textColor=ACCENT,
            leading=12, spaceAfter=3)))
        right_col.append(Paragraph(ai["risk_narrative"], ParagraphStyle("rv_body",
            fontName="Helvetica-Oblique", fontSize=8.5, textColor=GRAY_DARK,
            leading=13, spaceAfter=0)))

    right_col.append(Spacer(1, 8))

    # AI investment considerations (bull / bear)
    if ai and ai.get("investment_considerations"):
        right_col.append(Paragraph("INVESTMENT CONSIDERATIONS", styles["section_header"]))
        right_col.append(section_divider())
        for side, point in ai["investment_considerations"]:
            if side == "bull":
                right_col.append(Paragraph(
                    f'<font color="#1A7F4F">▲ Bull:</font>  {point}',
                    styles["bullet"]))
            else:
                right_col.append(Paragraph(
                    f'<font color="#C0392B">▼ Bear:</font>  {point}',
                    styles["bullet"]))
        right_col.append(Spacer(1, 8))

    # MACRO CONTEXT
    right_col.append(Paragraph("MACRO & INDUSTRY CONTEXT", styles["section_header"]))
    right_col.append(section_divider())

    right_col.append(Paragraph(f"Sector: {macro.get('sector_label', 'N/A')}  ·  Rate Env: {macro.get('rate_environment', 'N/A')}  ·  Cycle: {macro.get('cycle_stage', 'N/A')}",
        styles["body_small"]))
    right_col.append(Spacer(1, 6))

    right_col.append(Paragraph("Tailwinds", ParagraphStyle("tw_hdr",
        fontName="Helvetica-Bold", fontSize=8.5, textColor=GREEN, leading=12, spaceAfter=3)))
    for tw in macro.get("tailwinds", [])[:2]:
        right_col.append(Paragraph(f'<font color="#1A7F4F">↑</font>  {tw}', styles["bullet"]))

    right_col.append(Spacer(1, 4))
    right_col.append(Paragraph("Headwinds", ParagraphStyle("hw_hdr",
        fontName="Helvetica-Bold", fontSize=8.5, textColor=RED, leading=12, spaceAfter=3)))
    for hw in macro.get("headwinds", [])[:2]:
        right_col.append(Paragraph(f'<font color="#C0392B">↓</font>  {hw}', styles["bullet"]))

    right_col.append(Spacer(1, 4))
    right_col.append(Paragraph(f"Key Watch: {macro.get('key_watch', 'N/A')}",
        ParagraphStyle("kw", fontName="Helvetica-Oblique", fontSize=8,
        textColor=GRAY_MID, leading=12)))

    # ── ASSEMBLE TWO-COLUMN LAYOUT ──────────────────────────────────────────
    # Interleave left and right content in pairs to avoid single-table overflow
    # Each logical section becomes its own paired row
    max_len = max(len(left_col), len(right_col))
    # Pad shorter column
    while len(left_col) < max_len:
        left_col.append(Spacer(1, 1))
    while len(right_col) < max_len:
        right_col.append(Spacer(1, 1))

    # Build rows in chunks of ~8 flowables to prevent overflow
    chunk = 8
    for i in range(0, max_len, chunk):
        lchunk = left_col[i:i+chunk]
        rchunk = right_col[i:i+chunk]
        two_col = Table(
            [[lchunk, rchunk]],
            colWidths=[col_w, col_w],
        )
        two_col.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (0, -1), 0),
            ("RIGHTPADDING", (0, 0), (0, -1), 12),
            ("LEFTPADDING", (1, 0), (1, -1), 12),
            ("RIGHTPADDING", (1, 0), (1, -1), 0),
            ("LINEAFTER", (0, 0), (0, -1), 0.5, GRAY_LINE),
        ]))
        story.append(two_col)

    # ── DISCLOSURE ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.2*inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LINE))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This report is generated by an AI research tool and is for internal informational purposes only. "
        "It does not constitute investment advice. All data sourced from SEC EDGAR and Yahoo Finance. "
        "Verify all figures against primary sources before making any investment decision.",
        styles["body_small"]))

    return story


# ─────────────────────────────────────────────────────────────────────────────
# MASTER BUILD FUNCTION
# ─────────────────────────────────────────────────────────────────────────────
def build_pdf(financial: dict, return_data: dict, risk: dict, macro: dict,
              output_path: str, ai: dict = None) -> str:
    """
    Build the complete 2-page PDF dashboard.
    ai: optional dict of AI-generated commentary from ai_analyst.py
    Returns the output path.
    """
    ticker = financial.get("ticker", "UNKNOWN")
    company_name = financial.get("company_name", ticker)
    as_of = financial.get("as_of") or datetime.now().strftime("%B %d, %Y")

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.6*inch,
        rightMargin=0.6*inch,
        topMargin=0.3*inch,
        bottomMargin=0.5*inch,
    )

    styles = make_styles()
    bg = PageBackground(ticker, company_name, as_of, total_pages=2)

    story = []
    story += build_cover(financial, return_data, risk, macro, styles, ai=ai)
    story += build_analysis_page(financial, return_data, risk, macro, styles, ai=ai)

    doc.build(story,
              onFirstPage=bg.on_first_page,
              onLaterPages=bg.on_later_pages)

    print(f"[pdf_builder] PDF saved → {output_path}")
    return output_path


if __name__ == "__main__":
    # Quick smoke test with dummy data
    dummy_financial = {
        "ticker": "DEMO", "company_name": "Demo Corporation",
        "as_of": "June 6, 2025",
        "revenue_ttm_fmt": "$45.2B", "ebitda_fmt": "$12.1B", "free_cashflow_fmt": "$8.3B",
        "gross_margin_fmt": "62.1%", "operating_margin_fmt": "24.3%", "profit_margin_fmt": "18.5%",
        "roe_fmt": "32.1%", "roa_fmt": "14.2%",
        "revenue_growth_yoy_fmt": "+12.4%", "earnings_growth_yoy_fmt": "+18.7%",
        "total_debt_fmt": "$22.0B", "net_cash_fmt": "-$8.5B",
        "health_score": 7.5, "health_assessment": "Strong",
        "health_positives": ["Strong operating margin (24.3%)", "Positive free cash flow ($8.3B)"],
        "health_flags": ["Net debt position of $8.5B"],
    }
    dummy_return = {
        "ticker": "DEMO", "current_price_fmt": "$182.40", "market_cap": 2.8e12,
        "pe_ratio_fmt": "28.4x", "forward_pe_fmt": "24.1x", "peg_ratio_fmt": "1.8x",
        "ev_ebitda_fmt": "22.1x", "ev_revenue_fmt": "6.2x", "price_to_book_fmt": "8.4x",
        "dividend_yield_fmt": "0.6%", "beta_fmt": "1.24",
        "valuation": {
            "verdict": "Slightly Elevated", "signals": ["Trading at 14% premium to sector on P/E"],
            "benchmarks_used": {"pe": 28, "ev_ebitda": 20, "ev_rev": 6},
        },
        "positioning_52w": {
            "position_pct": 0.72, "position_pct_fmt": "72% of 52w range",
            "label": "Upper range", "low_fmt": "$142.00", "high_fmt": "$199.62",
            "from_high_pct_fmt": "-8.6%",
        },
    }
    dummy_risk = {
        "ticker": "DEMO", "overall_risk": "Moderate", "risk_score": 6.5,
        "beta_fmt": "1.24", "debt_ebitda_fmt": "1.8x", "net_cash_fmt": "-$8.5B",
        "top_risks": ["Elevated EV/EBITDA premium to sector"],
        "leverage": {"risk_level": "Low", "details": ["Debt/EBITDA of 1.8x is manageable"]},
        "volatility": {"risk_level": "Moderate", "details": ["Beta of 1.24 — moderately above market volatility"]},
        "profitability_risk": {"risk_level": "Low", "details": ["Operating margin of 24.3% provides reasonable buffer"]},
        "short_interest": {"risk_level": "Low", "details": ["Short ratio of 2.1 days — low short interest"]},
    }
    dummy_macro = {
        "ticker": "DEMO", "sector": "technology", "sector_label": "Technology",
        "rate_environment": "Higher-for-longer", "cycle_stage": "Late cycle",
        "tailwinds": ["AI infrastructure spending remains strong", "Enterprise software demand driven by digital transformation"],
        "headwinds": ["Elevated valuations leave limited margin of safety", "Rising interest rates increase discount rates"],
        "key_watch": "AI monetization timelines, enterprise IT budget cycles",
        "macro_posture": "Cautiously constructive",
    }
    build_pdf(dummy_financial, dummy_return, dummy_risk, dummy_macro,
              "/mnt/user-data/outputs/DEMO_research_brief.pdf")
    print("Done.")
