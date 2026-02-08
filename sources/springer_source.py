"""Springer 数据源实现 (RSS feeds)"""

import feedparser
from typing import List

from .base import BasePaperSource, Paper


class SpringerSource(BasePaperSource):
    """Springer 数据源 - 使用 RSS feeds"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.urls = config.get('urls', [])
        self.max_results = config.get('max_results', 2)

    def fetch_papers(self, max_results: int = 5) -> List[Paper]:
        """
        从 Springer RSS feeds 获取论文

        Args:
            max_results: 每个 feed 最多获取的论文数

        Returns:
            论文列表
        """
        if not self.enabled:
            return []

        papers = []

        for url in self.urls:
            self._log(f"从 RSS 获取论文: {url}")

            try:
                feed = feedparser.parse(url)

                for entry in feed.entries[:self.max_results]:
                    # 提取作者信息
                    authors = []
                    if hasattr(entry, 'authors') and entry.authors:
                        authors = [author.get('name', '') for author in entry.authors]
                    elif hasattr(entry, 'author') and entry.author:
                        authors = [entry.author]

                    paper = Paper(
                        title=entry.get('title', '').strip(),
                        authors=authors,
                        abstract=entry.get('summary', '') or entry.get('description', ''),
                        url=entry.get('link', ''),
                        published=entry.get('published', ''),
                        source="Springer"
                    )
                    papers.append(paper)

                self._log(f"获取到 {len(feed.entries[:self.max_results])} 篇论文")

            except Exception as e:
                self._log(f"获取失败: {e}", "WARN")

        return papers
