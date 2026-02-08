"""数据源基类和接口定义

定义所有数据源的统一接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime


class Paper:
    """论文数据模型"""

    def __init__(
        self,
        title: str,
        authors: List[str],
        abstract: str,
        url: str,
        published: Optional[str] = None,
        source: str = "Unknown"
    ):
        self.title = title
        self.authors = authors
        self.abstract = abstract
        self.url = url
        self.published = published
        self.source = source

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "url": self.url,
            "published": self.published,
            "source": self.source
        }

    def __repr__(self) -> str:
        return f"Paper(title='{self.title[:50]}...', source='{self.source}')"


class BasePaperSource(ABC):
    """数据源抽象基类"""

    def __init__(self, config: dict):
        """
        初始化数据源

        Args:
            config: 数据源配置字典
        """
        self.config = config
        self.enabled = config.get('enabled', False)

    @abstractmethod
    def fetch_papers(self, max_results: int = 5) -> List[Paper]:
        """
        获取论文列表

        Args:
            max_results: 最多获取的论文数量

        Returns:
            论文列表
        """
        pass

    def _log(self, message: str, level: str = "INFO") -> None:
        """日志输出"""
        prefix = {
            "INFO": "✓",
            "WARN": "⚠",
            "ERROR": "✗"
        }
        print(f"{prefix.get(level, '→')} {self.__class__.__name__}: {message}")
