"""飞书通知模块 - 支持限流控制和错峰发送策略"""

import time
import httpx
from typing import Optional, Dict, List
from datetime import datetime

from config.settings import Settings


class FeishuNotifier:
    """飞书机器人通知类 - 支持限流控制和错峰发送"""

    # 限流配置
    RATE_LIMIT_PER_MINUTE = 100  # 每分钟 100 次请求
    RATE_LIMIT_PER_SECOND = 5     # 每秒 5 次请求
    MAX_REQUEST_SIZE = 20 * 1024   # 请求体最大 20KB

    # 错峰时间窗口（避开高峰期）
    PEAK_HOURS = [
        (10, 0), (10, 30),   # 10:00, 10:30
        (17, 0), (17, 30),   # 17:00, 17:30
    ]

    def __init__(self, webhook_url: Optional[str] = None):
        """
        初始化飞书通知器

        Args:
            webhook_url: 飞书机器人 Webhook URL
        """
        self.webhook_url = webhook_url or Settings.FEISHU_WEBHOOK
        self.timeout = 30.0
        self.request_count = 0
        self.minute_start_time = time.time()
        self.last_request_time = 0

    def send(self, message: str) -> bool:
        """
        发送消息到飞书（自动限流）

        Args:
            message: Markdown 格式的消息

        Returns:
            是否发送成功
        """
        if not self.webhook_url:
            print("⚠ 未配置飞书 Webhook，跳过推送")
            return False

        # 检查请求体大小
        message_size = len(message.encode('utf-8'))
        if message_size > self.MAX_REQUEST_SIZE:
            print(f"⚠ 消息过大 ({message_size} bytes)，已压缩")
            message = self._compress_message(message, self.MAX_REQUEST_SIZE)

        # 限流控制
        self._wait_for_rate_limit()

        # 检查是否在高峰期
        if self._is_peak_hour():
            print("⚠ 当前处于高峰期，建议错峰发送")
            # 等待 30 秒避开高峰
            time.sleep(30)

        try:
            data = {
                "msg_type": "markdown",
                "content": {
                    "text": message
                }
            }

            response = httpx.post(
                self.webhook_url,
                json=data,
                timeout=self.timeout
            )

            self.request_count += 1
            self.last_request_time = time.time()

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    print("✅ 飞书推送成功")
                    return True
                else:
                    error_code = result.get('code')
                    error_msg = result.get('msg', '未知错误')
                    print(f"⚠ 飞书推送失败: [{error_code}] {error_msg}")

                    # 处理限流错误
                    if error_code == 11232:
                        print("⚠ 触发限流，等待 60 秒后重试...")
                        time.sleep(60)
                        return self._retry_send(data)
                    return False
            else:
                print(f"⚠ 飞书推送请求失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"⚠ 飞书推送异常: {e}")
            return False

    def send_report(
        self,
        papers: List[Dict],
        metadata: Optional[Dict] = None,
        formatter=None
    ) -> bool:
        """
        发送论文报告（自动格式化）

        Args:
            papers: 论文列表
            metadata: 元数据（日期、主题等）
            formatter: 格式化器

        Returns:
            是否发送成功
        """
        print("\n正在推送到飞书...")

        # 延迟加载格式化器避免循环依赖
        if formatter is None:
            from formatters import FeishuFormatter
            formatter = FeishuFormatter()

        message = formatter.format_report(papers, metadata)
        return self.send(message)

    def _wait_for_rate_limit(self):
        """限流等待策略"""
        current_time = time.time()
        elapsed_minute = current_time - self.minute_start_time

        # 重置分钟计数器
        if elapsed_minute >= 60:
            self.request_count = 0
            self.minute_start_time = current_time
        else:
            # 每分钟限流
            if self.request_count >= self.RATE_LIMIT_PER_MINUTE:
                wait_time = 60 - elapsed_minute
                print(f"⚠ 达到每分钟限流，等待 {wait_time:.1f} 秒...")
                time.sleep(wait_time)
                self.request_count = 0
                self.minute_start_time = time.time()

        # 每秒限流
        time_since_last = current_time - self.last_request_time
        if time_since_last < (1 / self.RATE_LIMIT_PER_SECOND):
            wait_time = (1 / self.RATE_LIMIT_PER_SECOND) - time_since_last
            time.sleep(wait_time)

    def _is_peak_hour(self) -> bool:
        """检查是否在高峰期"""
        now = datetime.now()
        for hour, minute in self.PEAK_HOURS:
            if now.hour == hour and (minute - 5 <= now.minute <= minute + 5):
                return True
        return False

    def _compress_message(self, message: str, max_size: int) -> str:
        """压缩消息以符合大小限制"""
        # 简单截断策略
        encoded = message.encode('utf-8')
        if len(encoded) <= max_size:
            return message

        # 保留头部，截断中间部分
        lines = message.split('\n')
        result = []
        current_size = 0

        for line in lines:
            line_size = len(line.encode('utf-8'))
            if current_size + line_size + 1 > max_size - 100:  # 预留 100 字节
                result.append("\n\n*内容已截断，完整报告请查看 daily_report.md*")
                break
            result.append(line)
            current_size += line_size + 1

        return '\n'.join(result)

    def _retry_send(self, data: dict, max_retries: int = 3) -> bool:
        """重试发送"""
        for attempt in range(max_retries):
            time.sleep(5)  # 等待 5 秒

            try:
                response = httpx.post(
                    self.webhook_url,
                    json=data,
                    timeout=self.timeout
                )

                self.request_count += 1
                self.last_request_time = time.time()

                if response.status_code == 200:
                    result = response.json()
                    if result.get('code') == 0:
                        print(f"✅ 飞书推送成功（重试 {attempt + 1} 次）")
                        return True
            except Exception as e:
                print(f"⚠ 重试失败 (尝试 {attempt + 1}/{max_retries}): {e}")

        return False

    def get_rate_limit_status(self) -> Dict[str, any]:
        """获取当前限流状态"""
        current_time = time.time()
        elapsed_minute = current_time - self.minute_start_time
        return {
            'requests_this_minute': self.request_count,
            'requests_remaining': self.RATE_LIMIT_PER_MINUTE - self.request_count,
            'seconds_until_reset': max(0, 60 - elapsed_minute),
            'is_peak_hour': self._is_peak_hour(),
            'last_request_seconds_ago': current_time - self.last_request_time if self.last_request_time else 0
        }
