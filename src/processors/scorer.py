"""
scorer.py - 综合评分计算器
评分公式：来源权重(30) + 内容类型权重(25) + 社区热度(25) + 时效性(20)
Breaking Change 额外加 15 分，总分 clamp 到 100
"""
from datetime import datetime, timezone
from typing import List

from src.fetchers.base_fetcher import Item


class Scorer:
    """综合评分计算器"""

    SOURCE_W = {"rss": 30, "github": 25, "pwc": 22, "hn": 18}
    CATEGORY_W = {
        "llm": 25, "framework": 22, "paper": 20,
        "rag": 18, "agent": 18, "workflow": 15, "other": 8,
    }

    def score(self, items: List[Item]) -> List[Item]:
        """计算每个条目的综合评分，写入 item.score"""
        now = datetime.now(timezone.utc)
        for item in items:
            s = self.SOURCE_W.get(item.source_type, 10)
            s += self.CATEGORY_W.get(item.category, 8)
            if item.is_breaking_change:
                s += 15
            s += self._hot_score(item)
            s += self._time_score(item, now)
            item.score = min(round(s, 1), 100.0)
        return items

    def _hot_score(self, item: Item) -> float:
        """社区热度，归一化到 0~25"""
        if item.source_type == "hn":
            return min(item.raw_score / 500 * 25, 25)
        if item.source_type == "pwc":
            stars = item.extra.get("stars", 0)
            return min(stars / 1000 * 25, 25)
        if item.source_type == "github":
            stars = item.extra.get("stars", 0)
            if stars > 0:
                return min(stars / 100_000 * 25, 25)  # 10万star=满分
            return 10  # 无 star 数据时给默认中等热度
        return 10  # rss 给默认中等热度

    def _time_score(self, item: Item, now: datetime) -> float:
        """时效性评分，0~20"""
        hours = (now - item.published_at).total_seconds() / 3600
        if hours <= 24:
            return 20
        if hours <= 48:
            return 15
        if hours <= 168:   # 7 天
            return 10
        if hours <= 720:   # 30 天
            return 5
        return 2
