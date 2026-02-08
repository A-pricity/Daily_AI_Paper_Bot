"""数据源模块 - 负责从不同数据源获取论文"""

from sources.base import BasePaperSource, Paper
from sources.arxiv_source import ArxivSource
from sources.springer_source import SpringerSource
from sources.semantic_scholar_source import SemanticScholarSource

__all__ = [
    'BasePaperSource',
    'Paper',
    'ArxivSource',
    'SpringerSource',
    'SemanticScholarSource'
]
