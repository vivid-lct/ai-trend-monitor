"""
deduplicator.py - 去重模块
基于 URL 精确匹配去除重复条目（跨运行 + 批内去重）
"""
from typing import List

from src.fetchers.base_fetcher import Item


class Deduplicator:
    """去重器"""

    def __init__(self, existing_urls: set):
        self.existing_urls = existing_urls

    def deduplicate(self, items: List[Item]) -> List[Item]:
        """去除已存在或本批次重复的条目"""
        seen = {self._norm(u) for u in self.existing_urls}
        result = []
        for item in items:
            n = self._norm(item.url)
            if n not in seen:
                seen.add(n)
                result.append(item)
        return result

    def _norm(self, url: str) -> str:
        """URL 标准化：去末尾斜杠，统一 https，小写"""
        return url.rstrip("/").replace("http://", "https://").lower()
