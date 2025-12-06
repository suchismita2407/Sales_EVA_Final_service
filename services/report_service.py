import os
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from db import query_one
from services.rag_service import analyze_gaps
from services.llm_service import get_llm


def generate_gap_pdf(opp_id: int, offering_id: int):
    opp = query_one("SELECT * FROM opportunities WHERE id=?", (opp_id,))
    off = query_one("SELECT * FROM offerings WHERE id=?", (offering_id,))

    gaps = analyze_gaps(opp_id, offering_id)

    # Ask LLM for narrative explanation
    llm = get_llm()
    prompt = f"""
    Write a professional consulting style gap assessment narrative 
    covering:

    Opportunity:
    {opp['description']}

    Offering:
    {off['description']}

    Covered points: {json.dumps(gaps['covered'])}
    Partial coverage: {json.dumps(gaps['partial'])}
    Missing areas: {json.dumps(gaps['missing'])}

    Focus on:
    - Scope alignment
    - Risks
    - Recommendations
    - Client Impact

    Write in 4-7 bullet points.
    """

    llm_resp = llm.invoke(prompt)
    narrative = llm_resp.content.strip()

    output_dir = "reports"
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"GAP_REPORT_O{opp_id}_F{offering_id}.pdf")


    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("<b>GAP ANALYSIS REPORT</b>", styles['Title']))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"<b>Opportunity:</b> {opp['name']}", styles['Normal']))
    elements.append(Paragraph(f"<b>Offering:</b> {off['name']}", styles['Normal']))
    elements.append(Spacer(1, 12))


    table_data = [
        ['Category', 'Details'],
        ['Covered', "\n".join(gaps['covered']) or "None"],
        ['Partial Coverage', "\n".join(gaps['partial']) or "None"],
        ['Missing', "\n".join(gaps['missing']) or "None"],
    ]

    table = Table(table_data, colWidths=[100, 360])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("<b>Consultant Narrative</b>", styles['Heading2']))
    elements.append(Paragraph(narrative.replace('\n', '<br/>'), styles['Normal']))

    doc.build(elements)

    return output_path
