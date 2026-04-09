"""Gera PDF a partir do manual do usuário (Markdown simplificado)."""
import os, re
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "09-manual-do-usuario.md")
OUT = os.path.join(BASE, "Manual-do-Usuario.pdf")

styles = getSampleStyleSheet()
PRIMARY = colors.HexColor("#2563EB")
DARK = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#64748B")
BG = colors.HexColor("#F1F5F9")

styles.add(ParagraphStyle(name="Titulo1", fontName="Helvetica-Bold",
    fontSize=22, textColor=PRIMARY, spaceBefore=18, spaceAfter=10, leading=26))
styles.add(ParagraphStyle(name="Titulo2", fontName="Helvetica-Bold",
    fontSize=16, textColor=DARK, spaceBefore=14, spaceAfter=8, leading=20))
styles.add(ParagraphStyle(name="Titulo3", fontName="Helvetica-Bold",
    fontSize=13, textColor=PRIMARY, spaceBefore=10, spaceAfter=6, leading=16))
styles.add(ParagraphStyle(name="Corpo", fontName="Helvetica",
    fontSize=10.5, textColor=DARK, leading=15, spaceAfter=6, alignment=TA_JUSTIFY))
styles.add(ParagraphStyle(name="Quote", fontName="Helvetica-Oblique",
    fontSize=10, textColor=MUTED, leftIndent=12, leading=14, spaceAfter=6))
styles.add(ParagraphStyle(name="CodeBox", fontName="Courier",
    fontSize=9.5, textColor=DARK, backColor=BG, leftIndent=8,
    rightIndent=8, borderPadding=6, leading=12, spaceAfter=6))

def inline(text):
    """Converte marcação inline markdown para tags ReportLab."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`", r'<font name="Courier" backColor="#F1F5F9">&nbsp;\1&nbsp;</font>', text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<link href="\2" color="#2563EB"><u>\1</u></link>', text)
    return text

def parse_md(md):
    lines = md.split("\n")
    flows = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Code fence
        if stripped.startswith("```"):
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            code_text = "<br/>".join(
                l.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;")
                for l in code
            )
            flows.append(Paragraph(code_text, styles["CodeBox"]))
            flows.append(Spacer(1, 4))
            continue

        # Horizontal rule
        if stripped in ("---", "***"):
            flows.append(Spacer(1, 6))
            t = Table([[""]], colWidths=[16 * cm], rowHeights=[0.5])
            t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 0.5, MUTED)]))
            flows.append(t)
            flows.append(Spacer(1, 6))
            i += 1
            continue

        # Headings
        if stripped.startswith("# "):
            flows.append(Paragraph(inline(stripped[2:]), styles["Titulo1"]))
            i += 1
            continue
        if stripped.startswith("## "):
            flows.append(Paragraph(inline(stripped[3:]), styles["Titulo2"]))
            i += 1
            continue
        if stripped.startswith("### "):
            flows.append(Paragraph(inline(stripped[4:]), styles["Titulo3"]))
            i += 1
            continue

        # Tables
        if stripped.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].strip().replace("|", "").replace(":", "").replace("-", "").strip()) == set():
            headers = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            data = [[Paragraph(inline(h), ParagraphStyle("th", parent=styles["Corpo"], fontName="Helvetica-Bold", textColor=colors.white, fontSize=10)) for h in headers]]
            for r in rows:
                data.append([Paragraph(inline(c), styles["Corpo"]) for c in r])
            col_count = len(headers)
            col_widths = [16 * cm / col_count] * col_count
            t = Table(data, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            flows.append(t)
            flows.append(Spacer(1, 8))
            continue

        # Blockquote
        if stripped.startswith("> "):
            flows.append(Paragraph(inline(stripped[2:]), styles["Quote"]))
            i += 1
            continue

        # Lists (numeric or bullet)
        if re.match(r"^(\d+\.|\-|\*)\s", stripped):
            items = []
            ordered = bool(re.match(r"^\d+\.\s", stripped))
            while i < len(lines):
                ls = lines[i].strip()
                if re.match(r"^(\d+\.|\-|\*)\s", ls):
                    content = re.sub(r"^(\d+\.|\-|\*)\s", "", ls)
                    items.append(ListItem(Paragraph(inline(content), styles["Corpo"]), leftIndent=12))
                    i += 1
                elif ls == "":
                    # Could be end or continuation; peek next
                    if i + 1 < len(lines) and re.match(r"^(\d+\.|\-|\*)\s", lines[i + 1].strip()):
                        i += 1
                        continue
                    break
                else:
                    break
            flows.append(ListFlowable(items, bulletType="1" if ordered else "bullet",
                                       leftIndent=18, bulletFontSize=10))
            flows.append(Spacer(1, 4))
            continue

        # Normal paragraph (accumulate until blank line)
        para = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||>|```|\d+\.|\-|\*)\s?", lines[i].strip()) and lines[i].strip() not in ("---", "***"):
            para.append(lines[i].strip())
            i += 1
        flows.append(Paragraph(inline(" ".join(para)), styles["Corpo"]))

    return flows

def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(2 * cm, 1.2 * cm, "Organizador de Tarefas — Manual do Usuário")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
    canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canvas.restoreState()

def main():
    with open(SRC, "r", encoding="utf-8") as f:
        md = f.read()
    flows = parse_md(md)
    doc = SimpleDocTemplate(OUT, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="Manual do Usuário — Organizador de Tarefas",
        author="Wendel Castro")
    doc.build(flows, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"OK: {OUT}")

if __name__ == "__main__":
    main()
