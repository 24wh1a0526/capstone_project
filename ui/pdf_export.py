"""
pdf_export.py
-------------
Converts a Markdown competitive intelligence report to a styled PDF.
Uses fpdf2 (pip install fpdf2).

Every string that reaches fpdf2 is passed through _sanitize() which:
  1. Maps common Unicode characters to ASCII equivalents
  2. Encodes to Latin-1 with errors="replace" as a final fallback

Every long token is passed through _breakable() which inserts real
spaces (NOT soft hyphens) so fpdf2 can wrap — fpdf2 2.7.x does NOT
treat \xad as a word-break opportunity, causing the error:
  "Not enough horizontal space to render a single character"
"""

from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO

from fpdf import FPDF, XPos, YPos


# ── Colour palette ─────────────────────────────────────────────────────
NAVY  = (26,  33,  64)
BLUE  = (25, 118, 210)
TEAL  = (0,  120, 130)
WHITE = (255, 255, 255)
LGRAY = (245, 246, 248)
DGRAY = (80,  80,  80)
BLACK = (30,  30,  30)

SECTION_ICONS = {
    "Executive Summary":         "EXECUTIVE SUMMARY",
    "Competitor Pricing":        "COMPETITOR PRICING",
    "Competitor Product":        "COMPETITOR PRODUCT UPDATES",
    "Market Signals":            "MARKET SIGNALS",
    "Strategic Recommendations": "STRATEGIC RECOMMENDATIONS",
    "Recommendations":           "STRATEGIC RECOMMENDATIONS",
    "References":                "REFERENCES",
    "Run Metadata":              "RUN METADATA",
}

# Plain ASCII used for the bullet glyph — no Unicode character
_BULLET = "-"


# ══════════════════════════════════════════════════════════════════════
# Text sanitization — MUST run on every string before it reaches fpdf2
# ══════════════════════════════════════════════════════════════════════

# Ordered list — no duplicate keys, all processed in sequence
_UNICODE_MAP = [
    # Dashes
    ("\u2014", "--"),   # em dash          —
    ("\u2013", "-"),    # en dash           –
    ("\u2012", "-"),    # figure dash
    ("\u2015", "--"),   # horizontal bar
    ("\u2011", "-"),    # non-breaking hyphen
    # Single quotes / apostrophes
    ("\u2018", "'"),    # left single quote  '
    ("\u2019", "'"),    # right single quote '
    ("\u201a", ","),    # single low-9 quote ‚
    ("\u201b", "'"),
    # Double quotes
    ("\u201c", '"'),    # left double quote  "
    ("\u201d", '"'),    # right double quote "
    ("\u201e", '"'),
    ("\u201f", '"'),
    # Ellipsis & special spaces
    ("\u2026", "..."),  # ellipsis  …
    ("\u00a0", " "),    # non-breaking space
    ("\u202f", " "),    # narrow no-break space
    ("\u2009", " "),    # thin space
    ("\u2003", " "),    # em space
    ("\u2002", " "),    # en space
    # Bullets / list markers
    ("\u2022", "-"),    # bullet            •
    ("\u2023", ">"),    # triangular bullet
    ("\u25cf", "-"),    # black circle
    ("\u25e6", "-"),    # white bullet
    ("\u2043", "-"),    # hyphen bullet
    # Check / ballot
    ("\u2610", "[ ]"),
    ("\u2611", "[x]"),
    ("\u2612", "[x]"),
    ("\u2713", "ok"),
    ("\u2714", "ok"),
    ("\u2717", "x"),
    ("\u2718", "x"),
    # Math
    ("\u00d7", "x"),
    ("\u00f7", "/"),
    ("\u2264", "<="),
    ("\u2265", ">="),
    ("\u2248", "~"),
    ("\u2260", "!="),
    ("\u221e", "inf"),
    ("\u00b1", "+/-"),
    ("\u00b2", "^2"),
    ("\u00b3", "^3"),
    # Currency
    ("\u20ac", "EUR"),
    ("\u00a3", "GBP"),
    ("\u00a5", "JPY"),
    ("\u20b9", "INR"),
    ("\u00a2", "c"),
    # Arrows
    ("\u2192", "->"),
    ("\u2190", "<-"),
    ("\u2194", "<->"),
    ("\u21d2", "=>"),
    ("\u21d0", "<="),
    ("\u2191", "^"),
    ("\u2193", "v"),
    # Misc typographic
    ("\u00ae", "(R)"),
    ("\u00a9", "(C)"),
    ("\u2122", "(TM)"),
    ("\u00b0", " deg"),
    ("\u00b7", "."),
    ("\u2027", "."),
    ("\u00ab", "<<"),
    ("\u00bb", ">>"),
    ("\u2039", "<"),
    ("\u203a", ">"),
    ("\u2020", "+"),
    ("\u2021", "++"),
    ("\u00a7", "S."),
    ("\u00b6", "P."),
]


