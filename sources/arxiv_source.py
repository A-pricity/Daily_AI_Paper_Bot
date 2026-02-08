"""ArXiv 数据源实现"""

import time
import arxiv
from typing import List

from sources.base import BasePaperSource, Paper
from config.settings import Settings


class ArxivSource(BasePaperSource):
    """ArXiv 数据源"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.search_topics = config.get('search_topics', [])
        self.max_results = config.get('max_results', 1)
        self.page_size = config.get('page_size', 10)
        self.delay_seconds = config.get('delay_seconds', 10)
        self.delay_between_topics = config.get('delay_between_topics', 15)

    def fetch_papers(self, max_results: int = 5) -> List[Paper]:
        """
        从 ArXiv 获取论文

        Args:
            max_results: 每个主题最多获取的论文数

        Returns:
            论文列表
        """
        if not self.enabled:
            return []

        papers = []
        max_retries = 3

        for i, topic in enumerate(self.search_topics):
            self._log(f"检索主题: {topic}")

            if i > 0:
                self._log(f"等待 {self.delay_between_topics} 秒后继续下一个主题")
                time.sleep(self.delay_between_topics)

            for attempt in range(max_retries):
                try:
                    client_arxiv = arxiv.Client(
                        page_size=self.page_size,
                        delay_seconds=self.delay_seconds
                    )
                    search = arxiv.Search(
                        query=topic,
                        max_results=self.max_results,
                        sort_by=arxiv.SortCriterion.SubmittedDate
                    )

                    topic_papers = []
                    for result in client_arxiv.results(search):
                        paper = Paper(
                            title=result.title,
                            authors=[author.name for author in result.authors],
                            abstract=result.summary,
                            url=result.entry_id,
                            published=str(result.published),
                            source="ArXiv"
                        )
                        topic_papers.append(paper)

                    papers.extend(topic_papers)
                    self._log(f"获取到 {len(topic_papers)} 篇论文 (主题: {topic})")
                    break

                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 10
                        self._log(f"请求失败，{wait_time} 秒后重试", "WARN")
                        time.sleep(wait_time)
                    else:
                        self._log(f"无法获取关于 '{topic}' 的论文", "ERROR")

        return papers
