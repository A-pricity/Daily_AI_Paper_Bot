# 模块化架构说明

## 项目结构

```
daily_ai_paper_bot/
├── main.py                         # 主程序入口
├── config/                         # 配置模块
│   ├── __init__.py
│   └── settings.py                 # 配置管理
├── sources/                        # 数据源模块
│   ├── __init__.py
│   ├── base.py                     # 抽象基类和接口
│   ├── arxiv_source.py             # ArXiv 数据源
│   ├── springer_source.py          # Springer 数据源
│   └── semantic_scholar_source.py # Semantic Scholar 数据源
├── llm/                           # LLM 调用模块
│   ├── __init__.py
│   └── client.py                   # NVIDIA API 客户端
├── formatters/                     # 格式化器模块
│   ├── __init__.py
│   ├── base.py                     # 抽象基类
│   ├── markdown.py                 # Markdown 格式化器
│   └── wechat.py                   # 企业微信格式化器
├── notification/                   # 通知模块
│   ├── __init__.py
│   └── wechat.py                  # 企业微信推送
├── utils/                         # 工具模块
│   ├── __init__.py
│   └── helpers.py                 # 辅助函数
├── .env.example                   # 环境变量模板
├── requirements.txt                # 依赖列表
└── README.md                      # 项目文档
```

## 模块职责划分

### 1. config (配置模块)

**职责**：
- 管理所有环境变量配置
- 提供统一的配置访问接口
- 数据源配置管理

**核心类**：
- `Settings`: 应用配置类，包含所有配置项
- `SOURCES_CONFIG`: 数据源配置字典

**接口**：
```python
from config import Settings, SOURCES_CONFIG

# 使用配置
api_key = Settings.NVIDIA_API_KEY
topics = Settings.ARXIV_SEARCH_TOPICS
config = SOURCES_CONFIG['arxiv']
```

---

### 2. sources (数据源模块)

**职责**：
- 定义统一的数据源接口
- 实现各数据源的论文获取逻辑
- 提供标准化的论文数据模型

**核心类**：
- `BasePaperSource`: 抽象基类，定义统一接口
- `Paper`: 论文数据模型
- `ArxivSource`: ArXiv 数据源实现
- `SpringerSource`: Springer RSS 数据源实现
- `SemanticScholarSource`: Semantic Scholar API 数据源实现

**接口**：
```python
from sources import BasePaperSource, Paper, ArxivSource

# 使用数据源
source = ArxivSource(config)
papers = source.fetch_papers(max_results=5)

# Paper 对象
paper = Paper(title="...", authors=["..."], ...)
data = paper.to_dict()  # 转换为字典
```

---

### 3. llm (LLM 调用模块)

**职责**：
- 封装 NVIDIA API 调用逻辑
- 生成论文摘要
- 处理 API 响应和错误

**核心类**：
- `LLMClient`: LLM 客户端类，负责 API 调用
- `generate_paper_summary`: 便捷函数，快速生成摘要

**接口**：
```python
from llm import LLMClient, generate_paper_summary

# 使用客户端
client = LLMClient()
summary = client.generate_summary(paper_dict)
client.close()

# 使用便捷函数
summary = generate_paper_summary(paper_dict)
```

---

### 4. formatters (格式化器模块)

**职责**：
- 将论文数据转换为不同格式的消息
- 支持多种输出格式（Markdown、企业微信、飞书等）
- 统一的格式化接口

**核心类**：
- `BaseFormatter`: 抽象基类，定义统一接口
- `MarkdownFormatter`: Markdown 格式化器，用于生成文件
- `WeChatFormatter`: 企业微信格式化器，紧凑布局，适合移动端
- `FeishuFormatter`: 飞书格式化器，针对 20KB 限制优化，关键信息前置

**接口**：
```python
from formatters import MarkdownFormatter, WeChatFormatter, FeishuFormatter

# Markdown 格式化器（用于文件）
md_formatter = MarkdownFormatter()
markdown_report = md_formatter.format_report(papers, metadata)

# 企业微信格式化器（用于推送）
wechat_formatter = WeChatFormatter()
wechat_message = wechat_formatter.format_report(papers, metadata)

# 飞书格式化器（用于推送，带限流控制）
feishu_formatter = FeishuFormatter()
feishu_message = feishu_formatter.format_report(papers, metadata)

# 单篇论文格式化
formatted_paper = wechat_formatter.format_paper(paper)
```

---

### 5. notification (通知模块)

**职责**：
- 封装企业微信和飞书推送逻辑
- 集成格式化器，支持自动格式化发送
- 飞书限流控制和错峰发送策略

**核心类**：
- `WeChatNotifier`: 企业微信通知器
- `FeishuNotifier`: 飞书通知器（带限流控制）

