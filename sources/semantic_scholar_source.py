"""Semantic Scholar 数据源实现"""

import httpx
import datetime
from typing import List

from sources.base import BasePaperSource, Paper
from config.settings import Settings


class SemanticScholarSource(BasePaperSource):
    """Semantic Scholar 数据源"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.search_topics = config.get('search_topics', [])
        self.max_results = config.get('max_results', 1)
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        self.timeout = 30.0

    def fetch_papers(self, max_results: int = 5) -> List[Paper]:
        """
        从 Semantic Scholar API 获取论文

        Args:
            max_results: 每个主题最多获取的论文数

        Returns:
            论文列表
        """
        if not self.enabled:
            return []

        if not self.api_key:
            self._log("未配置 API Key，跳过", "WARN")
            return []

        papers = []

        for topic in self.search_topics:
            self._log(f"检索: {topic}")

            try:
                params = {
                    'query': topic,
                    'limit': self.max_results,
                    'fields': 'title,authors,abstract,url,publicationDate',
                    'year': datetime.datetime.now().year  # 只获取今年的论文
                }

                headers = {'x-api-key': self.api_key}
                response = httpx.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    for paper_data in data.get('data', []):
                        authors = [
                            author.get('name', '')
                            for author in paper_data.get('authors', [])
                        ]

                        paper = Paper(
                            title=paper_data.get('title', ''),
                            authors=authors,
                            abstract=paper_data.get('abstract', '') or '无摘要',
                            url=paper_data.get('url', ''),
                            published=paper_data.get('publicationDate', ''),
                            source="Semantic Scholar"
                        )
                        papers.append(paper)

                    self._log(f"获取到 {len(data.get('data', []))} 篇论文")
                else:
                    self._log(f"API 错误: HTTP {response.status_code}", "ERROR")

            except Exception as e:
                self._log(f"请求失败: {e}", "ERROR")

        return papers
