# AI 前沿论文日报生成器

每天自动生成 AI 领域最新论文的中文技术简报，并推送到微信。

## 功能特点

- 🎯 **专注领域**：大语言模型、智能体、增强型 LLM 推理和推理优化
- 🤖 **智能翻译**：使用 NVIDIA GLM4.7 模型进行高质量翻译
- 📱 **微信推送**：自动推送到企业微信群
- ⏰ **定时运行**：每天早上 9 点（北京时间）自动运行
- 🔄 **自动重试**：API 请求失败时自动重试
- 📊 **去重机制**：自动去除重复论文

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
NVIDIA_API_KEY=your_nvidia_api_key_here
WECHAT_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key_here
```

### 3. 获取 NVIDIA API Key

1. 访问 https://build.nvidia.com/
2. 注册并登录
3. 在 API Keys 页面创建新的 API Key
4. 将 Key 填入 `.env` 文件

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

- `NVIDIA_API_KEY`: 你的 NVIDIA API Key
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

## 项目结构

```
daily_ai_paper_bot/
├── main.py                    # 主程序
├── requirements.txt            # 依赖列表
├── .env.example              # 环境变量模板
├── .env                      # 环境变量配置（不提交到 Git）
├── daily_report.md           # 生成的日报
└── .github/
    └── workflows/
        └── daily_paper_bot.yml # GitHub Actions 配置
```

## 依赖项

- `arxiv`: ArXiv API 客户端
- `openai`: OpenAI 兼容的 API 客户端
- `python-dotenv`: 环境变量管理
- `httpx`: HTTP 客户端

## 注意事项

1. **API 限流**：ArXiv API 有速率限制，程序已内置重试机制
2. **Token 限制**：NVIDIA API 的 `max_tokens` 设置为 3500，足够生成完整报告
3. **微信消息长度**：企业微信有消息长度限制，微信推送只发送论文标题和链接

## 许可证

MIT License
\"# Daily_AI_Paper_Bot\" 
