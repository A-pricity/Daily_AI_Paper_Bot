"""Markdown 格式化器 - 用于生成文件和完整报告"""

import datetime
from typing import Dict, List

from .base import BaseFormatter


class MarkdownFormatter(BaseFormatter):
    """Markdown 格式化器 - 生成完整的 Markdown 报告"""

    def format_report(self, papers: List[Dict], metadata: Dict = None) -> str:
        """
        生成 Markdown 格式的完整报告

        Args:
            papers: 论文列表
            metadata: 元数据（日期、主题等）

        Returns:
            Markdown 格式的报告
        """
        metadata = metadata or {}
        date = metadata.get('date', datetime.date.today())

        # 统计数据源
        source_stats = {}
        for paper in papers:
            source = paper.get('source', 'Unknown')
            source_stats[source] = source_stats.get(source, 0) + 1

        # 构建报告头部
        report = f"# 📅 AI 前沿论文日报 ({date})\n\n"
        report += f"**主题**: {metadata.get('topic', 'AI 前沿研究')}\n\n"
        report += f"**数据源**: {', '.join(source_stats.keys())}\n\n"
        report += f"今日为您精选 {len(papers)} 篇最新论文\n\n"

        # 生成每篇论文
        for paper in papers:
            report += self.format_paper(paper)
            report += "---\n\n"

        return report

    def format_paper(self, paper: Dict) -> str:
        """
        格式化单篇论文

        Args:
            paper: 论文字典

        Returns:
            Markdown 格式的论文
        """
        paper = paper.copy()

        # 如果论文包含 LLM 生成的摘要，直接使用
        if 'summary' in paper:
            return paper['summary']

        # 否则，从论文信息生成基础格式
        result = f"## 📄 论文标题：{paper.get('title', '')}\n"
        result += f"**第一作者**：{paper['authors'][0] if paper.get('authors') else 'Unknown'}\n"
        result += f"\n### 🎯 核心摘要\n{paper.get('abstract', '无摘要')}\n"

        if 'url' in paper:
            result += f"\n🔗 **原文链接**: {paper['url']}\n"
        if 'source' in paper:
            result += f"📚 **来源**: {paper['source']}\n"

        return result + "\n"
