import arxiv
from openai import OpenAI
import datetime
import os
import time
import httpx
from dotenv import load_dotenv
import json

# 加载 .env 文件
load_dotenv()

# 配置部分：从环境变量读取 NVIDIA API Key
NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')
if not NVIDIA_API_KEY:
    raise ValueError("请设置环境变量 NVIDIA_API_KEY 或在 .env 文件中配置")

# 获取企业微信 Webhook URL（可选）
WECHAT_WEBHOOK = os.getenv('WECHAT_WEBHOOK')

# 初始化 NVIDIA 客户端
http_client = httpx.Client(timeout=120.0)
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY,
    http_client=http_client
)

def get_latest_papers_with_retry(topic="Large Language Models", max_results=3, max_retries=3):
    """
    从 ArXiv 获取指定主题的最新论文，带重试机制
    """
    print(f"正在检索关于 {topic} 的最新论文...")

    for attempt in range(max_retries):
        try:
            # 使用新的 Client API，配置页面大小和延迟
            client_arxiv = arxiv.Client(page_size=10, delay_seconds=10)
            search = arxiv.Search(
                query=topic,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )

            papers_data = []
            for result in client_arxiv.results(search):
                papers_data.append({
                    "title": result.title,
                    "authors": [author.name for author in result.authors],
                    "abstract": result.summary,
                    "url": result.entry_id,
                    "published": result.published
                })

            print(f"✓ 成功获取 {len(papers_data)} 篇论文")
            return papers_data

        except Exception as e:
            print(f"⚠ 请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 10
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"✗ 无法获取关于 '{topic}' 的论文")
                return []

def extract_clean_summary(content):
    """
    从 API 响应中提取干净的格式化报告
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

    # 简化版本：直接从开始位置提取所有内容
    # 只在遇到明显的思考过程章节标题时才进行过滤
    result_lines = []
    skip_next_lines = False
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


def validate_summary(content):
    """
    验证报告是否包含所有必需的章节
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


