#!/usr/bin/env python3
"""
Build thesis docx from markdown and post-process table borders.

Usage:
python3 scripts/build_thesis_docx.py \
  --input docs/基于NLP技术的电商评论多维可视化分析平台_毕业论文_重写稿.md \
  --reference docs/基于NLP技术的电商评论多维可视化分析平台_毕业论文_初稿.docx \
  --output docs/基于NLP技术的电商评论多维可视化分析平台_毕业论文_重写稿.docx
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


DB_CAPTION_KEYWORDS = ("数据库", "数据表", "字段设计", "ER图")


def _border_element(tag: str, val: str, sz: str = "8", color: str = "000000") -> OxmlElement:
    element = OxmlElement(tag)
    element.set(qn("w:val"), val)
    if val != "nil":
        element.set(qn("w:sz"), sz)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)
    return element


def set_table_borders(table: Table, *, full: bool) -> None:
    tbl_pr = table._tbl.tblPr
    tbl_borders = tbl_pr.first_child_found_in("w:tblBorders")
    if tbl_borders is None:
        tbl_borders = OxmlElement("w:tblBorders")
        tbl_pr.append(tbl_borders)

    for child in list(tbl_borders):
        tbl_borders.remove(child)

    if full:
        border_map = {
            "w:top": "single",
            "w:left": "single",
            "w:bottom": "single",
            "w:right": "single",
            "w:insideH": "single",
            "w:insideV": "single",
        }
    else:
        border_map = {
            "w:top": "single",
            "w:left": "nil",
            "w:bottom": "single",
            "w:right": "nil",
            "w:insideH": "nil",
            "w:insideV": "nil",
        }

    for tag, val in border_map.items():
        tbl_borders.append(_border_element(tag, val))


def set_cell_border(cell, **borders: str) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_borders = tc_pr.first_child_found_in("w:tcBorders")
    if tc_borders is None:
        tc_borders = OxmlElement("w:tcBorders")
        tc_pr.append(tc_borders)

    for edge in ("top", "left", "bottom", "right"):
        value = borders.get(edge)
        if value is None:
            continue
        tag = f"w:{edge}"
        existing = tc_borders.find(qn(tag))
        if existing is not None:
            tc_borders.remove(existing)
        tc_borders.append(_border_element(tag, value))


def apply_three_line_table(table: Table) -> None:
    set_table_borders(table, full=False)

    for row in table.rows:
        for cell in row.cells:
            set_cell_border(cell, top="nil", left="nil", bottom="nil", right="nil")

    if table.rows:
        for cell in table.rows[0].cells:
            set_cell_border(cell, bottom="single")


def apply_full_grid_table(table: Table) -> None:
    set_table_borders(table, full=True)


def iter_block_items(document: Document):
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def is_db_caption(text: str) -> bool:
    normalized = (text or "").strip()
    return any(keyword in normalized for keyword in DB_CAPTION_KEYWORDS)


def postprocess_docx(docx_path: Path) -> None:
    document = Document(str(docx_path))
    last_nonempty_paragraph = ""

    for block in iter_block_items(document):
        if isinstance(block, Paragraph):
            if block.text.strip():
                last_nonempty_paragraph = block.text.strip()
            continue

        if isinstance(block, Table):
            if is_db_caption(last_nonempty_paragraph):
                apply_three_line_table(block)
            else:
                apply_full_grid_table(block)

    document.save(str(docx_path))


def build_docx(input_path: Path, reference_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "pandoc",
        str(input_path),
        "--reference-doc",
        str(reference_path),
        "--wrap=none",
        "--from",
        "gfm+hard_line_breaks",
        "--to",
        "docx",
        "--output",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)
    postprocess_docx(output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build thesis docx and post-process table styles")
    parser.add_argument("--input", required=True, help="Markdown source")
    parser.add_argument("--reference", required=True, help="Reference docx")
    parser.add_argument("--output", required=True, help="Output docx")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    reference_path = Path(args.reference).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Markdown source not found: {input_path}")
    if not reference_path.exists():
        raise FileNotFoundError(f"Reference docx not found: {reference_path}")

    build_docx(input_path, reference_path, output_path)
    print(f"[OK] docx generated: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
