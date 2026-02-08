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

        # 企业微信机器人 Markdown 消息长度限制约 4096 字符
        max_length = 4000

        # 解析报告内容并重新组织为紧凑格式
        wechat_message = self._format_wechat_message(report)

        # 如果消息超过长度限制，进行截断
        if len(wechat_message) > max_length:
            print(f"⚠ 消息过长 ({len(wechat_message)} 字符)，将截断到 {max_length} 字符")
            wechat_message = wechat_message[:max_length] + "\n\n*内容已截断*"

        return self.notifier.send(wechat_message)

    def _format_wechat_message(self, report: str) -> str:
        """
        将完整报告格式化为适合企业微信的紧凑消息

        Args:
            report: 原始报告内容

        Returns:
            格式化后的消息
        """
        lines = report.split('\n')
        result = []
        current_paper = None
        i = 0

        # 解析头部信息
        while i < len(lines) and not lines[i].strip().startswith('##'):
            line = lines[i].strip()
            if line:
                result.append(line)
            i += 1

        # 添加分隔线
        result.append('---')

        # 解析每篇论文
        paper_count = 0
        while i < len(lines):
            line = lines[i].strip()

            # 检测新论文开始
            if line.startswith('## 📄 论文标题：'):
                # 保存上一篇论文
                if current_paper:
                    result.append(self._format_paper_compact(current_paper))
                    result.append('---')

                # 开始新论文
                current_paper = {
                    'title_zh': line.replace('## 📄 论文标题：', '').strip(),
                    'title_en': '',
                    'author': '',
                    'institution': '',
                    'sections': {}
                }
                paper_count += 1

            elif line.startswith('**原标题**：'):
                current_paper['title_en'] = line.replace('**原标题**：', '').strip()
            elif line.startswith('**第一作者**：'):
                author_info = line.replace('**第一作者**：', '').strip()
                parts = author_info.split('|')
                current_paper['author'] = parts[0].strip()
                current_paper['institution'] = parts[1].strip() if len(parts) > 1 else '未知'
            elif line.startswith('### 🎯 核心摘要'):
                current_paper['sections']['summary'] = []
            elif line.startswith('### 💡 核心创新点与贡献'):
                current_paper['sections']['innovations'] = []
            elif line.startswith('### 🧐 简评与启示'):
                current_paper['sections']['comment'] = []
            elif line.startswith('🔗 **原文链接**：'):
                current_paper['url'] = line.replace('🔗 **原文链接**：', '').strip()
            elif line.startswith('📚 **来源**：'):
                current_paper['source'] = line.replace('📚 **来源**：', '').strip()
            elif line.startswith('*') and current_paper and 'innovations' in current_paper['sections']:
                # 创新点列表
                innovation = line.replace('*', '').strip()
                if innovation:
                    current_paper['sections']['innovations'].append(innovation)
            elif line and current_paper and not line.startswith('#') and not line.startswith('**'):
                # 普通内容
                if 'summary' in current_paper['sections']:
                    current_paper['sections']['summary'].append(line)
                elif 'comment' in current_paper['sections']:
                    current_paper['sections']['comment'].append(line)

            i += 1

        # 添加最后一篇论文
        if current_paper:
            result.append(self._format_paper_compact(current_paper))

        # 添加底部信息（引用块样式）
        result.append('')
        result.append('---')
        result.append(f"> 📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} | 📊 共**{paper_count}**篇")

        return '\n'.join(result)

    def _format_paper_compact(self, paper: dict) -> str:
        """
        格式化单篇论文为紧凑布局

        Args:
            paper: 论文字典

        Returns:
            格式化后的论文文本
        """
        parts = []

        # 标题行（加粗，重点突出）
        title_line = f"📌 **{paper['title_zh']}**"
        parts.append(title_line)

        # 英文标题（次要信息，普通文本）
        if paper['title_en']:
            parts.append(f"<font color=\"info\">{paper['title_en']}</font>")

        # 作者和信息行（紧凑排列）
        info_line = f"> 👤 {paper['author']}"
        if paper.get('source'):
            info_line += f" | 📚 {paper['source']}"
        parts.append(info_line)

        # 核心摘要（单行紧凑）
        if 'summary' in paper['sections'] and paper['sections']['summary']:
            summary_text = ' '.join(paper['sections']['summary'])
            # 限制摘要长度，避免过长
            if len(summary_text) > 150:
                summary_text = summary_text[:147] + '...'
            parts.append(f"💡 {summary_text}")

        # 创新点（使用简洁符号列表）
        if 'innovations' in paper['sections'] and paper['sections']['innovations']:
            parts.append("> **核心创新**")
            for innovation in paper['sections']['innovations'][:3]:  # 最多显示3个
                # 简化创新点文本
                if len(innovation) > 80:
                    innovation = innovation[:77] + '...'
                parts.append(f"> • {innovation}")

        # 简评（单行高亮）
        if 'comment' in paper['sections'] and paper['sections']['comment']:
            comment_text = ' '.join(paper['sections']['comment'])
            parts.append(f"📝 **简评**：{comment_text}")

        # 原文链接（可点击，使用引用块样式突出）
        if 'url' in paper and paper['url']:
            parts.append(f"> 🔗 [📖 阅读原文]({paper['url']})")

        return '\n'.join(parts)

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
