# 模块化重构分析报告

## 一、当前代码结构问题分析

### 1.1 推送格式相关代码未模块化的原因

在 `main.py` 中，推送和报告格式相关的代码包括：

| 方法 | 代码行数 | 职责 |
|------|---------|------|
| `generate_daily_report()` | ~30 行 | 生成 Markdown 格式的完整报告 |
| `send_wechat_notification()` | ~20 行 | 发送微信通知的入口 |
| `_format_wechat_message()` | ~100 行 | 解析报告并转换为微信格式 |
| `_format_paper_compact()` | ~40 行 | 格式化单篇论文为紧凑布局 |

**总计约 190 行代码**（约占 `main.py` 总行数的 60%）

---

### 1.2 未模块化的具体原因

#### 原因 1：紧耦合的业务逻辑

`PaperBot` 类将**报告生成**和**通知发送**两个独立的业务职责绑定在一起：

```python
# 当前设计：PaperBot 既负责生成报告，又负责格式化发送
class PaperBot:
    def generate_daily_report(self): ...  # 报告生成
    def send_wechat_notification(self): ...  # 通知发送
    def _format_wechat_message(self): ...  # 格式化转换
    def _format_paper_compact(self): ...  # 细节格式化
```

**问题**：
- 违反了**单一职责原则（SRP）**
- `PaperBot` 类过于臃肿（约 273 行）
- 报告格式和通知逻辑耦合在一起，难以独立测试

---

#### 原因 2：格式化逻辑嵌入主类

微信消息格式化的逻辑是**纯文本处理**，与业务逻辑无关：

```python
def _format_wechat_message(self, report: str) -> str:
    # 100+ 行的文本解析和格式化逻辑
    lines = report.split('\n')
    result = []
    current_paper = None
    # ... 复杂的解析逻辑
    return '\n'.join(result)
```

**问题**：
- 格式化逻辑与 `PaperBot` 的业务职责无关
- 无法在其他场景复用（如邮件、Slack 等其他通知渠道）
- 难以单元测试（需要构造完整的报告字符串）

---

#### 原因 3：通知模块职责不清晰

`notification/wechat.py` 中的 `WeChatNotifier` 类只负责**发送**消息：

```python
class WeChatNotifier:
    def send(self, message: str) -> bool:
        # 只负责发送，不关心消息格式
        data = {"msgtype": "markdown", "markdown": {"content": message}}
        response = httpx.post(self.webhook_url, json=data)
        ...
```

**问题**：
- 格式化逻辑散落在 `main.py` 中
- `WeChatNotifier` 无法独立使用（需要先格式化）
- 添加新的通知渠道时需要重复编写格式化逻辑

---

### 1.3 现有架构的限制

当前模块化架构（参考 `ARCHITECTURE.md`）：

| 模块 | 职责 | 缺失的职责 |
|------|------|-----------|
| `config` | 配置管理 | ❌ 格式化配置 |
| `sources` | 数据源获取 | ✅ 职责清晰 |
| `llm` | LLM 调用 | ✅ 职责清晰 |
| `notification` | 消息发送 | ❌ 消息格式化 |
| `utils` | 通用工具 | ❌ 格式化工具 |
| `main` | 流程协调 | ❌ 职责过重（包含格式化逻辑） |

---

## 二、模块化设计改进方案

### 2.1 新增 `formatters` 模块

#### 方案设计

创建独立的 `formatters/` 模块，负责所有消息格式化逻辑：

```
formatters/
├── __init__.py
├── base.py              # 抽象基类
├── markdown.py          # Markdown 格式化器
├── wechat.py            # 企业微信格式化器
└── email.py             # 邮件格式化器（未来扩展）
```

---

#### 基类设计 (`formatters/base.py`)

```python
"""格式化器抽象基类"""

from abc import ABC, abstractmethod
from typing import Dict, List


class BaseFormatter(ABC):
    """消息格式化器基类"""

    @abstractmethod
    def format_report(self, papers: List[Dict], metadata: Dict = None) -> str:
        """
        格式化完整的报告

        Args:
            papers: 论文列表
            metadata: 元数据（日期、主题等）

        Returns:
            格式化后的消息
        """
        pass

    @abstractmethod
    def format_paper(self, paper: Dict) -> str:
        """
        格式化单篇论文

        Args:
            paper: 论文字典

        Returns:
            格式化后的论文
        """
        pass
```

---

#### Markdown 格式化器 (`formatters/markdown.py`)