def generate_summary(paper, max_retries=3):
    """
    调用 NVIDIA API 生成中文解读，带重试机制
    """
    print(f"正在研读论文：{paper['title']} ...")

    # 使用更简洁的 prompt，明确要求只输出最终结果
    prompt = f"""任务：翻译以下英文论文摘要为中文技术简报。

必须严格按照以下格式输出，不要包含任何其他内容：

## 📄 论文标题：[中文翻译的标题]
**原标题**：{paper['title']}
**第一作者**：{paper['authors'][0]} | **机构**：未知

### 🎯 核心摘要
[用中文翻译论文摘要，保持专业术语准确性，内容要完整详细]

### 💡 核心创新点与贡献
* [根据摘要列出3个核心创新点]
* [创新点2]
* [创新点3]

### 🧐 简评与启示
[一句话总结论文价值]

论文摘要：{paper['abstract']}

输出要求：
1. 只输出格式化的报告内容
2. 不要输出任何分析、思考过程、步骤说明
3. 不要输出"好的，我来翻译"之类的开头
4. 直接从"## 📄"开始输出
5. 确保核心摘要部分有完整的内容，不要留空"""

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="z-ai/glm4.7",
                messages=[
                    {"role": "system", "content": "你是一个专业的AI论文翻译助手。只输出格式化的中文报告，不要输出任何思考过程或分析说明。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3500,  # 进一步增加到 3500
            )

            content = response.choices[0].message.content

            if content:
                # 清理输出，提取干净的报告
                cleaned = extract_clean_summary(content)

                # 验证是否包含所有必需章节
                missing = validate_summary(cleaned)
                if missing:
                    print(f"⚠ 报告不完整，缺少章节: {', '.join(missing)}")
                    if attempt < max_retries - 1:
                        print(f"尝试 {attempt + 1} 不完整，准备重试...")
                        time.sleep(30)
                        continue
                    else:
                        print(f"⚠ 已达最大重试次数，返回不完整的结果")

                return cleaned
            else:
                print("⚠ API 返回空内容")
                return "⚠ 模型返回空内容，请重试"

        except Exception as e:
            error_msg = str(e)
            print(f"⚠ 请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = 30
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                return f"⚠ API 请求失败，请稍后重试或检查 API Key 是否正确"

def send_to_wechat(message):
    """
    将消息发送到企业微信群机器人
    """
    if not WECHAT_WEBHOOK:
        print("⚠ 未配置企业微信 Webhook，跳过微信推送")
        return False

    try:
        # 企业微信消息格式
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": message
            }
        }

        response = httpx.post(
            WECHAT_WEBHOOK,
            json=data,
            timeout=30.0
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


def main():
    # 1. 获取论文
    # 专注于：大语言模型、智能体、增强型LLM推理和推理优化
    search_topics = [
        "Large Language Models",
        "LLM Agents",
        "Chain of Thought",
        "Batch of Thought",
        "LLM Reasoning"
    ]

    print("="*50)
    print("开始获取论文数据...")
    print("="*50)

    all_papers = []
    for i, topic in enumerate(search_topics):
        print(f"\n[{i+1}/{len(search_topics)}] 处理主题: {topic}")

        # 每次主题之间添加额外延迟
        if i > 0:
            print(f"等待 15 秒后继续下一个主题...")
            time.sleep(15)

        # 单个主题只获取 1 篇，减少请求压力
        papers = get_latest_papers_with_retry(topic=topic, max_results=1, max_retries=3)
        all_papers.extend(papers)

    # 去重（基于URL）
    seen_urls = set()
    unique_papers = []
    for paper in all_papers:
        if paper['url'] not in seen_urls:
            seen_urls.add(paper['url'])
            unique_papers.append(paper)

    # 限制最多5篇
    papers = unique_papers[:5]

    if not papers:
        print("\n⚠ 未能获取到任何论文，请稍后重试")
        return

    print(f"\n✓ 共获取到 {len(papers)} 篇论文\n")

    daily_report = f"# 📅 AI 前沿论文日报 ({datetime.date.today()})\n\n"
    daily_report += f"**主题**: 大语言模型、智能体、增强型LLM推理和推理优化\n\n"
    daily_report += f"今日为您精选 {len(papers)} 篇最新论文\n\n"

    # 2. 逐篇处理
    for i, paper in enumerate(papers, 1):
        print(f"\n处理第 {i}/{len(papers)} 篇论文...")
        summary = generate_summary(paper, max_retries=3)

        # 拼接内容
        daily_report += f"{summary}\n"
        daily_report += f"🔗 **原文链接**: {paper['url']}\n"
        daily_report += "---\n\n"

    # 3. 输出结果（实际部署时这里可以替换为发送邮件或推送到微信的代码）
    print("\n" + "="*20 + " 生成结果 " + "="*20 + "\n")
    print(daily_report)

    # 4. 将结果保存到文件
    with open('daily_report.md', 'w', encoding='utf-8') as f:
        f.write(daily_report)
    print("\n✅ 报告已保存到 daily_report.md")

    # 5. 推送到微信（如果配置了 Webhook）
    if WECHAT_WEBHOOK:
        print("\n正在推送到微信...")
        # 生成适合微信的消息格式（简化版）
        wechat_message = f"## 📅 AI 前沿论文日报 ({datetime.date.today()})\n\n"
        wechat_message += f"**主题**: 大语言模型、智能体、增强型LLM推理和推理优化\n\n"
        wechat_message += f"今日为您精选 {len(papers)} 篇最新论文\n\n"

        # 从已生成的报告中提取论文标题
        import re
        title_pattern = r'## 📄 论文标题：(.*?)\n'
        titles = re.findall(title_pattern, daily_report)

        for i, title in enumerate(titles, 1):
            wechat_message += f"**{i}. {title}**\n\n"

        # 添加 GitHub 链接（需要用户替换为自己的仓库地址）
        wechat_message += f"\n📮 [点击查看完整报告](https://github.com/your-username/daily_ai_paper_bot/blob/main/daily_report.md)"

        send_to_wechat(wechat_message)
    else:
        print("\n⚠ 未配置企业微信 Webhook，跳过微信推送")

    # 关闭 http 客户端
    http_client.close()

if __name__ == "__main__":
    main()
