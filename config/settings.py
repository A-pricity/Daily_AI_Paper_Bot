"""配置管理模块

负责加载和管理所有环境变量配置
"""

import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings:
    """应用配置类"""

    # API Keys
    NVIDIA_API_KEY: str = os.getenv('NVIDIA_API_KEY')
    SEMANTIC_SCHOLAR_API_KEY: Optional[str] = os.getenv('SEMANTIC_SCHOLAR_API_KEY')

    # 通知配置
    WECHAT_WEBHOOK: Optional[str] = os.getenv('WECHAT_WEBHOOK')

    # NVIDIA API 配置
    NVIDIA_API_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "z-ai/glm4.7"

    # ArXiv 配置
    ARXIV_SEARCH_TOPICS: List[str] = [
        "Large Language Models",
        "LLM Agents",
        "Chain of Thought",
        "Batch of Thought",
        "LLM Reasoning"
    ]

    # LLM 配置
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 3500
    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_DELAY: int = 30

    # HTTP 配置
    HTTP_TIMEOUT: float = 120.0
    HTTP_RETRY_DELAY: int = 30

    # 报告配置
    MAX_PAPERS: int = 5
    REPORT_FILE: str = "daily_report.md"

    @classmethod
    def validate(cls) -> None:
        """验证必要的配置项"""
        if not cls.NVIDIA_API_KEY:
            raise ValueError("请设置环境变量 NVIDIA_API_KEY 或在 .env 文件中配置")


# 数据源配置
SOURCES_CONFIG: Dict[str, Dict] = {
    'arxiv': {
        'enabled': True,
        'base_url': 'http://export.arxiv.org/api/query?',
        'search_topics': Settings.ARXIV_SEARCH_TOPICS,
        'max_results': 1,
        'page_size': 10,
        'delay_seconds': 10,
        'delay_between_topics': 15
    },
    'semantic_scholar': {
        'enabled': False,  # 默认关闭，需要 API Key
        'api_key': Settings.SEMANTIC_SCHOLAR_API_KEY,
        'search_topics': [
            "large language models",
            "LLM agents",
            "reasoning optimization"
        ],
        'max_results': 1
    },
    'springer': {
        'enabled': True,  # Springer 有公开的 RSS feeds
        'urls': [
            'https://link.springer.com/rss/journal/volumesandissues/12559',  # Machine Learning
            'https://link.springer.com/rss/journal/volumesandissues/11032',  # Neural Computation
        ],
        'max_results': 2
    }
}
