"""企业微信消息格式化器 - 紧凑布局，支持移动端"""

import datetime
import re
from typing import Dict, List

from .base import BaseFormatter


class WeChatFormatter(BaseFormatter):
    """企业微信消息格式化器 - 紧凑布局，适合移动端阅读"""

    # Emoji 配置
    EMOJI = {
        'title': '📌',
        'author': '👤',
        'source': '📚',
        'summary': '💡',
        'innovation': '🎯',
        'comment': '📝',
        'link': '🔗'
    }

    # 长度限制
    SUMMARY_MAX_LENGTH = 150
    INNOVATION_MAX_LENGTH = 80
    MAX_INNOVATIONS_DISPLAY = 3

    def __init__(self, max_length: int = 4000):
        """
        初始化格式化器

        Args:
            max_length: 最大消息长度（企业微信限制约 4096）
        """
        self.max_length = max_length
        self._paper_count = 0

    def format_report(self, papers: List[Dict], metadata: Dict = None) -> str:
        """
        生成企业微信紧凑格式的报告

        Args:
            papers: 论文列表
            metadata: 元数据（日期、主题等）

        Returns:
            企业微信格式的消息
        """
        metadata = metadata or {}
        date = metadata.get('date', datetime.date.today())
        topic = metadata.get('topic', '大语言模型、智能体、增强型LLM推理和推理优化')

        # 构建头部
        result = [self._build_header(date, topic, len(papers)), '---']

        # 格式化每篇论文
        for paper in papers:
            result.append(self.format_paper(paper))
            result.append('---')

        # 添加底部信息
        result.append('')
        result.append(self._build_footer())

        # 拼接并检查长度
        message = '\n'.join(result)
        if len(message) > self.max_length:
            message = self._truncate_message(message)

        return message

    def format_paper(self, paper: Dict) -> str:
        """
        格式化单篇论文为紧凑布局

        Args:
            paper: 论文字典

        Returns:
            紧凑格式的论文
        """
        # 解析 LLM 生成的摘要（如果存在）
        parsed = self._parse_llm_summary(paper.get('summary', ''))

        # 使用解析后的数据，或使用原始论文信息
        title_zh = parsed.get('title_zh', paper.get('title', ''))
        title_en = parsed.get('title_en', '')
        author = parsed.get('author', paper['authors'][0] if paper.get('authors') else 'Unknown')
        source = paper.get('source', parsed.get('source', ''))

        # 构建格式化部分
        parts = [
            self._format_title(title_zh),
            self._format_subtitle(title_en),
            self._format_info(author, source),
            self._format_summary(parsed.get('summary', [])),
            self._format_innovations(parsed.get('innovations', [])),
            self._format_comment(parsed.get('comment', [])),
            self._format_link(paper.get('url', ''))
        ]

        # 过滤空部分并拼接
        return '\n'.join(filter(None, parts))

    def _build_header(self, date, topic, count) -> str:
        """构建消息头部"""
        self._paper_count = count
        return f"# 📅 AI 前沿论文日报 ({date})\n\n**主题**: {topic}\n\n今日为您精选 {count} 篇最新论文"

    def _build_footer(self) -> str:
        """构建消息底部"""
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        return f"> 📅 {now} | 📊 共**{self._paper_count}**篇"

    def _parse_llm_summary(self, summary: str) -> Dict:
        """
        解析 LLM 生成的摘要，提取结构化数据

        Args:
            summary: LLM 生成的摘要文本

        Returns:
            结构化的论文数据
        """
        lines = summary.split('\n')
        result = {
            'title_zh': '',
            'title_en': '',
            'author': '',
            'institution': '',
            'source': '',
            'sections': {
                'summary': [],
                'innovations': [],
                'comment': []
            }
        }
        current_section = None

        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            # 解析标题
            if stripped.startswith('## 📄 论文标题：'):
                result['title_zh'] = stripped.replace('## 📄 论文标题：', '').strip()
            elif stripped.startswith('**原标题**：'):
                result['title_en'] = stripped.replace('**原标题**：', '').strip()
            elif stripped.startswith('**第一作者**：'):
                author_info = stripped.replace('**第一作者**：', '').strip()
                parts = author_info.split('|')
                result['author'] = parts[0].strip()
                result['institution'] = parts[1].strip() if len(parts) > 1 else '未知'
            elif stripped.startswith('### 🎯 核心摘要'):
                current_section = 'summary'
            elif stripped.startswith('### 💡 核心创新点与贡献'):
                current_section = 'innovations'
            elif stripped.startswith('### 🧐 简评与启示'):
                current_section = 'comment'
            elif stripped.startswith('🔗 **原文链接**：'):
                result['url'] = stripped.replace('🔗 **原文链接**：', '').strip()
            elif stripped.startswith('📚 **来源**：'):
                result['source'] = stripped.replace('📚 **来源**：', '').strip()
            elif stripped.startswith('*') and current_section == 'innovations':
                innovation = stripped.replace('*', '').strip()
                if innovation:
                    result['sections']['innovations'].append(innovation)
            elif current_section and not stripped.startswith('#') and not stripped.startswith('**'):
                if current_section in result['sections']:
                    result['sections'][current_section].append(stripped)

        return result

    def _format_title(self, title_zh: str) -> str:
        """格式化标题"""
        return f"{self.EMOJI['title']} **{title_zh}**"

    def _format_subtitle(self, title_en: str) -> str:
        """格式化副标题（英文标题）"""
        if not title_en:
            return ""
        return f"<font color=\"info\">{title_en}</font>"

    def _format_info(self, author: str, source: str) -> str:
        """格式化作者和来源信息"""
        info_line = f"> {self.EMOJI['author']} {author}"
        if source:
            info_line += f" | {self.EMOJI['source']} {source}"
        return info_line

    def _format_summary(self, summary_lines: List[str]) -> str:
        """格式化摘要（单行紧凑）"""
        if not summary_lines:
            return ""
        summary_text = ' '.join(summary_lines)
        if len(summary_text) > self.SUMMARY_MAX_LENGTH:
            summary_text = summary_text[:self.SUMMARY_MAX_LENGTH - 3] + '...'
        return f"{self.EMOJI['summary']} {summary_text}"

    def _format_innovations(self, innovations: List[str]) -> str:
        """格式化创新点（符号列表）"""
        if not innovations:
            return ""

        result = [f"> {self.EMOJI['innovation']} <strong>核心创新</strong>"]
        for innovation in innovations[:self.MAX_INNOVATIONS_DISPLAY]:
            if len(innovation) > self.INNOVATION_MAX_LENGTH:
                innovation = innovation[:self.INNOVATION_MAX_LENGTH - 3] + '...'
            result.append(f"> • {innovation}")

        return '\n'.join(result)

    def _format_comment(self, comment_lines: List[str]) -> str:
        """格式化简评（单行高亮）"""
        if not comment_lines:
            return ""
        comment_text = ' '.join(comment_lines)
        return f"{self.EMOJI['comment']} <strong>简评</strong>：{comment_text}"

    def _format_link(self, url: str) -> str:
        """格式化原文链接"""
        if not url:
            return ""
        return f"> {self.EMOJI['link']} [📖 阅读原文]({url})"

    def _truncate_message(self, message: str) -> str:
        """截断过长的消息"""
        truncated = message[:self.max_length]
        truncated += "\n\n*内容已截断，完整报告请查看 daily_report.md*"
        return truncated
