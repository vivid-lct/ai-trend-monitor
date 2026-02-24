"""
classifier.py - 关键词分类器 + Breaking Change 检测
根据 settings.yaml 中的关键词对条目进行分类，并标记 Breaking Change
"""
from typing import List

from src.fetchers.base_fetcher import Item

BREAKING_KEYWORDS = [
    "breaking change",
    "breaking:",
    "breaking -",
    "deprecated",
    "deprecation",
    "removed in",
    "removal of",
    "migration guide",
    "migration required",
    "incompatible",
    "backward incompatible",
    "no longer supported",
]

CATEGORY_PRIORITY = ["framework", "llm", "rag", "agent", "workflow"]


class Classifier:
    """关键词分类器"""

    def __init__(self, keywords_config: dict):
        self.kw = {
            k: [w.lower() for w in v]
            for k, v in keywords_config.items()
        }

    def classify(self, items: List[Item]) -> List[Item]:
        """为每个条目设置 category、is_breaking_change、tags"""
        for item in items:
            text = (item.title + " " + item.content).lower()
            if item.category != "paper":
                item.category = self._detect_category(text)
            item.is_breaking_change = any(kw in text for kw in BREAKING_KEYWORDS)
            item.tags = self._extract_tags(text, item.category)
        return items

    def _detect_category(self, text: str) -> str:
        for cat in CATEGORY_PRIORITY:
            if any(kw in text for kw in self.kw.get(cat, [])):
                return cat
        return "other"

    def _extract_tags(self, text: str, category: str) -> list:
        tags = [category]
        for group, words in self.kw.items():
            for w in words:
                if w in text and w not in tags:
                    tags.append(w)
                    break
        return tags[:5]