```python
"""Markdown 格式化器 - 用于生成文件和完整报告"""

import datetime
from typing import Dict, List
from .base import BaseFormatter


class MarkdownFormatter(BaseFormatter):
    """Markdown 格式化器"""

    def format_report(self, papers: List[Dict], metadata: Dict = None) -> str:
        """生成 Markdown 格式的完整报告"""
        metadata = metadata or {}
        date = metadata.get('date', datetime.date.today())

        # 统计数据源
        source_stats = {}
        for paper in papers:
            source = paper.get('source', 'Unknown')
            source_stats[source] = source_stats.get(source, 0) + 1

        # 构建报告
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
        """格式化单篇论文"""
        paper = paper.copy()  # 避免修改原数据

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
```

---

#### 企业微信格式化器 (`formatters/wechat.py`)

```python
"""企业微信消息格式化器 - 紧凑布局，支持移动端"""

import datetime
import re
from typing import Dict, List
from .base import BaseFormatter


class WeChatFormatter(BaseFormatter):
    """企业微信消息格式化器"""

    def __init__(self, max_length: int = 4000):
        """
        初始化格式化器

        Args:
            max_length: 最大消息长度（企业微信限制约 4096）
        """
        self.max_length = max_length

    def format_report(self, papers: List[Dict], metadata: Dict = None) -> str:
        """生成企业微信紧凑格式的报告"""
        metadata = metadata or {}
        date = metadata.get('date', datetime.date.today())
        topic = metadata.get('topic', '大语言模型、智能体、增强型LLM推理和推理优化')

        # 构建头部
        header = self._build_header(date, topic, len(papers))
        result = [header, '---']

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
        """格式化单篇论文为紧凑布局"""
        # 解析 LLM 生成的摘要（如果存在）
        parsed = self._parse_llm_summary(paper.get('summary', ''))

        # 使用解析后的数据，或使用原始论文信息
        title_zh = parsed.get('title_zh', paper.get('title', ''))
        title_en = parsed.get('title_en', '')
        author = parsed.get('author', paper['authors'][0] if paper.get('authors') else 'Unknown')
        source = paper.get('source', '')

        parts = [
            f"📌 **{title_zh}**",
            f"<font color=\"info\">{title_en}</font>" if title_en else None,
            f"> 👤 {author}" + (f" | 📚 {source}" if source else ""),
            self._format_summary(parsed.get('summary', [])),
            self._format_innovations(parsed.get('innovations', [])),
            self._format_comment(parsed.get('comment', [])),
            f"> 🔗 [📖 阅读原文]({paper['url']})" if paper.get('url') else None,
        ]

        return '\n'.join(filter(None, parts))

    def _build_header(self, date, topic, count) -> str:
        """构建消息头部"""
        return f"# 📅 AI 前沿论文日报 ({date})\n\n**主题**: {topic}\n\n今日为您精选 {count} 篇最新论文"

    def _build_footer(self) -> str:
        """构建消息底部"""
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        return f"> 📅 {now} | 📊 共**{self._paper_count}**篇"

    def _parse_llm_summary(self, summary: str) -> Dict:
        """解析 LLM 生成的摘要，提取结构化数据"""
        # ... 解析逻辑（从 main.py 迁移）
        pass

    def _format_summary(self, summary_lines: List[str]) -> str:
        """格式化摘要（单行紧凑）"""
        summary_text = ' '.join(summary_lines)
        if len(summary_text) > 150:
            summary_text = summary_text[:147] + '...'
        return f"💡 {summary_text}" if summary_text else ""

    def _format_innovations(self, innovations: List[str]) -> str:
        """格式化创新点（符号列表）"""
        if not innovations:
            return ""

        result = ["> **核心创新**"]
        for innovation in innovations[:3]:
            if len(innovation) > 80:
                innovation = innovation[:77] + '...'
            result.append(f"> • {innovation}")

        return '\n'.join(result)

    def _format_comment(self, comment_lines: List[str]) -> str:
        """格式化简评（单行高亮）"""
        if not comment_lines:
            return ""
        comment_text = ' '.join(comment_lines)
        return f"📝 **简评**：{comment_text}"

    def _truncate_message(self, message: str) -> str:
        """截断过长的消息"""
        truncated = message[:self.max_length]
        truncated += "\n\n*内容已截断，完整报告请查看 daily_report.md*"
        return truncated

    @property
    def _paper_count(self):
        """获取当前论文数量（在格式化过程中动态设置）"""
        return getattr(self, '_count', 0)
```

---

### 2.2 增强 `notification` 模块

#### 修改 `notification/wechat.py`

