"""
github_fetcher.py - GitHub Release 采集器
采集目标仓库的 Release 信息，自动检测 Breaking Change
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

from .base_fetcher import BaseFetcher, Item

logger = logging.getLogger(__name__)


class GitHubFetcher(BaseFetcher):
    """GitHub Release 采集器"""

    BASE_URL = "https://api.github.com"

    def fetch(self, since: Optional[datetime] = None) -> list[Item]:
        items = []
        token = self.config.get("github_token", "")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"

        repos = self.config.get("sources", {}).get("github", {}).get("repos", [])
        for repo_cfg in repos:
            owner = repo_cfg["owner"]
            repo = repo_cfg["repo"]
            name = repo_cfg["name"]

            # 获取仓库元信息（含 star 数），用于热度评分
            stars = 0
            try:
                meta = requests.get(
                    f"{self.BASE_URL}/repos/{owner}/{repo}", headers=headers, timeout=8
                )
                if meta.status_code == 200:
                    stars = meta.json().get("stargazers_count", 0)
            except requests.RequestException:
                pass

            url = f"{self.BASE_URL}/repos/{owner}/{repo}/releases"
            try:
                resp = requests.get(
                    url, headers=headers, params={"per_page": 10}, timeout=10
                )
                if resp.status_code == 404:
                    logger.debug(f"{owner}/{repo} 无 Release，跳过")
                    continue
                resp.raise_for_status()
            except requests.RequestException as e:
                logger.warning(f"GitHub {owner}/{repo} 请求失败: {e}")
                continue

            for release in resp.json():
                pub_str = release.get("published_at") or release.get("created_at", "")
                if not pub_str:
                    continue
                pub = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                if since and pub <= since:
                    continue

                tag = release.get("tag_name", "")
                rel_name = release.get("name") or ""
                title = f"[{name}] {tag}: {rel_name}".strip(": ")

                items.append(
                    Item(
                        title=title,
                        url=release["html_url"],
                        source=f"{name} GitHub",
                        source_type="github",
                        category="other",
                        published_at=pub,
                        content=(release.get("body") or "")[:500],
                        extra={"version": tag, "repo": f"{owner}/{repo}", "stars": stars},
                    )
                )

        return items
