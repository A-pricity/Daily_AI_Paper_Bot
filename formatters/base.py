"""格式化器抽象基类"""

from abc import ABC, abstractmethod
from typing import Dict, List


class BaseFormatter(ABC):
    """消息格式化器基类"""

    @abstractmethod
    def format_report(self, papers: List[Dict], metadata: Dict = None) -> str:
        """
        格式化完整的报告

        Args:
            papers: 论文列表
            metadata: 元数据（日期、主题等）

        Returns:
            格式化后的消息
        """
        pass

    @abstractmethod
    def format_paper(self, paper: Dict) -> str:
        """
        格式化单篇论文

        Args:
            paper: 论文字典

        Returns:
            格式化后的论文
        """
        pass
