"""微信通知模块

负责将日报推送到企业微信群
"""

import httpx
from typing import Optional

from ..config.settings import Settings


class WeChatNotifier:
    """企业微信通知类"""

    def __init__(self):
        """初始化通知器"""
        self.webhook_url = Settings.WECHAT_WEBHOOK
        self.timeout = 30.0

    def send(self, message: str) -> bool:
        """
        发送消息到企业微信群

        Args:
            message: 要发送的 Markdown 格式消息

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
