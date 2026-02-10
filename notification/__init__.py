"""通知模块 - 负责将日报推送到各平台"""

from .wechat import WeChatNotifier
from .feishu import FeishuNotifier

__all__ = ['WeChatNotifier', 'FeishuNotifier']
