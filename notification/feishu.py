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
        发送消息到飞书（自动限流，支持 Markdown 和 Text 类型降级）

        Args:
            message: 消息内容

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

        # 先尝试 Markdown 类型
        markdown_result = self._send_with_type(message, "markdown")
        if markdown_result:
            return True

        # Markdown 失败，降级到 text 类型
        print("⚠ Markdown 类型不支持，尝试 text 类型...")
        text_result = self._send_with_type(self._markdown_to_text(message), "text")
        return text_result

    def _send_with_type(self, message: str, msg_type: str) -> bool:
        """
        使用指定类型发送消息

        Args:
            message: 消息内容
            msg_type: 消息类型 (markdown/text)

        Returns:
            是否发送成功
        """
        try:
            data = {
                "msg_type": msg_type,
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
                    print(f"✅ 飞书推送成功 ({msg_type})")
                    return True
                else:
                    error_code = result.get('code')
                    error_msg = result.get('msg', '未知错误')
                    print(f"⚠ 飞书推送失败 ({msg_type}): [{error_code}] {error_msg}")

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

    def _markdown_to_text(self, markdown: str) -> str:
        """
        将 Markdown 转换为纯文本（简化版）

        Args:
            markdown: Markdown 格式文本

        Returns:
            纯文本
        """
        # 移除 Markdown 标记，保留内容
        text = markdown
        # 移除标题标记
        text = text.replace('### ', '').replace('## ', '').replace('# ', '')
        # 移除粗体标记
        text = text.replace('**', '')
        # 移除链接标记，保留 URL
        text = text.replace('[', '').replace('](', ' ').replace(')', '')
        # 移除引用标记
        text = text.replace('> ', '')
        # 移除列表标记
        text = text.replace('* ', '• ')
        # 移除代码块标记
        text = text.replace('`', '')

        return text

    def send_report(
        self,
        papers: List[Dict],
        metadata: Optional[Dict] = None,
        formatter=None,
        report_file: str = None
    ) -> bool:
        """
        发送论文报告（支持完整文件推送或自动格式化）

        Args:
            papers: 论文列表
            metadata: 元数据（日期、主题等）
            formatter: 格式化器
            report_file: 报告文件路径（直接读取文件发送）

        Returns:
            是否发送成功
        """
        print("\n正在推送到飞书...")

        # 优先读取 report_file（完整内容）
        if report_file:
            return self._send_full_report(report_file)

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

    def _send_full_report(self, report_file: str) -> bool:
        """
        发送完整报告文件（支持自动分段）

        Args:
            report_file: 报告文件路径

        Returns:
            是否发送成功
        """
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 添加摘要预览
            content_with_preview = self._add_preview_header(content)

            # 检查消息大小
            message_size = len(content_with_preview.encode('utf-8'))
            print(f"📄 报告大小: {message_size} bytes ({message_size/1024:.2f} KB)")

            if message_size <= self.MAX_REQUEST_SIZE:
                # 单条消息发送
                return self.send(content_with_preview)
            else:
                # 分段发送
                print(f"📊 内容超过单条限制，进行分段处理...")
                return self._send_segmented(content_with_preview)

        except FileNotFoundError:
            print(f"⚠ 报告文件不存在: {report_file}")
            return False
        except Exception as e:
            print(f"⚠ 读取报告文件失败: {e}")
            return False

    def _add_preview_header(self, content: str) -> str:
        """
        添加摘要预览头部

        Args:
            content: 原始内容

        Returns:
            带有预览的内容
        """
        lines = content.split('\n')
        preview_lines = []

        # 提取预览信息（前 15 行）
        for i, line in enumerate(lines[:15]):
            if line.strip():
                preview_lines.append(line)

        # 构建预览头部
        preview_header = [
            "# 📅 AI 前沿论文日报",
            "\n",
            "> **提示**: 长按消息可查看完整内容，或访问 daily_report.md 文件",
            "\n",
            "---",
            "\n"
        ]

        return '\n'.join(preview_header + lines)

    def _send_segmented(self, content: str) -> bool:
        """
        分段发送长消息

        Args:
            content: 完整内容

        Returns:
            是否全部发送成功
        """
        lines = content.split('\n')
        segments = []
        current_segment = []
        current_size = 0

        # 按论文分界符分段
        for line in lines:
            line_size = len(line.encode('utf-8')) + 1  # +1 for newline

            # 检查是否达到分段边界
            if current_size + line_size > self.MAX_REQUEST_SIZE - 500:  # 预留 500 字节
                if current_segment:
                    segments.append('\n'.join(current_segment))
                    current_segment = []
                    current_size = 0

            current_segment.append(line)
            current_size += line_size

        # 添加最后一段
        if current_segment:
            segments.append('\n'.join(current_segment))

        print(f"📊 共分 {len(segments)} 段发送")

        # 依次发送各段
        all_success = True
        for i, segment in enumerate(segments, 1):
            print(f"\n[{i}/{len(segments)}] 发送第 {i} 段...")
            success = self.send(segment)
            if not success:
                all_success = False
                print(f"⚠ 第 {i} 段发送失败")

            # 非最后一段等待 1 秒
            if i < len(segments):
                time.sleep(1)

        if all_success:
            print("✅ 全部分段发送完成")
        else:
            print("⚠ 部分段落发送失败")

        return all_success

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
