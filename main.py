"""
AI 前沿论文日报生成器 - 主程序入口

模块化架构：
- config: 配置管理
- sources: 多数据源论文获取
- llm: LLM 摘要生成
- notification: 微信推送
- utils: 辅助工具函数
"""

import datetime
import re
from typing import List, Dict

from config import Settings, SOURCES_CONFIG
from sources import ArxivSource, SpringerSource, SemanticScholarSource
from llm import LLMClient
from notification import WeChatNotifier
from utils import deduplicate_papers


class PaperBot:
    """论文日报生成机器人"""

    def __init__(self):
        """初始化机器人"""
        print("=" * 50)
        print("AI 前沿论文日报生成器")
        print("=" * 50)

        # 初始化组件
        self.llm_client = LLMClient()
        self.notifier = WeChatNotifier()

        # 初始化数据源
        self.sources = []
        if SOURCES_CONFIG['arxiv']['enabled']:
            self.sources.append(ArxivSource(SOURCES_CONFIG['arxiv']))
        if SOURCES_CONFIG['springer']['enabled']:
            self.sources.append(SpringerSource(SOURCES_CONFIG['springer']))
        if SOURCES_CONFIG['semantic_scholar']['enabled']:
            self.sources.append(SemanticScholarSource(SOURCES_CONFIG['semantic_scholar']))

        print(f"\n✓ 已初始化 {len(self.sources)} 个数据源")

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

        # 去重
        print(f"\n🔄 原始论文数: {len(all_papers)}")
        unique_papers = deduplicate_papers(all_papers)
        print(f"✓ 去重后: {len(unique_papers)}")

        # 限制数量
        papers = unique_papers[:Settings.MAX_PAPERS]
        print(f"✓ 最终选取: {len(papers)} 篇\n")

        return papers

    def generate_daily_report(self, papers: List[Dict]) -> str:
        """
        生成日报内容

        Args:
            papers: 论文列表

        Returns:
            日报内容
        """
        # 统计各数据源
        source_stats = {}
        for paper in papers:
            source = paper.get('source', 'Unknown')
            source_stats[source] = source_stats.get(source, 0) + 1

        # 构建报告头部
        report = f"# 📅 AI 前沿论文日报 ({datetime.date.today()})\n\n"
        report += f"**主题**: 大语言模型、智能体、增强型LLM推理和推理优化\n\n"
        report += f"**数据源**: {', '.join(source_stats.keys())}\n\n"
        report += f"今日为您精选 {len(papers)} 篇最新论文\n\n"

        # 生成每篇论文的摘要
        for i, paper in enumerate(papers, 1):
            print(f"\n[进度] 处理第 {i}/{len(papers)} 篇论文...")

            summary = self.llm_client.generate_summary(paper)

            report += f"{summary}\n"
            report += f"🔗 **原文链接**: {paper['url']}\n"
            if 'source' in paper:
                report += f"📚 **来源**: {paper['source']}\n"
            report += "---\n\n"

        return report

    def save_report(self, report: str) -> None:
        """
        保存日报到文件

        Args:
            report: 日报内容
        """
        with open(Settings.REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 报告已保存到 {Settings.REPORT_FILE}")

    def send_wechat_notification(self, report: str) -> bool:
        """
        发送微信通知

        Args:
            report: 日报内容

        Returns:
            是否发送成功
        """
        if not Settings.WECHAT_WEBHOOK:
            print("\n⚠ 未配置企业微信 Webhook，跳过微信推送")
            return False

        print("\n正在推送到微信...")

        # 生成适合微信的消息格式（简化版）
        wechat_message = f"## 📅 AI 前沿论文日报 ({datetime.date.today()})\n\n"
        wechat_message += f"**主题**: 大语言模型、智能体、增强型LLM推理和推理优化\n\n"

        # 从报告中提取论文标题
        title_pattern = r'## 📄 论文标题：(.*?)\n'
        titles = re.findall(title_pattern, report)

        for i, title in enumerate(titles, 1):
            wechat_message += f"**{i}. {title}**\n\n"

        # 添加 GitHub 链接
        wechat_message += f"\n📮 [点击查看完整报告](https://github.com/A-pricity/Daily_AI_Paper_Bot/blob/main/{Settings.REPORT_FILE})"

        return self.notifier.send(wechat_message)

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

            # 2. 生成日报
            report = self.generate_daily_report(papers)

            # 3. 输出结果
            print("\n" + "=" * 20 + " 生成结果 " + "=" * 20 + "\n")
            print(report)

            # 4. 保存报告
            self.save_report(report)

            # 5. 推送到微信
            self.send_wechat_notification(report)

        finally:
            # 清理资源
            self.llm_client.close()


def main():
    """主函数"""
    bot = PaperBot()
    bot.run()


if __name__ == "__main__":
    main()