```python
"""微信通知模块 - 集成格式化器"""

import httpx
from typing import Optional, Dict, List

from config.settings import Settings
from formatters import WeChatFormatter


class WeChatNotifier:
    """企业微信通知类 - 支持自动格式化"""

    def __init__(self, formatter: Optional[WeChatFormatter] = None):
        """
        初始化通知器

        Args:
            formatter: 消息格式化器，默认使用 WeChatFormatter
        """
        self.webhook_url = Settings.WECHAT_WEBHOOK
        self.timeout = 30.0
        self.formatter = formatter or WeChatFormatter()

    def send(self, message: str) -> bool:
        """
        发送已格式化的消息

        Args:
            message: Markdown 格式的消息

        Returns:
            是否发送成功
        """
        if not self.webhook_url:
            print("⚠ 未配置企业微信 Webhook，跳过微信推送")
            return False

        try:
            data = {
                "msgtype": "markdown",
                "markdown": {"content": message}
            }

            response = httpx.post(
                self.webhook_url,
                json=data,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    print("✅ 微信推送成功")
                    return True
                else:
                    print(f"⚠ 微信推送失败: {result.get('errmsg', '未知错误')}")
                    return False
            else:
                print(f"⚠ 微信推送请求失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"⚠ 微信推送异常: {e}")
            return False

    def send_report(
        self,
        papers: List[Dict],
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        发送论文报告（自动格式化）

        Args:
            papers: 论文列表
            metadata: 元数据（日期、主题等）

        Returns:
            是否发送成功
        """
        message = self.formatter.format_report(papers, metadata)
        return self.send(message)
```

---

#### 新增其他通知渠道示例

**邮件通知器** (`notification/email.py`):

```python
"""邮件通知模块"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config.settings import Settings
from formatters import MarkdownFormatter


class EmailNotifier:
    """邮件通知类"""

    def __init__(self, formatter: Optional[MarkdownFormatter] = None):
        self.smtp_server = Settings.SMTP_SERVER
        self.smtp_port = Settings.SMTP_PORT
        self.username = Settings.SMTP_USERNAME
        self.password = Settings.SMTP_PASSWORD
        self.from_email = Settings.EMAIL_FROM
        self.to_email = Settings.EMAIL_TO
        self.formatter = formatter or MarkdownFormatter()

    def send_report(self, papers: List, metadata: Dict = None) -> bool:
        """发送论文报告邮件"""
        message = self.formatter.format_report(papers, metadata)

        msg = MIMEMultipart()
        msg['From'] = self.from_email
        msg['To'] = self.to_email
        msg['Subject'] = f"📅 AI 前沿论文日报 - {metadata.get('date', '')}"

        msg.attach(MIMEText(message, 'plain', 'utf-8'))

        # 发送邮件逻辑...
        return True
```

---

### 2.3 简化 `main.py`

#### 重构后的 `main.py`

```python
"""AI 前沿论文日报生成器 - 主程序入口"""

import datetime
from typing import List, Dict

from config import Settings, SOURCES_CONFIG
from sources import ArxivSource, SpringerSource, SemanticScholarSource
from llm import LLMClient
from notification import WeChatNotifier
from formatters import MarkdownFormatter, WeChatFormatter
from utils import deduplicate_papers


class PaperBot:
    """论文日报生成机器人 - 简化版"""

    def __init__(self):
        """初始化机器人"""
        print("=" * 50)
        print("AI 前沿论文日报生成器")
        print("=" * 50)

        # 初始化组件
        self.llm_client = LLMClient()
        self.notifier = WeChatNotifier(WeChatFormatter())
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
        """从所有启用的数据源获取论文"""
        print("\n📚 开始获取论文数据...")
        print("=" * 50)

        all_papers = []

        for source in self.sources:
            try:
                papers = source.fetch_papers()
                paper_dicts = [p.to_dict() for p in papers]
                all_papers.extend(paper_dicts)
            except Exception as e:
                print(f"⚠ 数据源 {source.__class__.__name__} 出错: {e}")

        # 去重并限制数量
        unique_papers = deduplicate_papers(all_papers)
        papers = unique_papers[:Settings.MAX_PAPERS]

        print(f"\n🔄 原始论文数: {len(all_papers)}")
        print(f"✓ 去重后: {len(unique_papers)}")
        print(f"✓ 最终选取: {len(papers)} 篇\n")

        return papers

    def generate_summaries(self, papers: List[Dict]) -> List[Dict]:
        """为每篇论文生成摘要"""
        for i, paper in enumerate(papers, 1):
            print(f"\n[进度] 处理第 {i}/{len(papers)} 篇论文...")
            paper['summary'] = self.llm_client.generate_summary(paper)
        return papers

    def save_report(self, papers: List[Dict], report: str) -> None:
        """保存日报到文件"""
        with open(Settings.REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 报告已保存到 {Settings.REPORT_FILE}")

    def run(self):
        """运行完整的日报生成流程"""
        try:
            # 1. 获取论文
            papers = self.fetch_all_papers()

            if not papers:
                print("\n⚠ 未能获取到任何论文，请稍后重试")
                return

            # 2. 生成摘要
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
```

