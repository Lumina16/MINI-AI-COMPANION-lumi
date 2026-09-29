#!/usr/bin/env python3
"""Generate a PDF for the LUMI project from a text or Markdown-lite source file.

This is the build path for the LUMI deliverable PDF. It is deliberately
dependency-light (reportlab only) so it runs anywhere a venv can be created.

Usage:
    python tools/build_pdf.py <source.txt> <output.pdf> [--title "Title"]

Recognised lightweight markup (line-oriented, no parser surprises):
    # Heading        -> H1, starts a new page after the first
    ## Heading       -> H2
    ### Heading      -> H3
    - item           -> bullet
    > quote          -> indented block, italic
    ---              -> horizontal rule
    (blank line)     -> paragraph break
    anything else    -> paragraph body

Long lines and long paragraphs are wrapped to the page. Everything that does not
match a rule above is rendered verbatim, so a plain prompt dump still looks right.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm

# Asia/Kuching is UTC+8 year-round (no DST in Malaysia).
MYT = timezone(timedelta(hours=8))


def build_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "LumiTitle", parent=base["Title"], fontSize=22, leading=27,
            spaceAfter=4, textColor=colors.HexColor("#1b2a4a"),
        ),
        "stamp": ParagraphStyle(
            "LumiStamp", parent=base["Normal"], fontSize=8.5, leading=12,
            textColor=colors.HexColor("#5a6478"), spaceAfter=10,
        ),
        "h1": ParagraphStyle(
            "LumiH1", parent=base["Heading1"], fontSize=15, leading=19,
            spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#1b2a4a"),
        ),
        "h2": ParagraphStyle(
            "LumiH2", parent=base["Heading2"], fontSize=12.5, leading=16,
            spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#2f4a7a"),
        ),
        "h3": ParagraphStyle(
            "LumiH3", parent=base["Heading3"], fontSize=11, leading=14,
            spaceBefore=8, spaceAfter=3, textColor=colors.HexColor("#3c4c68"),
        ),
        "body": ParagraphStyle(
            "LumiBody", parent=base["BodyText"], fontSize=10, leading=14.5,
            alignment=TA_JUSTIFY, spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "LumiBullet", parent=base["BodyText"], fontSize=10, leading=14.5,
            leftIndent=14, bulletIndent=4, spaceAfter=3,
        ),
        "quote": ParagraphStyle(
            "LumiQuote", parent=base["BodyText"], fontSize=9.5, leading=14,
            leftIndent=14, rightIndent=10, textColor=colors.HexColor("#404a5e"),
            fontName="Helvetica-Oblique", spaceBefore=3, spaceAfter=6,
        ),
        "code": ParagraphStyle(
            "LumiCode", parent=base["Code"], fontName="Courier", fontSize=8,
            leading=11, leftIndent=10, rightIndent=6, spaceBefore=4, spaceAfter=6,
            backColor=colors.HexColor("#f2f4f8"),
            borderColor=colors.HexColor("#dfe4ee"), borderWidth=0.5,
            borderPadding=5,
        ),
    }
    return styles


def esc(text: str) -> str:
    """Escape XML-significant characters for reportlab Paragraph markup.

    ``amp`` is escaped first so later entities survive untouched.
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def inline_md(text: str) -> str:
    """Convert a narrow set of Markdown inline markup to reportlab tags.

    Input is escaped first, so ``**``/``*``/backtick are the only markup that can
    survive. Handles ``**bold**``, ``*italic*`` and `` `code` ``; anything else is
    left as literal text rather than being guessed at.
    """
    out = esc(text)

    # `code` -> monospace, boxed
    out = re.sub(
        r"`([^`]+)`",
        r'<font face="Courier" backColor="#f2f4f8">\1</font>',
        out,
    )
    # **bold**
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)
    # *italic* — only single stars not already consumed by the bold rule
    out = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", out)
    # _italic_
    out = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"<i>\1</i>", out)

    return out


