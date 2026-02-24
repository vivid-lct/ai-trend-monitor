"""
pwc_fetcher.py - 学术论文采集器（arXiv RSS）
通过 arXiv RSS 采集 AI/ML 最新论文（cs.AI + cs.LG + cs.CL）
注：Papers With Code API 在国内网络不可用，改用 arXiv RSS
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import feedparser

from .base_fetcher import BaseFetcher, Item

logger = logging.getLogger(__name__)

ARXIV_FEEDS = [
    ("https://arxiv.org/rss/cs.AI", "arXiv cs.AI"),
    ("https://arxiv.org/rss/cs.LG", "arXiv cs.LG"),
    ("https://arxiv.org/rss/cs.CL", "arXiv cs.CL"),
]


class PWCFetcher(BaseFetcher):
    """学术论文采集器（arXiv RSS）"""

    def fetch(self, since: Optional[datetime] = None) -> list[Item]:
        items = []
        seen_urls: set = set()
        top_n = self.config.get("sources", {}).get("papers_with_code", {}).get("top_n", 20)

        for feed_url, source_name in ARXIV_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
            except Exception as e:
                logger.warning(f"arXiv RSS 解析失败 {feed_url}: {e}")
                continue

            per_feed = max(1, top_n // len(ARXIV_FEEDS))
            for entry in feed.entries:
                if len([i for i in items if i.source == source_name]) >= per_feed:
                    break
                link = entry.get("link", "")
                if not link or link in seen_urls:
                    continue
                seen_urls.add(link)

                pub = self._parse_time(entry)
                if pub is None:
                    continue
                if since and pub <= since:
                    continue

                summary = re.sub(r"<[^>]+>", "", entry.get("summary", "")).strip()
                items.append(
                    Item(
                        title=entry.get("title", "").strip(),
                        url=link,
                        source=source_name,
                        source_type="pwc",
                        category="paper",
                        published_at=pub,
                        content=summary[:500],
                    )
                )

        return items[:top_n]

    def _parse_time(self, entry) -> Optional[datetime]:
        t = entry.get("published_parsed") or entry.get("updated_parsed")
        if t is None:
            return None
        try:
            return datetime(*t[:6], tzinfo=timezone.utc)
        except Exception:
            return None