---

## 三、模块化带来的改进

### 3.1 代码复用性

| 场景 | 重构前 | 重构后 |
|------|--------|--------|
| **新增邮件通知** | 需要复制格式化逻辑，约 150 行 | 复用 `MarkdownFormatter`，约 30 行 |
| **新增 Slack 通知** | 需要重新编写格式化逻辑 | 新增 `SlackFormatter`，复用解析逻辑 |
| **单元测试** | 需要构造完整的 `PaperBot` | 独立测试 `WeChatFormatter.format_paper()` |

**示例：添加 Telegram 通知**

```python
# 重构前：需要复制 150+ 行格式化逻辑
class TelegramNotifier:
    def format_message(self, papers):
        # 复制粘贴 main.py 中的格式化逻辑...
        pass

# 重构后：只需 10 行
from formatters import WeChatFormatter  # 复用微信格式化器

class TelegramNotifier:
    def __init__(self):
        self.formatter = WeChatFormatter()  # 复用现有格式化器

    def send_report(self, papers, metadata):
        message = self.formatter.format_report(papers, metadata)
        # 发送到 Telegram...
```

---

### 3.2 可维护性

| 维护场景 | 重构前 | 重构后 |
|----------|--------|--------|
| **修改微信消息格式** | 需要在 `main.py` 的 190 行代码中定位 | 只需修改 `formatters/wechat.py` |
| **调整摘要长度限制** | 散落在多个方法的魔法数字 | 集中在 `WeChatFormatter.__init__(max_length)` |
| **添加新的论文字段** | 需要修改 `_format_paper_compact` 和解析逻辑 | 扩展 `BaseFormatter` 接口，各格式化器自行适配 |

**示例：修改微信消息的 emoji**

```python
# 重构前：在 _format_paper_compact() 中查找替换
title_line = f"📌 **{paper['title_zh']}**"  # 第 1 处
info_line = f"> 👤 {paper['author']}"  # 第 2 处
summary_text = f"💡 {summary_text}"  # 第 3 处
# ... 还有多处

# 重构后：只需修改常量配置
class WeChatFormatter(BaseFormatter):
    EMOJI = {
        'title': '📌',
        'author': '👤',
        'summary': '💡',
        'innovation': '🎯',
        'comment': '📝',
        'link': '🔗'
    }

    # 所有 emoji 统一管理，易于修改
```

---

### 3.3 可读性

| 对比项 | 重构前 | 重构后 |
|--------|--------|--------|
| **main.py 行数** | 273 行 | ~120 行（减少 56%） |
| **方法复杂度** | `PaperBot` 有 8 个方法 | `PaperBot` 有 5 个方法 |
| **职责清晰度** | 报告生成、格式化、发送混杂 | 职责分离：生成 → 格式化 → 发送 |
| **代码理解成本** | 需要理解 190 行格式化逻辑 | `PaperBot.run()` 逻辑清晰 |

**重构后的 `main.py` 结构**：

```python
class PaperBot:
    """简洁明了的职责划分"""

    def __init__(self):
        # 只初始化依赖
        self.llm_client = LLMClient()
        self.notifier = WeChatNotifier(WeChatFormatter())
        self.report_formatter = MarkdownFormatter()

    def fetch_all_papers(self): ...     # 数据获取
    def generate_summaries(self, papers): ...  # 摘要生成
    def save_report(self, papers, report): ... # 文件保存
    def run(self): ...                    # 流程编排
```

**格式化逻辑独立成模块**：

```python
# formatters/wechat.py
class WeChatFormatter(BaseFormatter):
    """专注于企业微信消息格式化"""

    def format_report(self, papers, metadata): ...   # 完整报告
    def format_paper(self, paper): ...              # 单篇论文
    def _parse_llm_summary(self, summary): ...      # 解析逻辑
    def _format_summary(self, lines): ...           # 摘要格式化
    def _format_innovations(self, list): ...       # 创新点格式化
```

---

### 3.4 可测试性

| 测试场景 | 重构前 | 重构后 |
|----------|--------|--------|
| **测试格式化逻辑** | 需要构造完整的 `PaperBot` 对象 | 直接测试 `WeChatFormatter.format_paper()` |
| **Mock 格式化器** | 需要使用复杂的 monkey patching | 传入 `MockFormatter` 对象 |
| **单元测试覆盖率** | 难以达到 80%+ | 轻松达到 90%+ |

