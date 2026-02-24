"""
rss_fetcher.py - RSS / 官方博客采集器
通过 feedparser 解析 RSS Feed
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import feedparser

from .base_fetcher import BaseFetcher, Item

logger = logging.getLogger(__name__)


class RSSFetcher(BaseFetcher):
    """RSS / 官方博客采集器"""

    def fetch(self, since: Optional[datetime] = None) -> list[Item]:
        items = []
        feeds = self.config.get("sources", {}).get("rss", {}).get("feeds", [])

        for feed_cfg in feeds:
            url = feed_cfg["url"]
            try:
                feed = feedparser.parse(url)
            except Exception as e:
                logger.warning(f"RSS 解析失败 {url}: {e}")
                continue

            for entry in feed.entries:
                pub = self._parse_time(entry)
                if pub is None:
                    continue
                link = entry.get("link", "")
                if not link:
                    continue
                if since and pub <= since:
                    continue

                summary = entry.get("summary", "") or entry.get("description", "") or ""
                items.append(
                    Item(
                        title=entry.get("title", "").strip(),
                        url=link,
                        source=feed_cfg["name"],
                        source_type="rss",
                        category=feed_cfg.get("category", "other"),
                        published_at=pub,
                        content=self._clean_html(summary)[:500],
                    )
                )

        return items

    def _parse_time(self, entry) -> Optional[datetime]:
        """将 feedparser 的 time.struct_time 转为 UTC aware datetime"""
        t = entry.get("published_parsed") or entry.get("updated_parsed")
        if t is None:
            return None
        try:
            return datetime(*t[:6], tzinfo=timezone.utc)
        except Exception:
            return None

    def _clean_html(self, text: str) -> str:
        """简单去除 HTML 标签"""
        return re.sub(r"<[^>]+>", "", text).strip()
