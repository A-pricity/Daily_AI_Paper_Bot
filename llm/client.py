"""LLM 客户端模块

负责调用 NVIDIA API 生成论文摘要
"""

import time
from typing import Optional
import httpx
from openai import OpenAI

from config.settings import Settings
from utils.helpers import extract_clean_summary, validate_summary


class LLMClient:
    """LLM 客户端类"""

    def __init__(self):
        """初始化 LLM 客户端"""
        Settings.validate()

        self.http_client = httpx.Client(timeout=Settings.HTTP_TIMEOUT)
        self.client = OpenAI(
            base_url=Settings.NVIDIA_API_BASE_URL,
            api_key=Settings.NVIDIA_API_KEY,
            http_client=self.http_client
        )

    def generate_summary(
        self,
        paper: dict,
        max_retries: Optional[int] = None
    ) -> str:
        """
        生成论文摘要

        Args:
            paper: 论文字典，包含 title, authors, abstract 等
            max_retries: 最大重试次数，默认使用配置值

        Returns:
            生成的摘要文本
        """
        max_retries = max_retries or Settings.LLM_MAX_RETRIES

        title = paper['title']
        author = paper['authors'][0] if paper['authors'] else 'Unknown'

        prompt = self._build_prompt(paper)

        print(f"正在研读论文: {title}")

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=Settings.NVIDIA_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一个专业的AI论文翻译助手。只输出格式化的中文报告，不要输出任何思考过程或分析说明。"
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=Settings.LLM_TEMPERATURE,
                    max_tokens=Settings.LLM_MAX_TOKENS,
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
                            time.sleep(Settings.LLM_RETRY_DELAY)
                            continue

                    return cleaned
                else:
                    print("⚠ API 返回空内容")
                    return "⚠ 模型返回空内容，请重试"

            except Exception as e:
                print(f"⚠ 请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(Settings.LLM_RETRY_DELAY)
                else:
                    return f"⚠ API 请求失败: {str(e)}"

        return "⚠ 生成摘要失败"

    def _build_prompt(self, paper: dict) -> str:
        """构建生成摘要的 prompt"""
        return f"""任务：翻译以下英文论文摘要为中文技术简报。

必须严格按照以下格式输出，不要包含任何其他内容：

## 📄 论文标题：[中文翻译的标题]
**原标题**：{paper['title']}
**第一作者**：{paper['authors'][0] if paper['authors'] else 'Unknown'} | **机构**：未知

### 🎯 核心摘要
[用中文翻译论文摘要，保持专业术语准确性]

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

    def close(self):
        """关闭客户端连接"""
        if self.http_client:
            self.http_client.close()


def generate_paper_summary(paper: dict) -> str:
    """
    便捷函数：生成论文摘要

    Args:
        paper: 论文字典

    Returns:
        生成的摘要文本
    """
    client = LLMClient()
    try:
        return client.generate_summary(paper)
    finally:
        client.close()
