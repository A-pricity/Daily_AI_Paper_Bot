"""辅助工具模块

提供论文处理和文本处理的通用函数
"""

from typing import List, Dict
import re


def extract_clean_summary(content: str) -> str:
    """
    从 API 响应中提取干净的格式化报告

    Args:
        content: 原始 API 响应内容

    Returns:
        清理后的格式化报告
    """
    lines = content.split('\n')

    # 寻找报告开始标记（## 📄）
    start_idx = -1
    for i, line in enumerate(lines):
        if '## 📄' in line or '论文标题' in line:
            start_idx = i
            break

    if start_idx == -1:
        # 如果没找到，尝试寻找第一个 ## 标题
        for i, line in enumerate(lines):
            if line.strip().startswith('##'):
                start_idx = i
                break

    if start_idx == -1:
        # 还没找到，就返回整个内容
        return content

    # 从开始位置提取内容
    result_lines = []
    skip_reasoning_section = False

    for i in range(start_idx, len(lines)):
        line = lines[i]
        stripped = line.strip()

        # 检测思考过程的章节标题
        if (stripped.startswith('### 1.') or
            stripped.startswith('### 2.') or
            stripped.startswith('### 3.') or
            stripped.startswith('### 4.') or
            stripped.startswith('### 5.') or
            stripped.startswith('### 6.') or
            stripped in ['### 分析', '### 步骤', '### 思路', '### 输出',
                         '### 分析请求', '### 思考过程', '### 最终输出',
                         '### **分析**', '### **步骤**', '### **思路**',
                         '### 最终输出生成']):
            skip_reasoning_section = True
            continue

        # 如果在思考过程中，跳过带编号的列表项
        if skip_reasoning_section:
            if (stripped.startswith('1. **') or
                stripped.startswith('2. **') or
                stripped.startswith('3. **') or
                stripped.startswith('4. **') or
                stripped.startswith('5. **') or
                stripped.startswith('6. **')):
                continue

            # 如果遇到报告的主要章节，说明思考过程结束
            if stripped.startswith('## ') or stripped.startswith('### 🎯') or stripped.startswith('### 💡') or stripped.startswith('### 🧐'):
                skip_reasoning_section = False

        # 如果不在跳过模式，保留这一行
        if not skip_reasoning_section:
            result_lines.append(line)

    return '\n'.join(result_lines).strip()


def validate_summary(content: str) -> List[str]:
    """
    验证报告是否包含所有必需的章节

    Args:
        content: 报告内容

    Returns:
        缺少的章节列表
    """
    required_sections = [
        '### 🎯 核心摘要',
        '### 💡 核心创新点与贡献',
        '### 🧐 简评与启示'
    ]

    missing = []
    for section in required_sections:
        if section not in content:
            missing.append(section)

    return missing


def deduplicate_papers(papers: List[Dict], key: str = 'url') -> List[Dict]:
    """
    去重论文列表

    Args:
        papers: 论文列表
        key: 用于去重的键名，默认为 'url'

    Returns:
        去重后的论文列表
    """
    seen = set()
    unique = []

    for paper in papers:
        if isinstance(paper, dict):
            value = paper.get(key)
        else:
            value = getattr(paper, key, None)

        if value and value not in seen:
            seen.add(value)
            unique.append(paper)

    return unique
