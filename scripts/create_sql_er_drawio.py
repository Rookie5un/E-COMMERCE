from __future__ import annotations

import html
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = Path("/Users/rookie/Desktop/script.sql")
DIAGRAM_DIR = ROOT / "docs" / "diagrams"
FIGURE_DIR = ROOT / "docs" / "figures"
DRAWIO_PATH = DIAGRAM_DIR / "11_基于SQL数据库E-R图.drawio"
PNG_PATH = FIGURE_DIR / "figure_4_11_sql_database_er.png"


ENTITY_STYLE = (
    "rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#111111;"
    "strokeWidth=1.2;fontSize=14;fontStyle=1;fontColor=#111111;"
)
ATTR_STYLE = (
    "ellipse;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#111111;"
    "strokeWidth=1;fontSize=10;fontColor=#111111;"
)
REL_STYLE = (
    "rhombus;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#111111;"
    "strokeWidth=1;fontSize=12;fontColor=#111111;"
)
EDGE_STYLE = "edgeStyle=none;rounded=0;html=1;endArrow=none;strokeColor=#111111;strokeWidth=1;"
TITLE_STYLE = (
    "text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;"
    "whiteSpace=wrap;fontSize=20;fontStyle=1;fontColor=#111111;"
)


@dataclass(frozen=True)
class Column:
    name: str
    comment: str
    is_pk: bool
    is_fk: bool


@dataclass(frozen=True)
class ForeignKey:
    table: str
    column: str
    ref_table: str
    ref_column: str


@dataclass
class Table:
    name: str
    comment: str
    columns: list[Column]


TABLE_POSITIONS: dict[str, tuple[int, int]] = {
    "users": (170, 210),
    "products": (740, 210),
    "review_batches": (1310, 210),
    "reviews": (740, 760),
    "analysis_runs": (1310, 760),
    "reports": (1880, 760),
    "review_sentiments": (170, 1320),
    "aspect_mentions": (740, 1320),
    "issue_topics": (1310, 1320),
    "issue_topic_reviews": (1880, 1320),
}

RELATION_LABELS: dict[tuple[str, str], str] = {
    ("products", "created_by"): "创建",
    ("review_batches", "product_id"): "包含",
    ("review_batches", "created_by"): "导入",
    ("analysis_runs", "product_id"): "关联分析",
    ("analysis_runs", "batch_id"): "关联批次",
    ("analysis_runs", "started_by"): "启动",
    ("reports", "run_id"): "生成报告",
    ("reports", "created_by"): "创建报告",
    ("reviews", "product_id"): "拥有评论",
    ("reviews", "batch_id"): "包含评论",
    ("aspect_mentions", "run_id"): "识别功能点",
    ("aspect_mentions", "review_id"): "包含功能点",
    ("issue_topics", "run_id"): "提取问题",
    ("issue_topics", "representative_review_id"): "代表",
    ("issue_topic_reviews", "issue_topic_id"): "关联评论",
    ("issue_topic_reviews", "review_id"): "关联主题",
    ("review_sentiments", "run_id"): "生成情感",
    ("review_sentiments", "review_id"): "产生情感",
}

RELATION_POSITIONS: dict[tuple[str, str], tuple[int, int]] = {
    ("products", "created_by"): (545, 235),
    ("review_batches", "product_id"): (1115, 235),
    ("review_batches", "created_by"): (815, 500),
    ("reviews", "product_id"): (765, 550),
    ("reviews", "batch_id"): (1085, 585),
    ("analysis_runs", "product_id"): (1110, 690),
    ("analysis_runs", "batch_id"): (1365, 530),
    ("analysis_runs", "started_by"): (1010, 720),
    ("reports", "run_id"): (1670, 790),
    ("reports", "created_by"): (1450, 565),
    ("review_sentiments", "run_id"): (960, 1110),
    ("review_sentiments", "review_id"): (570, 1060),
    ("aspect_mentions", "run_id"): (1165, 1110),
    ("aspect_mentions", "review_id"): (765, 1060),
    ("issue_topics", "run_id"): (1365, 1110),
    ("issue_topics", "representative_review_id"): (1085, 1045),
    ("issue_topic_reviews", "issue_topic_id"): (1655, 1355),
    ("issue_topic_reviews", "review_id"): (1585, 1060),
}

