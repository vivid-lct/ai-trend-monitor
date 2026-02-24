"""
filter.py - 阈值过滤规则引擎
根据 settings.yaml 中的阈值规则过滤低质量内容
注意：评分 < 30 的内容不在此处过滤，仅在 HTML 展示层灰显
"""
from datetime import datetime, timedelta, timezone
from typing import List

from src.fetchers.base_fetcher import Item


class ThresholdFilter:
    """阈值过滤器"""

    def __init__(self, config: dict):
        self.config = config

    def filter(self, items: List[Item]) -> List[Item]:
        """过滤不符合阈值的条目，返回通过的条目列表"""
        return [item for item in items if self._passes(item)]

    def _passes(self, item: Item) -> bool:
        # 规则 1：标题和 URL 不能为空
        if not item.title.strip() or not item.url.strip():
            return False
        # 规则 2：HN 帖子必须达到最低分数（双重保障）
        if item.source_type == "hn":
            min_hn = self.config.get("hacker_news_min", 50)
            if item.raw_score < min_hn:
                return False
        # 规则 3：发布时间不能是未来（容错 ±1 小时）
        now = datetime.now(timezone.utc)
        if item.published_at > now + timedelta(hours=1):
            return False
        return True
