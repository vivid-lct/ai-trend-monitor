"""
coze_client.py - Coze API 客户端（Mode 2 专用）
使用 cozepy SDK 以流式响应方式调用 Coze Bot，完成 AI 趋势摘要分析
"""
import logging
from typing import List

from cozepy import Coze, TokenAuth, Message, ChatEventType, COZE_CN_BASE_URL

from src.fetchers.base_fetcher import Item

logger = logging.getLogger(__name__)


class CozeClient:
    """Coze API 客户端（基于 cozepy SDK，流式响应）"""

    def __init__(self, api_key: str, bot_id: str, user_id: str = "ai_trend_tracker"):
        self._bot_id = bot_id
        self._user_id = user_id
        self._coze = Coze(
            auth=TokenAuth(token=api_key),
            base_url=COZE_CN_BASE_URL,
        )

    def send(self, items: List[Item]) -> dict:
        """
        将高分条目发送给 Coze Bot，流式接收分析报告。
        优先取 score>=60 的前20条，不足时兜底取前10条。
        返回 {"status": "ok", "reply": "...", "token_count": N}
        """
        high_items = [i for i in items if i.score >= 60][:20]
        if not high_items:
            high_items = items[:10]

        prompt = self._build_prompt(high_items)

        reply_parts: List[str] = []
        token_count = 0

        try:
            print("\n[Coze] 正在连接云端大模型，请稍候...", end="", flush=True)
            first_chunk = True
            for event in self._coze.chat.stream(
                bot_id=self._bot_id,
                user_id=self._user_id,
                additional_messages=[
                    Message.build_user_question_text(prompt),
                ],
            ):
                if event.event == ChatEventType.CONVERSATION_MESSAGE_DELTA:
                    if first_chunk:
                        print(" ✓ 已连接，模型分析中...\n")
                        first_chunk = False
                    chunk = event.message.content
                    print(chunk, end="", flush=True)
                    reply_parts.append(chunk)

                if event.event == ChatEventType.CONVERSATION_CHAT_COMPLETED:
                    token_count = event.chat.usage.token_count if event.chat.usage else 0

            print()  # 流式输出结束换行
            reply = "".join(reply_parts)
            return {"status": "ok", "reply": reply, "token_count": token_count}

        except Exception as e:
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
            lines.append(f"   来源：{item.source} | 时间：{pub} | 评分：{item.score:.0f}")
            if item.is_breaking_change:
                lines.append("   ⚠️ Breaking Change")
            if item.content:
                lines.append(f"   摘要：{item.content[:200]}")
            lines.append("")
        return "\n".join(lines)
