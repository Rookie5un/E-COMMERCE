#!/usr/bin/env python3
"""Remove italic formatting from the DOCX table of contents styles and entries."""

from __future__ import annotations

import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DOCX_PATH = ROOT / "docs/基于NLP技术的电商评论多维可视化分析平台_毕业论文_初稿.docx"

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
ET.register_namespace("w", NS["w"])


def qn(tag: str) -> str:
    prefix, name = tag.split(":", 1)
    return f"{{{NS[prefix]}}}{name}"


def is_toc_style_id(style_id: str | None) -> bool:
    return bool(style_id) and style_id.startswith("TOC") and style_id[3:].isdigit()


def remove_italic_from_run_properties(r_pr: ET.Element | None) -> int:
    if r_pr is None:
        return 0
    removed = 0
    for tag in ("w:i", "w:iCs"):
        for child in list(r_pr.findall(qn(tag))):
            r_pr.remove(child)
            removed += 1
    return removed


def patch_styles(xml_bytes: bytes) -> tuple[bytes, int]:
    root = ET.fromstring(xml_bytes)
    removed = 0
    for style in root.findall("w:style", NS):
        style_id = style.get(qn("w:styleId"))
        style_name = style.find("w:name", NS)
        name = style_name.get(qn("w:val")) if style_name is not None else ""
        if is_toc_style_id(style_id) or (name or "").lower().startswith("toc "):
            removed += remove_italic_from_run_properties(style.find("w:rPr", NS))
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), removed


def patch_document(xml_bytes: bytes) -> tuple[bytes, int]:
    root = ET.fromstring(xml_bytes)
    removed = 0
    for paragraph in root.iter(qn("w:p")):
        p_style = paragraph.find("w:pPr/w:pStyle", NS)
        if p_style is None or not is_toc_style_id(p_style.get(qn("w:val"))):
            continue
        for run_properties in paragraph.findall(".//w:rPr", NS):
            removed += remove_italic_from_run_properties(run_properties)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), removed


def patch_docx(docx_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = docx_path.with_name(f"{docx_path.stem}_backup_toc_no_italic_{timestamp}.docx")
    shutil.copy2(docx_path, backup_path)

    temp_path = docx_path.with_suffix(".tocfix.tmp.docx")
    total_removed = 0

    with zipfile.ZipFile(docx_path, "r") as src, zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "word/styles.xml":
                data, removed = patch_styles(data)
                total_removed += removed
            elif item.filename == "word/document.xml":
                data, removed = patch_document(data)
                total_removed += removed
            dst.writestr(item, data)

    temp_path.replace(docx_path)
    print(f"[OK] backup: {backup_path}")
    print(f"[OK] docx: {docx_path}")
    print(f"[OK] removed italic tags: {total_removed}")
    return backup_path


def main() -> int:
    patch_docx(DOCX_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
