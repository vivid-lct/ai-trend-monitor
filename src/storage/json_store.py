"""
json_store.py - JSON 文件存储模块
负责读写 data/latest.json、data/last_run.json、data/archive/YYYY-MM.json

存储策略：
  - latest.json：滚动合并，新条目 + 历史条目合并去重，保留最近 keep_days 天
    → 始终是"最近一段时间的有效内容"，文件大小稳定可控
  - archive/YYYY-MM.json：追加式，每次运行将新条目追加到当月文件，月底归档
  - 避免单文件无限膨胀，每月数据量可控
"""
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from src.fetchers.base_fetcher import Item


class JsonStore:
    """JSON 文件存储管理器"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.latest_path = self.data_dir / "latest.json"
        self.last_run_path = self.data_dir / "last_run.json"
        self.archive_dir = self.data_dir / "archive"

    def is_cold_start(self) -> bool:
        """判断是否首次运行（无历史数据）"""
        return not self.latest_path.exists()

    def get_last_run_time(self) -> Optional[datetime]:
        """获取上次运行时间，用于增量采集"""
        if not self.last_run_path.exists():
            return None
        data = json.loads(self.last_run_path.read_text(encoding="utf-8"))
        return datetime.fromisoformat(data["last_run_at"])

    def get_existing_urls(self) -> set:
        """获取已存储的所有 URL，用于去重"""
        if not self.latest_path.exists():
            return set()
        data = json.loads(self.latest_path.read_text(encoding="utf-8"))
        return {item["url"] for item in data.get("items", [])}

    def save(self, items: List[Item], keep_days: int = 30) -> None:
        """
        保存条目：
        - latest.json：滚动合并，新条目 + 历史条目合并去重，保留最近 keep_days 天
        - archive/YYYY-MM.json：追加式，将新条目追加到当月文件
        """
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc)
        new_dicts = [self._to_dict(i) for i in items]

        # 1. 滚动合并写入 latest.json
        merged = self._merge_with_existing(new_dicts, now, keep_days)
        payload = {
            "generated_at": now.isoformat(),
            "total": len(merged),
            "items": merged,
        }
        self.latest_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        # 2. 追加写入月度归档 archive/YYYY-MM.json
        month_key = now.strftime("%Y-%m")
        archive_path = self.archive_dir / f"{month_key}.json"
        self._append_to_monthly_archive(archive_path, new_dicts, now)

    def _merge_with_existing(
        self, new_dicts: list, now: datetime, keep_days: int
    ) -> list:
        """将新条目与 latest.json 中的历史条目合并，去重并裁剪到 keep_days 天内"""
        from datetime import timedelta
        cutoff = now - timedelta(days=keep_days)

        # 读取已有条目
        existing = []
        if self.latest_path.exists():
            try:
                data = json.loads(self.latest_path.read_text(encoding="utf-8"))
                existing = data.get("items", [])
            except (json.JSONDecodeError, KeyError):
                existing = []

        # 过滤掉超出时间窗口的旧条目
        def within_window(item_dict: dict) -> bool:
            try:
                pub = datetime.fromisoformat(item_dict["published_at"])
                return pub >= cutoff
            except Exception:
                return True  # 解析失败则保留

        existing = [i for i in existing if within_window(i)]

        # 合并：新条目优先，按 URL 去重
        existing_urls = {i["url"] for i in existing}
        for d in new_dicts:
            if d["url"] not in existing_urls:
                existing.append(d)
                existing_urls.add(d["url"])

        # 按评分降序排序
        existing.sort(key=lambda x: x.get("score", 0), reverse=True)
        return existing

    def _append_to_monthly_archive(
        self, archive_path: Path, new_items: list, now: datetime
    ) -> None:
        """将新条目追加到月度归档文件，按 URL 去重"""
        if archive_path.exists():
            try:
                existing = json.loads(archive_path.read_text(encoding="utf-8"))
                all_items = existing.get("items", [])
            except (json.JSONDecodeError, KeyError):
                all_items = []
        else:
            all_items = []

        existing_urls = {item["url"] for item in all_items}
        added = [i for i in new_items if i["url"] not in existing_urls]
        all_items.extend(added)

        payload = {
            "month": now.strftime("%Y-%m"),
            "last_updated": now.isoformat(),
            "total": len(all_items),
            "items": all_items,
        }
        archive_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def load_latest(self) -> List[dict]:
        """加载最新采集结果（返回原始 dict 列表）"""
        if not self.latest_path.exists():
            return []
        return json.loads(self.latest_path.read_text(encoding="utf-8")).get("items", [])

    def update_last_run_time(self) -> None:
        """更新上次运行时间"""
        now = datetime.now(timezone.utc)
        self.last_run_path.write_text(
            json.dumps({"last_run_at": now.isoformat()}, ensure_ascii=False),
            encoding="utf-8",
        )

    def _to_dict(self, item: Item) -> dict:
        d = asdict(item)
        d["published_at"] = item.published_at.isoformat()
        return d
