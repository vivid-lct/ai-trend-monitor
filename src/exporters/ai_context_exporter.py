"""
ai_context_exporter.py - AI 上下文导出器
生成 data/ai_context.md，Mode 1 自动执行，供 AI 工具读取分析
格式为结构化 Markdown，AI 可直接作为上下文输入
"""
from pathlib import Path
from typing import List

from src.fetchers.base_fetcher import Item

CATEGORY_NAMES = {
    "framework": "框架更新",
    "llm": "大模型动态",
    "rag": "RAG 技术",
    "agent": "AI Agent",
    "workflow": "工作流",
    "paper": "论文（有开源实现）",
    "other": "其他",
}


class AIContextExporter:
    """AI 上下文 Markdown 导出器"""

    def __init__(self, output_path: str = "data/ai_context.md"):
        self.output_path = Path(output_path)

    def export(self, items: List[Item], generated_at: str = "") -> str:
        """
        导出为 AI 友好的 Markdown 格式
        :param items: 已评分排序的条目列表
        :param generated_at: 生成时间字符串
        :return: 输出文件路径
        """
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# AI 技术趋势数据上下文",
            f"生成时间：{generated_at}",
            f"数据条目：{len(items)} 条（过滤+评分后）",
            "",
            "---",
            "",
        ]

        # Breaking Change 优先展示
        breaking = [i for i in items if i.is_breaking_change]
        if breaking:
            lines.append("## ⚠️ Breaking Change（需立即关注）")
            lines.append("")
            for idx, item in enumerate(breaking, 1):
                lines.extend(self._format_item(idx, item))
            lines.append("")

        # 按分类分组，非 Breaking Change 条目
        non_breaking = [i for i in items if not i.is_breaking_change]
        for cat, cat_name in CATEGORY_NAMES.items():
            cat_items = [i for i in non_breaking if i.category == cat]
            if not cat_items:
                continue
            lines.append(f"## {cat_name}")
            lines.append("")
            for idx, item in enumerate(cat_items, 1):
                lines.extend(self._format_item(idx, item))
            lines.append("")

        content = "\n".join(lines)
        self.output_path.write_text(content, encoding="utf-8")
        return str(self.output_path)

    def _format_item(self, idx: int, item: Item) -> list:
        pub = item.published_at.strftime("%Y-%m-%d")
        bc_mark = " ⚠️ Breaking Change" if item.is_breaking_change else ""
        summary = item.content[:200].replace("\n", " ") if item.content else "（无摘要）"
        return [
            f"{idx}. **[{item.title}]**{bc_mark} - {item.source} (评分: {item.score})",
            f"   - 链接：{item.url}",
            f"   - 时间：{pub}",
            f"   - 摘要：{summary}",
            "",
        ]
