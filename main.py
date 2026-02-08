"""
AI 前沿论文日报生成器 - 主程序入口

模块化架构：
- config: 配置管理
- sources: 多数据源论文获取
- llm: LLM 摘要生成
- formatters: 消息格式化
- notification: 通知推送
- utils: 辅助工具函数
"""

import datetime
from typing import List, Dict

from config import Settings, SOURCES_CONFIG
from sources import ArxivSource, SpringerSource, SemanticScholarSource
from llm import LLMClient
from notification import WeChatNotifier
from formatters import MarkdownFormatter
from utils import deduplicate_papers


class PaperBot:
    """论文日报生成机器人 - 流程编排"""

    def __init__(self):
        """初始化机器人"""
        print("=" * 50)
        print("AI 前沿论文日报生成器")
        print("=" * 50)

        # 初始化组件
        self.llm_client = LLMClient()
        self.notifier = WeChatNotifier()
        self.report_formatter = MarkdownFormatter()

        # 初始化数据源
        self.sources = self._init_sources()
        print(f"\n✓ 已初始化 {len(self.sources)} 个数据源")

    def _init_sources(self) -> List:
        """初始化数据源"""
        sources = []
        if SOURCES_CONFIG['arxiv']['enabled']:
            sources.append(ArxivSource(SOURCES_CONFIG['arxiv']))
        if SOURCES_CONFIG['springer']['enabled']:
            sources.append(SpringerSource(SOURCES_CONFIG['springer']))
        if SOURCES_CONFIG['semantic_scholar']['enabled']:
            sources.append(SemanticScholarSource(SOURCES_CONFIG['semantic_scholar']))
        return sources

    def fetch_all_papers(self) -> List[Dict]:
        """
        从所有启用的数据源获取论文

        Returns:
            论文列表
        """
        print("\n📚 开始获取论文数据...")
        print("=" * 50)

        all_papers = []

        # 从各数据源获取论文
        for source in self.sources:
            try:
                papers = source.fetch_papers()
                # 转换为字典格式
                paper_dicts = [p.to_dict() for p in papers]
                all_papers.extend(paper_dicts)
            except Exception as e:
                print(f"⚠ 数据源 {source.__class__.__name__} 出错: {e}")

        # 去重并限制数量
        print(f"\n🔄 原始论文数: {len(all_papers)}")
        unique_papers = deduplicate_papers(all_papers)
        print(f"✓ 去重后: {len(unique_papers)}")

        papers = unique_papers[:Settings.MAX_PAPERS]
        print(f"✓ 最终选取: {len(papers)} 篇\n")

        return papers

    def generate_summaries(self, papers: List[Dict]) -> List[Dict]:
        """
        为每篇论文生成 LLM 摘要

        Args:
            papers: 论文列表

        Returns:
            包含摘要的论文列表
        """
        for i, paper in enumerate(papers, 1):
            print(f"\n[进度] 处理第 {i}/{len(papers)} 篇论文...")
            paper['summary'] = self.llm_client.generate_summary(paper)
        return papers

    def save_report(self, papers: List[Dict], report: str) -> None:
        """
        保存日报到文件

        Args:
            papers: 论文列表
            report: 报告内容
        """
        with open(Settings.REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 报告已保存到 {Settings.REPORT_FILE}")

    def run(self):
        """
        运行完整的日报生成流程
        """
        try:
            # 1. 获取论文
            papers = self.fetch_all_papers()

            if not papers:
                print("\n⚠ 未能获取到任何论文，请稍后重试")
                return

            # 2. 生成 LLM 摘要
            papers = self.generate_summaries(papers)

            # 3. 生成报告（Markdown 格式）
            metadata = {
                'date': datetime.date.today(),
                'topic': '大语言模型、智能体、增强型LLM推理和推理优化'
            }
            report = self.report_formatter.format_report(papers, metadata)

            # 4. 输出结果
            print("\n" + "=" * 20 + " 生成结果 " + "=" * 20 + "\n")
            print(report)

            # 5. 保存报告
            self.save_report(papers, report)

            # 6. 推送到微信（自动格式化）
            self.notifier.send_report(papers, metadata)

        finally:
            # 清理资源
            self.llm_client.close()


def main():
    """主函数"""
    bot = PaperBot()
    bot.run()


if __name__ == "__main__":
    main()
