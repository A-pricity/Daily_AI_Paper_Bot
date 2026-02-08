"""数据源模块 - 负责从不同数据源获取论文"""

from .base import BasePaperSource, Paper
from .arxiv_source import ArxivSource
from .springer_source import SpringerSource
from .semantic_scholar_source import SemanticScholarSource

__all__ = [
    'BasePaperSource',
    'Paper',
    'ArxivSource',
    'SpringerSource',
    'SemanticScholarSource'
]
