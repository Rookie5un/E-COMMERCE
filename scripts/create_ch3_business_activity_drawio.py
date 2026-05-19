from __future__ import annotations

import html
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIAGRAM_DIR = ROOT / "docs" / "diagrams"
FIG_DIR = ROOT / "docs" / "figures" / "ch3_extra"
DRAWIO_PATH = DIAGRAM_DIR / "08_第三章业务活动图.drawio"
PNG_PATH = FIG_DIR / "figure_3_2_business_activity.png"


def cell(cell_id: str, value: str, style: str, x: int, y: int, w: int, h: int) -> str:
    return f'''        <mxCell id="{cell_id}" value="{html.escape(value)}" style="{style}" vertex="1" parent="1">
          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>
        </mxCell>'''


def edge(edge_id: str, source: str, target: str, label: str = "") -> str:
    style = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;strokeWidth=2;strokeColor=#475569;"
    return f'''        <mxCell id="{edge_id}" value="{html.escape(label)}" style="{style}" edge="1" parent="1" source="{source}" target="{target}">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>'''


def build_drawio() -> str:
    title = "rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=none;fontSize=20;fontStyle=1;fontColor=#1f2933;"
    start = "ellipse;html=1;shape=startState;fillColor=#111827;strokeColor=#111827;"
    end = "ellipse;html=1;shape=endState;fillColor=#111827;strokeColor=#111827;"
    action = "rounded=1;whiteSpace=wrap;html=1;arcSize=8;fillColor=#e0f2fe;strokeColor=#0284c7;fontSize=14;fontStyle=1;fontColor=#0f172a;"
    decision = "rhombus;whiteSpace=wrap;html=1;fillColor=#fef3c7;strokeColor=#d97706;fontSize=13;fontStyle=1;fontColor=#0f172a;"
    note = "rounded=1;whiteSpace=wrap;html=1;arcSize=8;fillColor=#f8fafc;strokeColor=#cbd5e1;fontSize=12;fontColor=#334155;"

    cells = [
        cell("title", "评论分析业务活动图", title, 390, 25, 320, 42),
        cell("start", "", start, 525, 92, 30, 30),
        cell("a1", "用户登录系统", action, 465, 145, 150, 48),
        cell("a2", "创建或选择商品", action, 465, 220, 150, 48),
        cell("a3", "上传CSV评论文件", action, 465, 295, 150, 48),
        cell("d1", "导入校验通过？", decision, 448, 370, 185, 80),
        cell("a4", "查看导入失败原因并修正文件", action, 160, 386, 205, 52),
        cell("a5", "查看批次统计", action, 465, 485, 150, 48),
        cell("a6", "创建分析任务", action, 465, 560, 150, 48),
        cell("d2", "任务执行完成？", decision, 448, 635, 185, 80),
        cell("a7", "等待或刷新任务状态", action, 730, 649, 190, 52),
        cell("a8", "查看分析总览", action, 465, 750, 150, 48),
        cell("a9", "生成或查看分析报告", action, 445, 825, 190, 48),
        cell("end", "", end, 525, 905, 32, 32),
        cell("n1", "校验内容包括必要字段、空评论、重复评论和格式异常。", note, 665, 382, 250, 46),
        cell("n2", "任务结果包括情感分布、功能点排行和负面问题关键词。", note, 665, 750, 250, 46),
    ]
    edges = [
        edge("e1", "start", "a1"),
        edge("e2", "a1", "a2"),
        edge("e3", "a2", "a3"),
        edge("e4", "a3", "d1"),
        edge("e5", "d1", "a4", "否"),
        edge("e6", "a4", "a3"),
        edge("e7", "d1", "a5", "是"),
        edge("e8", "a5", "a6"),
        edge("e9", "a6", "d2"),
        edge("e10", "d2", "a7", "否"),
        edge("e11", "a7", "d2"),
        edge("e12", "d2", "a8", "是"),
        edge("e13", "a8", "a9"),
        edge("e14", "a9", "end"),
    ]
    inner = "\n".join(cells + edges)
    return f'''<mxfile host="app.diagrams.net" modified="2026-05-06T00:00:00.000Z" agent="5.0" version="21.0.0" type="device">
  <diagram name="第三章业务活动图" id="ch3-business-activity">
    <mxGraphModel dx="1422" dy="1100" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1080" pageHeight="980" math="0" shadow="0">
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
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    DRAWIO_PATH.write_text(build_drawio(), encoding="utf-8")
    subprocess.run(
        ["drawio", "-x", "-f", "png", "-o", str(PNG_PATH), str(DRAWIO_PATH)],
        check=True,
        cwd=str(ROOT),
    )
    print(f"drawio: {DRAWIO_PATH}")
    print(f"png: {PNG_PATH}")


if __name__ == "__main__":
    main()
