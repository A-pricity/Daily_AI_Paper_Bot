# AI 前沿论文日报生成器

每天自动生成 AI 领域最新论文的中文技术简报，并推送到微信。

## 功能特点

- 🎯 **专注领域**：大语言模型、智能体、增强型 LLM 推理和推理优化
- 🤖 **智能翻译**：使用 NVIDIA GLM4.7 模型进行高质量翻译
- 📱 **微信推送**：自动推送到企业微信群
- ⏰ **定时运行**：每天早上 9 点（北京时间）自动运行
- 🔄 **自动重试**：API 请求失败时自动重试
- 📊 **去重机制**：自动去除重复论文
- 🌐 **多数据源**：支持 ArXiv、Springer、Semantic Scholar 等多个期刊/会议

## 支持的数据源

| 数据源 | 说明 | 是否需要 API Key |
|--------|------|----------------|
| **ArXiv** | 计算机科学预印本平台 | ❌ 不需要 |
| **Springer** | 顶级学术出版商 | ❌ 不需要（使用 RSS） |
| **Semantic Scholar** | AI 学术搜索引擎 | ✅ 需要（可选） |

### 可以获取的顶级期刊/会议

通过 ArXiv 可获取：
- ICML, NeurIPS, ICLR 等顶级会议论文
- 机器学习、深度学习、NLP 等领域预印本

通过 Springer 可获取：
- *Machine Learning* 期刊
- *Neural Computation* 期刊
- 其他 Springer 出版的 AI/ML 期刊

通过 Semantic Scholar 可获取：
- CVPR, ECCV, ACL, EMNLP 等会议论文
- 各大学术期刊的最新研究

## 本地运行

### 1. 安装依赖

```bash
# 使用 uv（推荐）
pip install uv
uv venv
uv pip install -r requirements.txt

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的 API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```
# NVIDIA API Key（必填）
NVIDIA_API_KEY=your_nvidia_api_key_here

# Semantic Scholar API Key（可选，用于获取更多论文源）
SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_api_key_here

# 企业微信 Webhook URL（可选）
WECHAT_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key_here
```

### 3. 获取 API Keys

#### NVIDIA API Key（必填）

1. 访问 https://build.nvidia.com/
2. 注册并登录
3. 在 API Keys 页面创建新的 API Key
4. 将 Key 填入 `.env` 文件

#### Semantic Scholar API Key（可选）

1. 访问 https://www.semanticscholar.org/product/api#api-key
2. 注册并申请免费的 API Key
3. 将 Key 填入 `.env` 文件

### 4. 获取企业微信 Webhook（可选）

1. 在企业微信群中点击 "..." -> 添加群机器人
2. 设置机器人名称并创建
3. 复制 Webhook 地址
4. 将地址填入 `.env` 文件

### 5. 运行程序

```bash
python main.py
```

生成的日报将保存在 `daily_report.md` 文件中。

## 部署到 GitHub Actions

### 1. 创建 GitHub 仓库

将此代码推送到你的 GitHub 仓库。

### 2. 配置 GitHub Secrets

进入仓库的 Settings -> Secrets and variables -> Actions，添加以下 Secrets：

- `NVIDIA_API_KEY`: 你的 NVIDIA API Key（必填）
- `SEMANTIC_SCHOLAR_API_KEY`: Semantic Scholar API Key（可选）
- `WECHAT_WEBHOOK`: 企业微信 Webhook URL（可选）

### 3. 修改 GitHub 仓库地址

编辑 `.github/workflows/daily_paper_bot.yml` 中的链接：

```yaml
wechat_message += f"\n📮 [点击查看完整报告](https://github.com/你的用户名/daily_ai_paper_bot/blob/main/daily_report.md)"
```

修改为你的实际仓库地址。

### 4. 自动运行

GitHub Actions 会在每天 UTC 时间 01:00（北京时间 09:00）自动运行。

你也可以在 GitHub Actions 页面手动触发运行。

## 配置数据源

在 `main.py` 中修改 `SOURCES_CONFIG` 可以启用或禁用不同的数据源：

```python
SOURCES_CONFIG = {
    'arxiv': {
        'enabled': True,  # 启用 ArXiv
        'search_topics': [...]  # 搜索主题
    },
    'springer': {
        'enabled': True,  # 启用 Springer
        'urls': [...]  # RSS 链接
    },
    'semantic_scholar': {
        'enabled': False,  # 需要 API Key
        'api_key': os.getenv('SEMANTIC_SCHOLAR_API_KEY'),
        'search_topics': [...]
    }
}
```

## 项目结构

```
daily_ai_paper_bot/
├── main.py                    # 主程序
├── requirements.txt            # 依赖列表
├── .env.example              # 环境变量模板
├── .env                      # 环境变量配置（不提交到 Git）
├── daily_report.md           # 生成的日报
├── README.md                 # 项目文档
├── DEPLOYMENT.md            # 部署指南
└── .github/
    └── workflows/
        └── daily_paper_bot.yml # GitHub Actions 配置
```

## 依赖项

- `arxiv`: ArXiv API 客户端
- `openai`: OpenAI 兼容的 API 客户端
- `python-dotenv`: 环境变量管理
- `httpx`: HTTP 客户端
- `feedparser`: RSS/Atom 解析器

## 注意事项

1. **API 限流**：ArXiv API 有速率限制，程序已内置重试机制
2. **Token 限制**：NVIDIA API 的 `max_tokens` 设置为 3500，足够生成完整报告
3. **微信消息长度**：企业微信有消息长度限制，微信推送只发送论文标题和链接
4. **数据源覆盖**：不同的数据源有不同的论文覆盖范围，建议组合使用以获取更全面的论文

## 扩展数据源

如需添加更多期刊/会议，可以在 `main.py` 中：

1. 添加新的获取函数（如 `get_papers_from_source_name`）
2. 在 `SOURCES_CONFIG` 中添加配置
3. 在 `main()` 函数中调用新函数

## 许可证

MIT License