def lines_to_flowables(lines, styles):
    """Turn lightweight-markup lines into reportlab flowables."""
    flow = []
    para_buf: list[str] = []
    code_buf: list[str] = []
    in_code = False
    table_rows: list[list[str]] = []
    first_h1_seen = False

    def flush_para():
        if para_buf:
            flow.append(Paragraph(inline_md(" ".join(para_buf).strip()),
                                  styles["body"]))
            para_buf.clear()

    def flush_code():
        nonlocal in_code
        if code_buf:
            # One Paragraph per line keeps long commands readable and wrapped.
            for ln in code_buf:
                flow.append(Paragraph(esc(ln) or "&nbsp;", styles["code"]))
            code_buf.clear()
        in_code = False

    def flush_table():
        if not table_rows:
            return
        ncol = max(len(r) for r in table_rows)
        rows = [r + [""] * (ncol - len(r)) for r in table_rows]
        data = [[Paragraph(inline_md(c), styles["body"]) for c in r] for r in rows]
        avail = PAGE_W - 2 * MARGIN
        t = Table(data, colWidths=[avail / ncol] * ncol, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef1f7")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c8cfdd")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        flow.append(Spacer(1, 4))
        flow.append(t)
        flow.append(Spacer(1, 6))
        table_rows.clear()

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()

        # Fenced code block toggle takes precedence over everything else.
        if stripped.startswith("```"):
            if in_code:
                flush_code()
            else:
                flush_para()
                flush_table()
                in_code = True
            continue

        if in_code:
            code_buf.append(line)
            continue

        # Markdown table row (skip |---|---| separators).
        if stripped.startswith("|") and stripped.endswith("|"):
            flush_para()
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(set(c) <= set("-: ") and c for c in cells):
                continue  # separator row
            table_rows.append(cells)
            continue

        flush_table()

        if not stripped:
            flush_para()
            continue

        if stripped.startswith("### "):
            flush_para()
            flow.append(Paragraph(esc(stripped[4:]), styles["h3"]))
        elif stripped.startswith("## "):
            flush_para()
            flow.append(Paragraph(esc(stripped[3:]), styles["h2"]))
        elif stripped.startswith("# "):
            flush_para()
            if first_h1_seen:
                flow.append(PageBreak())
            first_h1_seen = True
            flow.append(Paragraph(esc(stripped[2:]), styles["h1"]))
        elif stripped in ("---", "***", "___"):
            flush_para()
            flow.append(Spacer(1, 4))
            flow.append(HRFlowable(width="100%", thickness=0.6,
                                   color=colors.HexColor("#c8cfdd")))
            flow.append(Spacer(1, 4))
        elif stripped.startswith(("- ", "* ")):
            flush_para()
            flow.append(Paragraph(inline_md(stripped[2:]), styles["bullet"],
                                  bulletText="\u2022"))
        elif re.match(r"^\d+\.\s", stripped):
            flush_para()
            num, _, rest = stripped.partition(" ")
            flow.append(Paragraph(inline_md(rest), styles["bullet"],
                                  bulletText=num.rstrip(".")))
        elif stripped.startswith("> "):
            flush_para()
            flow.append(Paragraph(esc(stripped[2:]), styles["quote"]))
        else:
            para_buf.append(stripped)

    flush_para()
    flush_code()
    flush_table()
    return flow


def make_footer(title: str):
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#8a93a6"))
        canvas.drawString(MARGIN, 12 * mm, title)
        canvas.drawRightString(PAGE_W - MARGIN, 12 * mm, f"Page {doc.page}")
        canvas.setStrokeColor(colors.HexColor("#dfe4ee"))
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 15 * mm, PAGE_W - MARGIN, 15 * mm)
        canvas.restoreState()
    return footer


def build_pdf(source: Path, output: Path, title: str | None = None) -> Path:
    styles = build_styles()
    lines = source.read_text(encoding="utf-8").splitlines()

    # Default the title to the first H1, else the filename.
    derived = title
    if derived is None:
        for line in lines:
            if line.strip().startswith("# "):
                derived = line.strip()[2:]
                break
        derived = derived or source.stem.replace("_", " ").replace("-", " ").title()

    doc = SimpleDocTemplate(
        str(output), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=20 * mm,
        title=derived, author="LUMI / MINI-AI-COMPANION",
    )

    now_myt = datetime.now(MYT)
    now_utc = now_myt.astimezone(timezone.utc)
    stamp = (
        f"Generated {now_myt:%Y-%m-%d %H:%M:%S} MYT (UTC+8) "
        f"/ {now_utc:%Y-%m-%d %H:%M:%S} UTC "
        f"&nbsp;&nbsp;|&nbsp;&nbsp; source: {esc(source.name)}"
    )

    flow = [
        Paragraph(esc(derived), styles["title"]),
        HRFlowable(width="100%", thickness=1.1, color=colors.HexColor("#1b2a4a")),
        Spacer(1, 4),
        Paragraph(stamp, styles["stamp"]),
    ]
    flow += lines_to_flowables(lines, styles)

    doc.build(flow, onFirstPage=make_footer(derived), onLaterPages=make_footer(derived))
    return output


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Build the LUMI PDF from a text source.")
    p.add_argument("source", type=Path, help="input .txt / .md source")
    p.add_argument("output", type=Path, help="output .pdf path")
    p.add_argument("--title", default=None, help="override document title")
    args = p.parse_args(argv)

    if not args.source.exists():
        print(f"error: source not found: {args.source}", file=sys.stderr)
        return 2
    if args.output.suffix.lower() != ".pdf":
        print("error: output path must end in .pdf", file=sys.stderr)
        return 2

    # reportlab opens the file directly; make sure the directory exists first.
    if args.output.parent and str(args.output.parent) not in ("", "."):
        args.output.parent.mkdir(parents=True, exist_ok=True)

    out = build_pdf(args.source, args.output, args.title)
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