CORE_COLUMNS: dict[str, set[str]] = {
    "users": {"id", "username", "password", "email", "real_name", "role", "status"},
    "products": {"id", "name", "category", "platform", "url", "description"},
    "review_batches": {"id", "source_type", "file_name", "row_count", "imported_count", "status"},
    "reviews": {"id", "external_id", "raw_content", "cleaned_content", "content_hash", "rating", "review_time", "is_valid"},
    "analysis_runs": {"id", "status", "progress_stage", "progress_message", "model_name", "model_version", "config_json"},
    "reports": {"id", "title", "summary_json", "pdf_path"},
    "review_sentiments": {"id", "label", "confidence", "positive_prob", "neutral_prob", "negative_prob"},
    "aspect_mentions": {"id", "aspect_name", "normalized_aspect", "start_offset", "end_offset", "confidence", "linked_sentiment"},
    "issue_topics": {"id", "keyword", "normalized_keyword", "score", "frequency"},
    "issue_topic_reviews": {"id", "evidence_text"},
}


def esc(value: str) -> str:
    return html.escape(value, quote=True).replace("\n", "&#xa;")


def cell(cell_id: str, value: str, style: str, x: int, y: int, w: int, h: int) -> str:
    return f'''        <mxCell id="{cell_id}" value="{esc(value)}" style="{style}" vertex="1" parent="1">
          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>
        </mxCell>'''


def edge(edge_id: str, source: str, target: str, label: str = "") -> str:
    label_cell = ""
    if label:
        label_cell = f'''
        <mxCell id="{edge_id}-label" value="{esc(label)}" style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];fontSize=10;fontColor=#111111;" vertex="1" connectable="0" parent="{edge_id}">
          <mxGeometry x="0" y="-8" relative="1" as="geometry">
            <mxPoint as="offset"/>
          </mxGeometry>
        </mxCell>'''
    return f'''        <mxCell id="{edge_id}" value="" style="{EDGE_STYLE}" edge="1" parent="1" source="{source}" target="{target}">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>{label_cell}'''


def table_blocks(sql: str) -> list[tuple[str, str, str]]:
    pattern = re.compile(r"create table (\w+)\s*\((.*?)\)\s*comment '([^']+)'", re.S | re.I)
    return pattern.findall(sql)


def parse_sql(sql: str) -> tuple[dict[str, Table], list[ForeignKey]]:
    tables: dict[str, Table] = {}
    fks: list[ForeignKey] = []

    for table_name, body, table_comment in table_blocks(sql):
        pk_columns: set[str] = set()
        fk_columns: set[str] = set()

        inline_pk_match = re.search(r"^\s*(\w+)\s+.+?\n\s*primary key", body, re.M | re.I)
        if inline_pk_match:
            pk_columns.add(inline_pk_match.group(1))

        for fk_match in re.finditer(
            r"foreign key \((\w+)\) references (\w+) \((\w+)\)",
            body,
            re.I,
        ):
            column, ref_table, ref_column = fk_match.groups()
            fk_columns.add(column)
            fks.append(ForeignKey(table_name, column, ref_table, ref_column))

        columns: list[Column] = []
        for line in body.splitlines():
            stripped = line.strip().rstrip(",")
            if not stripped or stripped.lower().startswith(("constraint", "foreign key", "unique", "primary key")):
                continue
            match = re.match(r"^(\w+)\s+.*?(?:comment '([^']+)')?$", stripped, re.I)
            if not match:
                continue
            name, comment = match.groups()
            if name.lower() in {"on", "references"}:
                continue
            columns.append(Column(name, comment or name, name in pk_columns, name in fk_columns))

        tables[table_name] = Table(table_name, table_comment, columns)

    return tables, fks