def _sanitize(text: str) -> str:
    """
    Replace every Unicode character outside Latin-1 with a safe ASCII
    equivalent, then encode/decode through Latin-1 to catch anything
    the explicit map missed.  Must be called on ALL strings before they
    are passed to pdf.cell() or pdf.multi_cell().
    """
    for char, replacement in _UNICODE_MAP:
        text = text.replace(char, replacement)
    # Final safety net — replace anything still outside Latin-1 with '?'
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _clean(text: str) -> str:
    """Strip markdown syntax then sanitize for Latin-1."""
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # [label](url) -> label
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)           # **bold**
    text = re.sub(r'\*(.+?)\*',     r'\1', text)           # *italic*
    text = re.sub(r'`([^`]+)`',     r'\1', text)           # `code`
    text = re.sub(r'^#+\s*',        '',    text)            # headings
    return _sanitize(text.strip())


def _breakable(text: str, max_run: int = 35) -> str:
    """
    Split any token longer than max_run characters by inserting a REAL
    SPACE so fpdf2 can wrap at that point.

    IMPORTANT: Do NOT use soft hyphens (\xad) here.  fpdf2 2.7.x renders
    \xad as a visible character and does NOT treat it as a word-break
    opportunity, which causes the error:
        "Not enough horizontal space to render a single character"
    """
    words = text.split(" ")
    result = []
    for word in words:
        if len(word) > max_run:
            # Split into fixed-width chunks separated by spaces
            chunks = [word[i:i + max_run] for i in range(0, len(word), max_run)]
            result.append(" ".join(chunks))
        else:
            result.append(word)
    return " ".join(result)


# ══════════════════════════════════════════════════════════════════════
# PDF class
# ══════════════════════════════════════════════════════════════════════

class BriefingPDF(FPDF):
    """Custom FPDF subclass with header / footer."""

    def __init__(self, topic: str):
        super().__init__()
        # Pre-sanitize once — used in header, footer, and cover block
        self.safe_topic = _sanitize(topic)
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(18, 18, 18)

    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 12, "F")
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*WHITE)
        self.set_xy(0, 2)
        self.cell(0, 8, "  COMPETITIVE INTELLIGENCE BRIEFING CREW", align="L")
        self.set_xy(0, 2)
        self.cell(0, 8, f"{datetime.now().strftime('%d %b %Y')}  ", align="R")
        self.set_text_color(*BLACK)
        self.ln(6)

    def footer(self):
        self.set_y(-14)
        self.set_fill_color(*NAVY)
        self.rect(0, self.get_y(), 210, 14, "F")
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*WHITE)
        # Use pre-sanitized topic; hardcoded string uses '-' not em dash
        self.cell(
            0, 14,
            f"  Page {self.page_no()}  |  {self.safe_topic[:80]}  |  "
            "Confidential - AI-generated briefing",
            align="C",
        )
        self.set_text_color(*BLACK)


