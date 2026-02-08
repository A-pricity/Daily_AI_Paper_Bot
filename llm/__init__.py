"""LLM 调用模块 - 负责与大语言模型的交互"""

from .client import LLMClient, generate_paper_summary

__all__ = ['LLMClient', 'generate_paper_summary']
