"""Renders the case-intelligence payload into a downloadable, branded PDF.

Reuses the header/footer/section styling pattern from the repo-root
``gen_pdf.py`` sample-document generator, as a reusable "consultation
packet" export for a real case (see issue #23).
"""
from __future__ import annotations

from typing import Any

from fpdf import FPDF


class _ConsultationPacketPDF(FPDF):
    def header(self) -> None:
        self.set_fill_color(11, 31, 58)
        self.rect(0, 0, 210, 18, "F")
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(255, 255, 255)
        self.set_y(5)
        self.cell(0, 8, "ADVOCATEAI  |  Consultation Packet", align="C")
        self.set_text_color(0, 0, 0)
        self.ln(14)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, f"Page {self.page_no()} | AdvocateAI | Informational, not legal advice", align="C")


def _divider(pdf: FPDF) -> None:
    pdf.set_draw_color(200, 210, 225)
    pdf.set_line_width(0.4)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(4)


def _section_header(pdf: FPDF, text: str) -> None:
    pdf.set_fill_color(240, 244, 251)
    pdf.set_draw_color(30, 99, 233)
    pdf.set_line_width(0.8)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(11, 31, 58)
    pdf.cell(0, 8, text, border="L", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_line_width(0.2)
    pdf.ln(2)


def _body(pdf: FPDF, text: str, size: int = 10) -> None:
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(50, 60, 75)
    pdf.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _bullet_list(pdf: FPDF, items: list[str]) -> None:
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 60, 75)
    for item in items:
        # Reset to the left margin before each bullet -- multi_cell's default
        # new_x leaves the cursor at the right edge, which starves the next
        # bullet's "-" + multi_cell of horizontal space.
        pdf.set_x(pdf.l_margin)
        pdf.cell(6, 6, "-")
        pdf.multi_cell(0, 6, str(item), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def render_consultation_packet(case: dict[str, Any], case_intelligence: dict[str, Any]) -> bytes:
    """Render a case + its case-intelligence payload to PDF bytes.

    ``case`` is the case row dict (case_id, title, description, legal_area,
    issue_type, urgency, city, status, ...). ``case_intelligence`` is the
    structured object produced by ``case_intelligence_service.build_case_intelligence``
    (readiness_score, missing_information, follow_up_questions, risk_flags,
    deadlines, consultation_prep, recommended_next_steps).
    """
    pdf = _ConsultationPacketPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(20, 22, 20)

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(11, 31, 58)
    pdf.cell(0, 10, f"Case #{case.get('case_id')}: {case.get('title', '')}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(100, 120, 150)
    pdf.cell(
        0,
        6,
        f"Legal area: {case.get('legal_area', 'N/A')}  |  Urgency: {case.get('urgency', 'N/A')}  |  "
        f"Location: {case.get('city') or 'Unknown'}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(2)
    _divider(pdf)

    _section_header(pdf, "  CASE SUMMARY")
    _body(pdf, case.get("ai_summary") or case.get("description") or "No summary available.")

    readiness_score = case_intelligence.get("readiness_score", 0)
    readiness_band = case_intelligence.get("readiness_band", "")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(255, 243, 225)
    pdf.set_draw_color(200, 150, 0)
    pdf.set_text_color(100, 60, 0)
    pdf.cell(60, 8, "  Readiness score:", border=1, fill=True)
    pdf.set_text_color(180, 30, 30)
    pdf.cell(0, 8, f"  {readiness_score}/100 ({readiness_band})", border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    deadlines = case_intelligence.get("deadlines") or []
    _section_header(pdf, "  KEY DEADLINES")
    if deadlines:
        for item in deadlines:
            status = str(item.get("status", "")).upper()
            _body(pdf, f"{item.get('date', '')}  [{status}]  {item.get('title', '')}")
    else:
        _body(pdf, "No deadlines captured yet.")

    _section_header(pdf, "  MISSING INFORMATION")
    _bullet_list(pdf, case_intelligence.get("missing_information") or ["None noted."])

    _section_header(pdf, "  RISK FLAGS")
    _bullet_list(pdf, case_intelligence.get("risk_flags") or ["None noted."])

    consultation_prep = case_intelligence.get("consultation_prep") or {}
    _section_header(pdf, "  CONSULTATION PREP")
    _body(pdf, f"Goal: {consultation_prep.get('one_line_goal', '')}")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(11, 31, 58)
    pdf.cell(0, 6, "Documents to bring:", new_x="LMARGIN", new_y="NEXT")
    _bullet_list(pdf, consultation_prep.get("documents_to_bring") or [])
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(11, 31, 58)
    pdf.cell(0, 6, "Questions to ask:", new_x="LMARGIN", new_y="NEXT")
    _bullet_list(pdf, consultation_prep.get("questions_to_ask") or [])

    _section_header(pdf, "  RECOMMENDED NEXT STEPS")
    _bullet_list(pdf, case_intelligence.get("recommended_next_steps") or ["None noted."])

    _divider(pdf)
    pdf.set_fill_color(254, 242, 242)
    pdf.set_draw_color(239, 68, 68)
    pdf.set_line_width(0.5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(185, 28, 28)
    pdf.multi_cell(
        0,
        7,
        "  This packet is AI-generated informational support, not legal advice. "
        "Verify facts, deadlines, and jurisdiction with a qualified lawyer.",
        border=1,
        fill=True,
    )

    output = pdf.output()
    return bytes(output)
