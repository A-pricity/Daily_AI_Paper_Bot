"""微信通知模块 - 集成格式化器，支持自动格式化"""

import httpx
from typing import Optional, Dict, List

from config.settings import Settings


class WeChatNotifier:
    """企业微信通知类 - 支持自动格式化和发送"""

    def __init__(self, formatter=None):
        """
        初始化通知器

        Args:
            formatter: 消息格式化器，延迟导入避免循环依赖
        """
        self.webhook_url = Settings.WECHAT_WEBHOOK
        self.timeout = 30.0
        self._formatter = formatter

    @property
    def formatter(self):
        """延迟加载格式化器，避免循环导入"""
        if self._formatter is None:
            from formatters import WeChatFormatter
            self._formatter = WeChatFormatter()
        return self._formatter

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
                "markdown": {
                    "content": message
                }
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
        print("\n正在推送到微信...")
        message = self.formatter.format_report(papers, metadata)
        return self.send(message)

