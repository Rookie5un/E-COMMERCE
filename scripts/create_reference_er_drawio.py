from __future__ import annotations

import html
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIAGRAM_DIR = ROOT / "docs" / "diagrams"
FIGURE_DIR = ROOT / "docs" / "figures"
DRAWIO_PATH = DIAGRAM_DIR / "10_参考图数据库E-R图.drawio"
PNG_PATH = FIGURE_DIR / "figure_4_11_database_er_reference.png"


ENTITY_STYLE = (
    "rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#111111;"
    "strokeWidth=1.2;fontSize=13;fontColor=#111111;"
)
ATTR_STYLE = (
    "ellipse;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#111111;"
    "strokeWidth=1;fontSize=12;fontColor=#111111;"
)
REL_STYLE = (
    "rhombus;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#111111;"
    "strokeWidth=1;fontSize=12;fontColor=#111111;"
)
TITLE_STYLE = (
    "text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;"
    "whiteSpace=wrap;rounded=0;fontSize=18;fontStyle=1;fontColor=#111111;"
)
EDGE_STYLE = (
    "edgeStyle=none;rounded=0;html=1;endArrow=none;"
    "strokeColor=#111111;strokeWidth=1;"
)


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def cell(cell_id: str, value: str, style: str, x: int, y: int, w: int, h: int) -> str:
    return f'''        <mxCell id="{cell_id}" value="{esc(value)}" style="{style}" vertex="1" parent="1">
          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>
        </mxCell>'''


def edge(edge_id: str, source: str, target: str, label: str = "") -> str:
    label_xml = ""
    if label:
        label_xml = f'''
        <mxCell id="{edge_id}-label" value="{esc(label)}" style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];fontSize=11;fontColor=#111111;" vertex="1" connectable="0" parent="{edge_id}">
          <mxGeometry x="0" y="-8" relative="1" as="geometry">
            <mxPoint as="offset"/>
          </mxGeometry>
        </mxCell>'''
    return f'''        <mxCell id="{edge_id}" value="" style="{EDGE_STYLE}" edge="1" parent="1" source="{source}" target="{target}">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>{label_xml}'''


def entity(cells: list[str], edges: list[str], name: str, label: str, x: int, y: int, attrs: list[tuple[str, int, int]]) -> None:
    cells.append(cell(name, label, ENTITY_STYLE, x, y, 108, 42))
    for i, (attr, ax, ay) in enumerate(attrs, start=1):
        attr_id = f"{name}-attr-{i}"
        cells.append(cell(attr_id, attr, ATTR_STYLE, ax, ay, 96, 36))
        edges.append(edge(f"{name}-attr-edge-{i}", name, attr_id))


def relation(cells: list[str], edges: list[str], rel_id: str, label: str, x: int, y: int, links: list[tuple[str, str]]) -> None:
    cells.append(cell(rel_id, label, REL_STYLE, x, y, 68, 50))
    for i, (target, card) in enumerate(links, start=1):
        edges.append(edge(f"{rel_id}-edge-{i}", rel_id, target, card))