**接口**：
```python
from notification import WeChatNotifier, FeishuNotifier

# 企业微信通知器
wechat_notifier = WeChatNotifier()
success = wechat_notifier.send(markdown_message)
success = wechat_notifier.send_report(papers, metadata)

# 飞书通知器（自动限流）
feishu_notifier = FeishuNotifier()
success = feishu_notifier.send(markdown_message)
success = feishu_notifier.send_report(papers, metadata)

# 查看飞书限流状态
status = feishu_notifier.get_rate_limit_status()
print(status)
# {
#   'requests_this_minute': 2,
#   'requests_remaining': 98,
#   'seconds_until_reset': 45,
#   'is_peak_hour': False,
#   'last_request_seconds_ago': 10
# }
```

---

### 6. utils (工具模块)

**职责**：
- 提供通用的辅助函数
- 论文数据去重
- 文本清理和验证

**核心函数**：
- `extract_clean_summary`: 清理 LLM 输出，提取格式化报告
- `validate_summary`: 验证报告完整性
- `deduplicate_papers`: 论文去重

**接口**：
```python
from utils import extract_clean_summary, validate_summary, deduplicate_papers

# 清理输出
cleaned = extract_clean_summary(raw_content)

# 验证报告
missing = validate_summary(report_content)

# 去重
unique = deduplicate_papers(papers_list)
```

---

### 7. main (主程序)

**职责**：
- 协调各模块完成日报生成流程
- 实现完整的业务逻辑
- 管理程序生命周期

**核心类**：
- `PaperBot`: 日报生成机器人主类

**流程**：
```python
bot = PaperBot()
bot.run()

# PaperBot.run() 内部流程：
# 1. fetch_all_papers() - 从所有数据源获取论文
# 2. generate_summaries() - 为每篇论文生成 LLM 摘要
# 3. report_formatter.format_report() - 生成 Markdown 报告
# 4. save_report() - 保存到文件
# 5. notifier.send_report() - 推送到微信（自动格式化）
```

---

## 模块调用关系图

```
┌─────────────┐
│   main.py   │  主程序入口
└──────┬──────┘
       │
       ├─────────────────────────────────────────────────────┐
       │                                             │
       ▼                                             ▼
┌──────────────┐                              ┌──────────────┐
│    config   │ ───配置──▶                │    llm      │
└──────────────┘                              └──────┬───────┘
                                                    │
       │                                            │
       ▼                                            ▼
┌──────────────┐                              ┌──────────────┐
│   sources   │ ───论文──▶  PaperBot ◀────│ generate    │
└──────────────┘                              │ summary     │
       │                                      └──────────────┘
       │
       ▼
┌──────────────┐
│   utils     │ ◀────使用────┐
└──────────────┘              │
                             │
┌──────────────┐ ◀──使用──┐
│  formatters │          │
└──────┬───────┘          │
       │                  │
       ▼                  │
┌──────────────┐ ◀──通知──┘
│ notification│
└──────────────┘
```

---

## 模块间依赖关系

| 模块 | 依赖的模块 | 说明 |
|------|-----------|------|
| **main** | config, sources, llm, formatters, notification, utils | 协调所有模块 |
| **sources** | config, utils | 读取配置，使用工具函数 |
| **llm** | config, utils | 读取配置，使用文本处理函数 |
| **formatters** | 无 | 独立格式化逻辑 |
| **notification** | config, formatters | 读取配置，使用格式化器 |
| **utils** | 无 | 独立工具函数 |
| **config** | 无 | 独立配置管理 |

**设计原则**：
- ✅ **单向依赖**：避免循环依赖
- ✅ **低耦合**：模块间通过简单接口交互
- ✅ **高内聚**：每个模块职责单一明确
- ✅ **可替换**：数据源和通知模块易于扩展

---

## 扩展指南

### 添加新的数据源

1. 在 `sources/` 目录创建新文件，如 `new_source.py`

2. 继承 `BasePaperSource`：
```python
from sources.base import BasePaperSource, Paper

class NewSource(BasePaperSource):
    def fetch_papers(self, max_results=5):
        # 实现获取逻辑
        return [Paper(...)]
```

3. 在 `sources/__init__.py` 中导出：
```python
from .new_source import NewSource
__all__ = [..., 'NewSource']
```

4. 在 `config/settings.py` 的 `SOURCES_CONFIG` 中添加配置

5. 在 `main.py` 的 `PaperBot.__init__()` 中初始化

### 添加新的通知渠道

1. 在 `notification/` 目录创建新文件，如 `email.py`

2. 创建通知器类：
```python
class EmailNotifier:
    def send(self, message):
        # 实现邮件发送逻辑
        pass
```

3. 在 `notification/__init__.py` 中导出

4. 在 `main.py` 中使用

---

## 测试建议

```python
# 测试单个数据源
from sources import ArxivSource
from config import SOURCES_CONFIG

source = ArxivSource(SOURCES_CONFIG['arxiv'])
papers = source.fetch_papers()
print(f"获取到 {len(papers)} 篇论文")

# 测试 LLM
from llm import LLMClient

client = LLMClient()
paper = {"title": "...", "authors": [...], "abstract": "..."}
summary = client.generate_summary(paper)
print(summary)

# 测试工具函数
from utils import deduplicate_papers

papers = [...]
unique = deduplicate_papers(papers)
print(f"去重: {len(papers)} -> {len(unique)}")
```
