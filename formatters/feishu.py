"""飞书消息格式化器 - 错峰发送、请求体压缩、关键信息前置"""

import datetime
from typing import Dict, List

from .base import BaseFormatter


class FeishuFormatter(BaseFormatter):
    """飞书消息格式化器 - 针对 20KB 限制优化，关键信息前置"""

    # 飞书 Markdown 样式
    EMOJI = {
        'title': '📌',
        'author': '👤',
        'source': '📚',
        'summary': '💡',
        'innovation': '🎯',
        'comment': '📝',
        'link': '🔗'
    }

    # 长度限制（严格控制 20KB 以内）
    SUMMARY_MAX_LENGTH = 120      # 比微信更短
    INNOVATION_MAX_LENGTH = 60   # 比微信更短
    MAX_INNOVATIONS_DISPLAY = 2    # 只显示 2 个创新点
    MAX_PAPERS_DISPLAY = 3         # 最多显示 3 篇论文

    def __init__(self, max_length: int = 20 * 1024):
        """
        初始化格式化器

        Args:
            max_length: 最大消息长度（飞书限制 20KB）
        """
        self.max_length = max_length
        self._paper_count = 0

    def format_report(self, papers: List[Dict], metadata: Dict = None) -> str:
        """
        生成飞书紧凑格式的报告

        Args:
            papers: 论文列表
            metadata: 元数据（日期、主题等）

        Returns:
            飞书格式的消息（严格控制 20KB 以内）
        """
        metadata = metadata or {}
        date = metadata.get('date', datetime.date.today())
        topic = metadata.get('topic', '大语言模型、智能体、增强型LLM推理和推理优化')

        # 限制论文数量
        papers_to_display = papers[:self.MAX_PAPERS_DISPLAY]
        self._paper_count = len(papers_to_display)

        # 构建头部（关键信息前置）
        result = [self._build_header(date, topic, len(papers_to_display), len(papers))]

        # 格式化每篇论文（关键信息前置）
        for paper in papers_to_display:
            result.append(self.format_paper(paper))
            result.append('---')

        # 添加底部信息（简化）
        result.append(f"> 📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} | 📊 共**{len(papers)}**篇")

        # 拼接并严格检查长度
        message = '\n'.join(result)
        message_size = len(message.encode('utf-8'))

        if message_size > self.max_length:
            print(f"⚠ 消息过大 ({message_size} bytes)，进行压缩")
            message = self._compress_message(message, result)

        return message

    def format_paper(self, paper: Dict) -> str:
        """
        格式化单篇论文（关键信息前置）

        Args:
            paper: 论文字典

        Returns:
            紧凑格式的论文
        """
        # 解析 LLM 生成的摘要
        parsed = self._parse_llm_summary(paper.get('summary', ''))

        # 提取关键信息
        title_zh = parsed.get('title_zh', paper.get('title', ''))
        title_en = parsed.get('title_en', '')
        author = parsed.get('author', paper['authors'][0] if paper.get('authors') else 'Unknown')
        source = paper.get('source', parsed.get('source', ''))
        url = paper.get('url', '')

        # 关键信息前置布局
        parts = [
            f"## {self.EMOJI['title']} {title_zh}",  # 标题最前
            self._format_critical_info(author, source, url),  # 关键信息次之
            self._format_summary(parsed.get('summary', [])),  # 摘要
            self._format_innovations(parsed.get('innovations', [])),  # 创新点
            self._format_comment(parsed.get('comment', []))  # 简评
        ]

        return '\n'.join(filter(None, parts))

    def _build_header(self, date, topic, displayed_count, total_count) -> str:
        """构建消息头部（关键信息前置）"""
        header = f"# 📅 **AI 论文日报** | {date}\n\n"
        header += f"**主题**: {topic}\n\n"

        if displayed_count < total_count:
            header += f"精选 **{displayed_count}** 篇（共 {total_count} 篇）\n\n"
        else:
            header += f"精选 **{displayed_count}** 篇\n\n"

        return header

    def _format_critical_info(self, author: str, source: str, url: str) -> str:
        """格式化关键信息（作者、来源、链接）- 前置显示"""
        lines = [f"**{self.EMOJI['author']}**: {author}"]

        if source:
            lines.append(f"**{self.EMOJI['source']}**: {source}")

        if url:
            lines.append(f"**{self.EMOJI['link']}**: [{url}]({url})")

        return '\n'.join(lines)

    def _format_summary(self, summary_lines: List[str]) -> str:
        """格式化摘要（超短版本）"""
        if not summary_lines:
            return ""

        summary_text = ' '.join(summary_lines)
        # 严格限制长度
        if len(summary_text) > self.SUMMARY_MAX_LENGTH:
            summary_text = summary_text[:self.SUMMARY_MAX_LENGTH - 3] + '...'

        return f"**{self.EMOJI['summary']} 核心摘要**: {summary_text}"

    def _format_innovations(self, innovations: List[str]) -> str:
        """格式化创新点（只显示 2 个）"""
        if not innovations:
            return ""

        result = [f"**{self.EMOJI['innovation']} 核心创新**"]
        for innovation in innovations[:self.MAX_INNOVATIONS_DISPLAY]:
            if len(innovation) > self.INNOVATION_MAX_LENGTH:
                innovation = innovation[:self.INNOVATION_MAX_LENGTH - 3] + '...'
            result.append(f"- {innovation}")

        return '\n'.join(result)

    def _format_comment(self, comment_lines: List[str]) -> str:
        """格式化简评（单行高亮）"""
        if not comment_lines:
            return ""

        comment_text = ' '.join(comment_lines)
        return f"**{self.EMOJI['comment']} 简评**: {comment_text}"

    def _parse_llm_summary(self, summary: str) -> Dict:
        """解析 LLM 生成的摘要，提取结构化数据"""
        lines = summary.split('\n')
        result = {
            'title_zh': '',
            'title_en': '',
            'author': '',
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

            if stripped.startswith('## 📄 论文标题：'):
                result['title_zh'] = stripped.replace('## 📄 论文标题：', '').strip()
            elif stripped.startswith('**原标题**：'):
                result['title_en'] = stripped.replace('**原标题**：', '').strip()
            elif stripped.startswith('**第一作者**：'):
                author_info = stripped.replace('**第一作者**：', '').strip()
                parts = author_info.split('|')
                result['author'] = parts[0].strip()
            elif stripped.startswith('### 🎯 核心摘要'):
                current_section = 'summary'
            elif stripped.startswith('### 💡 核心创新点与贡献'):
                current_section = 'innovations'
            elif stripped.startswith('### 🧐 简评与启示'):
                current_section = 'comment'
            elif stripped.startswith('📚 **来源**：'):
                result['source'] = stripped.replace('📚 **来源**：', '').strip()
            elif stripped.startswith('🔗 **原文链接**：'):
                result['url'] = stripped.replace('🔗 **原文链接**：', '').strip()
            elif stripped.startswith('*') and current_section == 'innovations':
                innovation = stripped.replace('*', '').strip()
                if innovation:
                    result['sections']['innovations'].append(innovation)
            elif current_section and not stripped.startswith('#') and not stripped.startswith('**'):
                if current_section in result['sections']:
                    result['sections'][current_section].append(stripped)

        return result

    def _compress_message(self, message: str, lines: List[str]) -> str:
        """压缩消息以符合 20KB 限制"""
        # 移除多余的空行
        compressed_lines = [line for line in lines if line.strip()]
        compressed = '\n'.join(compressed_lines)

        # 如果还是太大，移除分隔符
        if len(compressed.encode('utf-8')) > self.max_length:
            compressed_lines = [line for line in compressed_lines if line != '---']
            compressed = '\n'.join(compressed_lines)

        return compressed