def build_drawio() -> str:
    cells: list[str] = [
        cell("title", "数据库 E-R 图", TITLE_STYLE, 470, 24, 220, 34),
        cell("subtitle", "参考图 4.11 结构绘制", "text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;fontSize=12;fontColor=#666666;", 485, 54, 190, 26),
    ]
    edges: list[str] = []

    entity(
        cells,
        edges,
        "account",
        "账号信息",
        520,
        560,
        [
            ("账号id", 446, 520),
            ("用户名", 536, 505),
            ("密码", 630, 520),
        ],
    )
    entity(
        cells,
        edges,
        "module",
        "模组信息",
        185,
        310,
        [
            ("模组id", 80, 300),
            ("模组名", 78, 372),
            ("用户名", 68, 230),
            ("模组编号", 300, 286),
            ("创作者", 305, 350),
        ],
    )
    entity(
        cells,
        edges,
        "module_score",
        "模组评分",
        185,
        130,
        [
            ("模组评分id", 65, 126),
            ("模组编号", 120, 62),
            ("评分", 230, 62),
            ("评分来源", 315, 95),
        ],
    )
    entity(
        cells,
        edges,
        "user_score",
        "用户评分",
        482,
        135,
        [
            ("用户评分id", 400, 130),
            ("用户名", 476, 70),
            ("评分", 575, 76),
            ("评分来源", 640, 134),
        ],
    )
    entity(
        cells,
        edges,
        "player_recommend",
        "扮演者推荐记录",
        780,
        120,
        [
            ("扮演者推荐记录id", 690, 80),
            ("用户名", 778, 50),
            ("扮演者用户名", 870, 54),
            ("用户评分", 965, 104),
        ],
    )
    entity(
        cells,
        edges,
        "user",
        "用户信息",
        840,
        310,
        [
            ("用户id", 762, 282),
            ("QQ号", 732, 348),
            ("用户名", 840, 255),
            ("昵称", 948, 280),
            ("性别", 1038, 310),
            ("用户扩散状态", 1008, 370),
            ("用户组", 948, 430),
            ("住地", 844, 440),
            ("年龄", 742, 430),
        ],
    )
    entity(
        cells,
        edges,
        "post",
        "帖子信息",
        180,
        745,
        [
            ("帖子id", 72, 724),
            ("用户名", 82, 650),
            ("帖子编号", 172, 640),
            ("帖子类型", 300, 678),
            ("帖子归属", 318, 770),
            ("帖子内容", 60, 812),
            ("帖子楼层", 308, 844),
        ],
    )
    entity(
        cells,
        edges,
        "battle_score",
        "战报评分",
        155,
        1110,
        [
            ("战报评分id", 120, 1212),
            ("帖子编号", 70, 1166),
            ("评分", 250, 1210),
            ("评分来源", 330, 1165),
        ],
    )
    entity(
        cells,
        edges,
        "battle_recommend",
        "战报推荐记录",
        486,
        930,
        [
            ("战报推荐记录id", 410, 1018),
            ("用户名", 550, 1034),
            ("帖子编号", 666, 990),
            ("战报评分", 602, 870),
        ],
    )
    entity(
        cells,
        edges,
        "group_recommend",
        "跑团推荐记录",
        462,
        1120,
        [
            ("跑团推荐记录id", 370, 1210),
            ("用户名", 520, 1225),
            ("帖子编号", 637, 1210),
            ("跑团评分", 668, 1128),
        ],
    )
    entity(
        cells,
        edges,
        "role_attr",
        "角色属性",
        812,
        575,
        [
            ("角色属性id", 690, 575),
            ("角色编号", 735, 662),
            ("属性值", 760, 510),
            ("属性名", 845, 500),
        ],
    )
    entity(
        cells,
        edges,
        "role_recommend",
        "角色推荐记录",
        958,
        575,
        [
            ("角色推荐记录id", 955, 666),
            ("用户名", 1038, 665),
            ("角色编号", 1038, 526),
            ("角色评分", 948, 508),
        ],
    )
    entity(
        cells,
        edges,
        "role",
        "角色信息",
        780,
        850,
        [
            ("角色id", 1022, 810),
            ("用户名", 995, 738),
            ("姓名", 1040, 870),
            ("世界观", 1035, 935),
            ("世代", 1030, 1000),
            ("所属模组", 1015, 1065),
            ("角色编号", 812, 1038),
        ],
    )
    entity(
        cells,
        edges,
        "role_score",
        "角色评分",
        820,
        1160,
        [
            ("角色评分id", 980, 1146),
            ("角色编号", 720, 1216),
            ("评分", 820, 1262),
            ("评分来源", 928, 1258),
        ],
    )

    relation(cells, edges, "rel_module_score", "属于", 205, 220, [("module_score", "n"), ("module", "1")])
    relation(cells, edges, "rel_upload", "上传", 345, 332, [("module", "n"), ("account", "1")])
    relation(cells, edges, "rel_module_post", "使用", 210, 520, [("module", "1"), ("post", "n")])
    relation(cells, edges, "rel_user_score", "属于", 520, 315, [("user_score", "n"), ("account", "1")])
    relation(cells, edges, "rel_player_account", "属于", 660, 335, [("player_recommend", "n"), ("account", "1")])
    relation(cells, edges, "rel_user_account", "属于", 735, 438, [("user", "1"), ("account", "1")])
    relation(cells, edges, "rel_role_attr", "属于", 820, 690, [("role_attr", "n"), ("role", "1")])
    relation(cells, edges, "rel_role_rec", "属于", 955, 705, [("role_recommend", "n"), ("role", "1")])
    relation(cells, edges, "rel_role_account", "属于", 665, 705, [("account", "1"), ("role", "n")])
    relation(cells, edges, "rel_use_role", "使用", 548, 770, [("account", "1"), ("post", "n"), ("role", "n")])
    relation(cells, edges, "rel_post_account", "属于", 340, 675, [("post", "n"), ("account", "1")])
    relation(cells, edges, "rel_post_battle_score", "属于", 135, 940, [("post", "1"), ("battle_score", "n")])
    relation(cells, edges, "rel_post_group", "属于", 250, 940, [("post", "1"), ("group_recommend", "n")])
    relation(cells, edges, "rel_post_battle_rec", "属于", 375, 910, [("post", "1"), ("battle_recommend", "n")])
    relation(cells, edges, "rel_role_score", "属于", 835, 1065, [("role", "1"), ("role_score", "n")])

    inner = "\n".join(cells + edges)
    return f'''<mxfile host="app.diagrams.net" modified="2026-05-08T00:00:00.000Z" agent="5.0" version="21.0.0" type="device">
  <diagram name="数据库E-R图" id="reference-er-diagram">
    <mxGraphModel dx="1422" dy="1460" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1160" pageHeight="1320" math="0" shadow="0">
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
    DIAGRAM_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    DRAWIO_PATH.write_text(build_drawio(), encoding="utf-8")
    subprocess.run(
        ["drawio", "-x", "-f", "png", "-o", str(PNG_PATH), str(DRAWIO_PATH)],
        cwd=str(ROOT),
        check=True,
    )
    print(f"drawio: {DRAWIO_PATH}")
    print(f"png: {PNG_PATH}")


if __name__ == "__main__":
    main()
