"""
coze_client.py - Coze API 客户端（Mode 2 专用，开发中）
将采集数据格式化为 Prompt 发送给 Coze Bot，获取 AI 摘要和推送结果
"""
import logging
from typing import List

import requests

from src.fetchers.base_fetcher import Item

logger = logging.getLogger(__name__)


class CozeClient:
    """Coze API 客户端"""

    def __init__(self, api_key: str, bot_id: str, api_base: str = "https://api.coze.cn"):
        self.api_key = api_key
        self.bot_id = bot_id
        self.api_base = api_base.rstrip("/")

    def send(self, items: List[Item]) -> dict:
        """
        将高分条目发送给 Coze Bot 处理
        :param items: 已过滤、评分的条目列表（只发送 score >= 60 的前20条）
        :return: Coze 返回的处理结果摘要
        """
        high_items = [i for i in items if i.score >= 60][:20]
        if not high_items:
            high_items = items[:10]  # 兜底：至少发10条

        prompt = self._build_prompt(high_items)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "bot_id": self.bot_id,
            "user_id": "ai_trend_tracker",
            "stream": False,
            "auto_save_history": False,
            "additional_messages": [
                {"role": "user", "content": prompt, "content_type": "text"}
            ],
        }
        try:
            resp = requests.post(
                f"{self.api_base}/v3/chat",
                headers=headers,
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            # 提取 Coze 回复文本
            messages = data.get("data", {}).get("messages", [])
            reply = next(
                (m.get("content", "") for m in messages if m.get("role") == "assistant"),
                "（无回复）",
            )
            return {"status": "ok", "reply": reply, "raw": data}
        except requests.RequestException as e:
            logger.error(f"Coze API 调用失败: {e}")
            return {"status": "error", "error": str(e)}

    def _build_prompt(self, items: List[Item]) -> str:
        lines = [
            "以下是今日 AI 技术趋势采集数据，请帮我：",
            "1. 用中文总结最重要的 3~5 条动态",
            "2. 特别标注 Breaking Change",
            "3. 给出你的观点：哪条最值得关注，理由是什么",
            "",
            "---数据开始---",
            "",
        ]
        for i, item in enumerate(items, 1):
            pub = item.published_at.strftime("%Y-%m-%d")
            lines.append(f"{i}. [{item.category.upper()}] {item.title}")
            lines.append(f"   来源：{item.source} | 时间：{pub} | 评分：{item.score}")
            if item.is_breaking_change:
                lines.append("   ⚠️ Breaking Change")
            if item.content:
                lines.append(f"   摘要：{item.content[:200]}")
            lines.append("")
        return "\n".join(lines)
