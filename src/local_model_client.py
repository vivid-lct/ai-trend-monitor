"""
local_model_client.py - 本地大模型客户端（Mode 4）
通过 Ollama 服务调用本地部署的大模型，对 AI 趋势数据进行深度分析
前提：Ollama 已安装并运行，qwen2.5:3b 模型已下载
"""
import logging
from pathlib import Path
from typing import List

import requests
from openai import OpenAI

from src.fetchers.base_fetcher import Item

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"
_DEFAULT_PROMPT_FILE = "ai_analyst.md"

_FALLBACK_PROMPT = "你是一位专业的 AI 技术趋势分析师，请用中文输出结构清晰、简洁实用的分析报告。"


def load_system_prompt(prompt_file: str = _DEFAULT_PROMPT_FILE) -> str:
    """
    从 config/prompts/ 目录加载系统提示词
    :param prompt_file: 提示词文件名（如 ai_analyst.md 或 summarizer.md）
    :return: 提示词文本
    """
    prompt_path = _PROMPTS_DIR / prompt_file
    if prompt_path.exists():
        text = prompt_path.read_text(encoding="utf-8").strip()
        logger.debug(f"已加载提示词：{prompt_path}")
        return text
    logger.warning(f"提示词文件不存在：{prompt_path}，使用内置默认提示词")
    return _FALLBACK_PROMPT


class LocalModelClient:
    """本地大模型客户端，通过 Ollama OpenAI 兼容 API 调用"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:3b",
                 max_tokens: int = 2048, top_n: int = 20,
                 prompt_file: str = _DEFAULT_PROMPT_FILE):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self.top_n = top_n
        self.system_prompt = load_system_prompt(prompt_file)
        self.client = OpenAI(base_url=f"{self.base_url}/v1", api_key="ollama")

    def is_available(self) -> bool:
        """检查 Ollama 服务是否正常运行"""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def get_installed_models(self) -> list:
        """获取已安装模型列表"""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            return []

    def _build_user_prompt(self, items: List[Item]) -> str:
        """将条目列表转换为结构化的用户 prompt"""
        top_items = sorted(items, key=lambda x: x.score, reverse=True)[:self.top_n]
        dates = [i.published_at for i in top_items if i.published_at]
        if dates:
            start_date = min(dates).strftime("%Y-%m-%d")
            end_date = max(dates).strftime("%Y-%m-%d")
            date_ctx = f"{start_date} 至 {end_date}"
        else:
            date_ctx = "近期"
        lines = [
            f"以下是 {date_ctx} 采集的 {len(top_items)} 条 AI 技术资讯，"
            f"按重要性评分（0-100）从高到低排序，总共来自 {len(set(i.source for i in top_items))} 个来源。"
            f"请进行深度分析：\n"
        ]
        for i, item in enumerate(top_items, 1):
            summary = (item.content or "")[:200].strip()
            tags = "、".join(item.tags[:5]) if item.tags else ""
            score_str = f"评分 {item.score:.0f}"
            lines.append(
                f"【{i}】{item.title}（{score_str}）\n"
                f"   来源：{item.source} | 类别：{item.category}"
                + (f" | 标签：{tags}" if tags else "")
                + (f"\n   摘要：{summary}" if summary else "")
            )
        return "\n\n".join(lines)

    def analyze(self, items: List[Item]) -> dict:
        """
        调用本地大模型分析采集数据
        :param items: 已过滤、评分的条目列表
        :return: {"status": "ok"/"error", "report": str, "model": str, "item_count": int}
        """
        if not self.is_available():
            return {"status": "error", "report": "⚠ Ollama 服务未运行，请先启动 Ollama（系统托盘应有图标）"}

        installed = self.get_installed_models()
        if not any(self.model in m for m in installed):
            return {
                "status": "error",
                "report": f"⚠ 模型 {self.model} 未安装，请运行：ollama pull {self.model}\n"
                          f"已安装模型：{', '.join(installed) or '（无）'}"
            }

        if not items:
            return {"status": "error", "report": "⚠ 暂无数据，请先运行 Mode 1 采集数据"}

        user_prompt = self._build_user_prompt(items)
        top_n_actual = min(len(items), self.top_n)

        try:
            logger.info(f"调用本地模型 {self.model} 分析 {top_n_actual} 条数据...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=self.max_tokens,
            )
            report = response.choices[0].message.content
            logger.info(f"本地模型分析完成，输出 {len(report)} 字符")
            return {
                "status": "ok",
                "report": report,
                "model": self.model,
                "item_count": top_n_actual,
            }
        except Exception as e:
            logger.error(f"本地模型调用失败：{e}")
            return {"status": "error", "report": f"⚠ 模型调用失败：{e}"}