**示例：单元测试对比**

```python
# 重构前：难以独立测试格式化逻辑
def test_wechat_formatting():
    # 需要初始化完整的 PaperBot
    bot = PaperBot()
    bot.llm_client = Mock()  # Mock LLM
    bot.notifier = Mock()    # Mock 通知器

    # 调用私有方法（不推荐）
    result = bot._format_paper_compact(mock_paper)
    assert "📌" in result

# 重构后：直接测试格式化器
def test_wechat_formatter():
    formatter = WeChatFormatter()
    paper = {
        'title': 'Test Paper',
        'authors': ['Author A'],
        'url': 'https://example.com',
        'summary': '...',
    }
    result = formatter.format_paper(paper)
    assert "📌" in result
    assert len(result) <= 4000  # 测试长度限制
```

---

### 3.5 可扩展性

| 扩展场景 | 重构前 | 重构后 |
|----------|--------|--------|
| **支持 HTML 格式报告** | 需要重写 `generate_daily_report()` | 新增 `HTMLFormatter` 继承 `BaseFormatter` |
| **支持 JSON 格式输出** | 需要修改多处代码 | 新增 `JSONFormatter` 继承 `BaseFormatter` |
| **支持多语言报告** | 需要修改所有格式化方法 | 在格式化器中添加语言参数 |

**示例：添加 JSON 格式报告**

```python
# 重构前：需要修改 generate_daily_report()，破坏现有逻辑
def generate_daily_report(self, papers):
    # 需要在此处添加 JSON 序列化逻辑
    # 会影响 Markdown 格式的生成
    pass

# 重构后：新增独立格式化器
class JSONFormatter(BaseFormatter):
    """JSON 格式化器"""

    def format_report(self, papers, metadata=None):
        import json
        data = {
            'date': str(metadata.get('date', '')) if metadata else '',
            'count': len(papers),
            'papers': papers
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def format_paper(self, paper):
        import json
        return json.dumps(paper, ensure_ascii=False, indent=2)

# 使用
json_formatter = JSONFormatter()
json_report = json_formatter.format_report(papers)
```

---

## 四、重构实施计划

### 4.1 阶段划分

| 阶段 | 任务 | 预计时间 |
|------|------|---------|
| **阶段 1** | 创建 `formatters/` 模块，实现基类和 Markdown 格式化器 | 1 小时 |
| **阶段 2** | 实现 `WeChatFormatter`，迁移格式化逻辑 | 2 小时 |
| **阶段 3** | 重构 `notification` 模块，集成格式化器 | 1 小时 |
| **阶段 4** | 简化 `main.py`，移除格式化代码 | 1 小时 |
| **阶段 5** | 编写单元测试，验证重构 | 1 小时 |
| **阶段 6** | 更新文档（`ARCHITECTURE.md`） | 0.5 小时 |

**总计：6.5 小时**

---

### 4.2 风险控制

| 风险 | 应对措施 |
|------|---------|
| **破坏现有功能** | 保留旧代码，逐步迁移，确保向后兼容 |
| **测试不充分** | 在每个阶段后运行完整测试 |
| **文档不同步** | 在重构完成后立即更新文档 |

---

## 五、总结

### 5.1 核心改进点

| 维度 | 具体改进 |
|------|---------|
| **代码复用性** | 格式化逻辑可在多个通知渠道复用 |
| **可维护性** | 职责分离，修改局部不影响全局 |
| **可读性** | `main.py` 行数减少 56%，逻辑更清晰 |
| **可测试性** | 格式化逻辑可独立单元测试 |
| **可扩展性** | 新增格式或通知渠道只需继承基类 |

### 5.2 设计原则遵循

| 原则 | 实现方式 |
|------|---------|
| **单一职责原则（SRP）** | `PaperBot` 只负责流程编排，格式化由专门的 `Formatter` 负责 |
| **开闭原则（OCP）** | 新增格式化器无需修改现有代码 |
| **依赖倒置原则（DIP）** | `WeChatNotifier` 依赖抽象的 `BaseFormatter` 而非具体实现 |

### 5.3 建议

✅ **推荐进行重构**，原因：
1. 当前 `main.py` 代码过于臃肿
2. 格式化逻辑与业务逻辑紧耦合
3. 难以添加新的通知渠道或报告格式
4. 单元测试困难

⚠️ **重构时机**：
- 当前功能稳定运行后再进行
- 保留旧代码作为备份
- 分阶段实施，每个阶段后测试