# ══════════════════════════════════════════════════════════════════════
# Section rendering helpers
# ══════════════════════════════════════════════════════════════════════

def _render_section_header(pdf: FPDF, label: str) -> None:
    """Draw a coloured section-header bar."""
    pdf.ln(4)
    pdf.set_fill_color(*BLUE)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 10)
    # Reset X to left margin before cell(0,...) to guarantee full width
    pdf.set_x(pdf.l_margin)
    pdf.cell(
        0, 8, f"  {_sanitize(label)}",
        fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.set_text_color(*BLACK)
    pdf.ln(2)


def _render_body(pdf: FPDF, text: str, section: str) -> None:
    """Render body text: bullets, numbered lists, metadata, paragraphs."""
    is_metadata = "metadata"   in section.lower()
    is_refs     = "reference"  in section.lower()

    for line in text.splitlines():
        raw   = line.strip()
        # _clean already calls _sanitize, so `clean` is always Latin-1 safe
        clean = _clean(raw)
        if not clean:
            pdf.ln(2)
            continue

        # ── Bullet points ──────────────────────────────────────────────
        if raw.startswith(("- ", "* ", "+ ")):
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*DGRAY)
            pdf.set_x(22)
            pdf.cell(4, 6, _BULLET, align="C")
            pdf.set_x(26)
            bullet_text = clean[2:] if clean[:2] in ("- ", "* ", "+ ") else clean
            pdf.multi_cell(162, 6, _breakable(bullet_text), fill=False)
            continue

        # ── Numbered list ──────────────────────────────────────────────
        if re.match(r'^\d+\.', raw):
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*DGRAY)
            pdf.set_x(22)
            pdf.multi_cell(162, 6, _breakable(clean))
            continue

        # ── Metadata / references (monospace) ─────────────────────────
        if is_metadata or is_refs:
            pdf.set_font("Courier", "", 8)
            pdf.set_text_color(*TEAL)
            pdf.set_x(pdf.l_margin)           # reset before multi_cell(0,...)
            pdf.multi_cell(0, 5, _breakable(clean, max_run=30))
            pdf.set_text_color(*BLACK)
            continue

        # ── Normal paragraph ──────────────────────────────────────────
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*DGRAY)
        pdf.set_x(pdf.l_margin)               # reset before multi_cell(0,...)
        pdf.multi_cell(0, 6, _breakable(clean))

    pdf.ln(2)


# ══════════════════════════════════════════════════════════════════════
# Public entry point
# ══════════════════════════════════════════════════════════════════════

def markdown_to_pdf(report: str, topic: str) -> bytes:
    """
    Convert a markdown briefing report to PDF bytes.

    Args:
        report: Full markdown report string
        topic:  Research topic (used in header / footer)

    Returns:
        Raw PDF bytes suitable for st.download_button
    """
    pdf = BriefingPDF(topic=topic)
    pdf.add_page()

    # ── Cover title block ──────────────────────────────────────────────
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 12, 210, 40, "F")

    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(18, 18)
    pdf.multi_cell(174, 10, "Competitive Intelligence\nBriefing Report", align="L")

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(180, 210, 255)
    pdf.set_xy(18, 42)
    # Use pre-sanitized topic; _breakable guards against long topic strings
    pdf.cell(0, 8, f"Topic: {_breakable(pdf.safe_topic, max_run=50)}", align="L")

    pdf.set_text_color(*BLACK)
    pdf.set_xy(18, 54)

    # ── Parse and render sections ──────────────────────────────────────
    parts = re.split(r'^(##\s+.+)$', report, flags=re.MULTILINE)
    current_heading = ""

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part.startswith("## "):
            heading_text   = part.lstrip("# ").strip()
            current_heading = heading_text
            label = heading_text.upper()
            for k, v in SECTION_ICONS.items():
                if k.lower() in heading_text.lower():
                    label = v
                    break
            _render_section_header(pdf, label)
        else:
            _render_body(pdf, part, current_heading)

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
