"""
hn_fetcher.py - Hacker News 采集器
通过 HN Algolia API 采集高分帖子，含阈值过滤
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

from .base_fetcher import BaseFetcher, Item

logger = logging.getLogger(__name__)

CORE_KEYWORDS = [
    "LangChain", "LlamaIndex", "RAG", "AI Agent",
    "LLM", "Coze", "DeepSeek", "MCP", "Claude", "GPT",
]


class HNFetcher(BaseFetcher):
    """Hacker News 采集器"""

    API_URL = "https://hn.algolia.com/api/v1/search"

    def fetch(self, since: Optional[datetime] = None) -> list[Item]:
        items = []
        seen_ids: set = set()
        min_score = self.config.get("thresholds", {}).get("hacker_news_min", 50)

        for keyword in CORE_KEYWORDS:
            numeric_filters = f"points>={min_score}"
            if since:
                numeric_filters += f",created_at_i>={int(since.timestamp())}"

            params = {
                "query": keyword,
                "tags": "story",
                "numericFilters": numeric_filters,
                "hitsPerPage": 15,
            }
            try:
                resp = requests.get(self.API_URL, params=params, timeout=10)
                resp.raise_for_status()
            except requests.RequestException as e:
                logger.warning(f"HN 请求失败 (keyword={keyword}): {e}")
                continue

            for hit in resp.json().get("hits", []):
                hn_id = hit.get("objectID")
                if not hn_id or hn_id in seen_ids:
                    continue
                seen_ids.add(hn_id)

                pub = datetime.fromtimestamp(hit["created_at_i"], tz=timezone.utc)
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hn_id}"

                items.append(
                    Item(
                        title=hit.get("title", ""),
                        url=url,
                        source="Hacker News",
                        source_type="hn",
                        category="other",
                        published_at=pub,
                        raw_score=hit.get("points", 0),
                        extra={
                            "hn_id": hn_id,
                            "comments": hit.get("num_comments", 0),
                        },
                    )
                )

        return items
