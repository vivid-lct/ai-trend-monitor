"""
base_fetcher.py - 采集器基类
所有采集器继承此类，实现 fetch() 方法
返回统一格式的 Item 列表
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Item:
    """统一数据条目格式"""
    title: str                          # 标题
    url: str                            # 原文链接
    source: str                         # 数据源名称（如 "LangChain GitHub"）
    source_type: str                    # 数据源类型：github / rss / hn / pwc / arxiv
    category: str                       # 分类：framework / llm / rag / agent / workflow / paper / other
    published_at: datetime              # 发布时间
    content: str = ""                   # 正文摘要或描述
    score: float = 0.0                  # 综合评分（0-100）
    is_breaking_change: bool = False    # 是否为 Breaking Change
    tags: list = field(default_factory=list)  # 标签列表
    raw_score: int = 0                  # 原始社区热度分数（HN分数、Stars等）
    extra: dict = field(default_factory=dict) # 扩展字段（版本号、作者等）


class BaseFetcher(ABC):
    """采集器基类"""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def fetch(self, since: Optional[datetime] = None) -> list[Item]:
        """
        采集数据
        :param since: 增量采集起始时间，None 表示全量采集
        :return: Item 列表
        """
        pass

    def is_enabled(self) -> bool:
        return self.config.get("enabled", True)