def attr_positions(x: int, y: int, count: int) -> list[tuple[int, int]]:
    positions: list[tuple[int, int]] = []
    top = min(3, count)
    for i in range(top):
        positions.append((x - 112 + i * 112, y - 95))

    remaining = count - top
    left = min(3, (remaining + 1) // 2)
    right = min(4, remaining - left)
    for i in range(left):
        positions.append((x - 190, y - 18 + i * 64))
    for i in range(right):
        positions.append((x + 165, y - 18 + i * 64))

    remaining = count - len(positions)
    for i in range(remaining):
        positions.append((x - 112 + i * 112, y + 112))
    return positions


def column_label(column: Column) -> str:
    prefix = []
    if column.is_pk:
        prefix.append("主键")
    if column.is_fk:
        prefix.append("外键")
    marker = f"{'/'.join(prefix)} " if prefix else ""
    return f"{marker}{chinese_label(column.comment)}"


def chinese_label(value: str) -> str:
    replacements = {
        "ID": "编号",
        "id": "编号",
        "JSON格式": "结构化格式",
        "JSON": "结构化数据",
        "PDF文件路径": "报告文件路径",
        "PDF": "报告文件",
        "TextRank": "关键词权重",
        "0-1": "零到一",
        "progress_stage": "进度阶段",
        "progress_message": "进度消息",
        "progress_updated_at": "进度更新时间",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(r"[（(].*?[）)]", "", value)
    value = re.sub(r"\s+", "", value)
    return value


def draw_entity(cells: list[str], edges: list[str], table: Table, x: int, y: int) -> None:
    entity_id = f"table-{table.name}"
    cells.append(cell(entity_id, chinese_label(table.comment), ENTITY_STYLE, x, y, 150, 54))
    columns = [column for column in table.columns if column.name in CORE_COLUMNS[table.name]]
    for index, column in enumerate(columns, start=1):
        ax, ay = attr_positions(x, y, len(columns))[index - 1]
        attr_id = f"{entity_id}-attr-{column.name}"
        cells.append(cell(attr_id, column_label(column), ATTR_STYLE, ax, ay, 132, 36))
        edges.append(edge(f"{attr_id}-edge", entity_id, attr_id))


def draw_relation(cells: list[str], edges: list[str], fk: ForeignKey) -> None:
    rel_id = f"rel-{fk.table}-{fk.column}"
    x, y = RELATION_POSITIONS[(fk.table, fk.column)]
    label = RELATION_LABELS.get((fk.table, fk.column), "属于")
    cells.append(cell(rel_id, label, REL_STYLE, x, y, 86, 58))
    edges.append(edge(f"{rel_id}-one", f"table-{fk.ref_table}", rel_id, "一"))
    edges.append(edge(f"{rel_id}-many", rel_id, f"table-{fk.table}", "多"))


def build_drawio(sql: str) -> str:
    tables, fks = parse_sql(sql)
    cells = [
        cell("title", "数据库实体关系图", TITLE_STYLE, 985, 35, 300, 42),
        cell(
            "subtitle",
            "根据建表脚本绘制，主键和外键已在属性中标注",
            "text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;fontSize=12;fontColor=#666666;",
            860,
            72,
            540,
            28,
        ),
    ]
    edges: list[str] = []

    for table_name, position in TABLE_POSITIONS.items():
        draw_entity(cells, edges, tables[table_name], *position)

    for fk in fks:
        draw_relation(cells, edges, fk)

    inner = "\n".join(cells + edges)
    return f'''<mxfile host="app.diagrams.net" modified="2026-05-08T00:00:00.000Z" agent="5.0" version="21.0.0" type="device">
  <diagram name="基于SQL数据库E-R图" id="sql-er-diagram">
    <mxGraphModel dx="2300" dy="1800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="2260" pageHeight="1680" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{inner}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
'''


def main() -> None:
    sql = SQL_PATH.read_text(encoding="utf-8")
    DIAGRAM_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    DRAWIO_PATH.write_text(build_drawio(sql), encoding="utf-8")
    subprocess.run(
        ["drawio", "-x", "-f", "png", "-o", str(PNG_PATH), str(DRAWIO_PATH)],
        cwd=str(ROOT),
        check=True,
    )
    print(f"drawio: {DRAWIO_PATH}")
    print(f"png: {PNG_PATH}")


if __name__ == "__main__":
    main()
