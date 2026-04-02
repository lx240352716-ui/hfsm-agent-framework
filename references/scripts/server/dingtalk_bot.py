# -*- coding: utf-8 -*-
"""
钉钉机器人 v2 — AsyncChatbotHandler + HFSM Controller。

基于 dingtalk_stream.AsyncChatbotHandler：
- process() 是同步方法，SDK 自动在 ThreadPoolExecutor 中执行
- raw_process() 立即返回 ACK，不阻塞 WebSocket
"""

import os
import sys
import json
import logging

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, '..', 'core'))

from llm_client import _load_env
_load_env()

import dingtalk_stream
from dingtalk_stream import AckMessage, ChatbotMessage

logger = logging.getLogger('dingtalk_bot')


class HFSMBotHandler(dingtalk_stream.AsyncChatbotHandler):
    """HFSM 机器人消息处理器。

    继承 AsyncChatbotHandler:
    - process() 同步方法（不要 async）
    - SDK 自动放进线程池执行
    - raw_process() 立即返回 ACK
    """

    def __init__(self):
        super().__init__(max_workers=4)
        self._webhooks = {}

    def process(self, callback: dingtalk_stream.CallbackMessage):
        """处理消息（同步，SDK 在线程池中调用此方法）。"""
        from hfsm_controller import get_controller, reset_controller

        try:
            # 解析消息
            data = callback.data if isinstance(callback.data, dict) else json.loads(callback.data)
            incoming = ChatbotMessage.from_dict(data)
            text = ''
            if incoming.text:
                text = incoming.text.content.strip() if incoming.text.content else ''

            sender_id = incoming.sender_staff_id or 'unknown'

            if not text:
                return AckMessage.STATUS_OK, 'OK'

            # 保存 incoming_message 用于回复
            self._webhooks[sender_id] = incoming

            logger.info(f"收到消息: [{sender_id}] {text}")

            # ── 特殊命令 ──
            if text.lower() in ['/reset', '重置', '清除']:
                reset_controller(sender_id)
                self.reply_text("🔄 会话已重置，请发送新需求。", incoming)
                return AckMessage.STATUS_OK, 'OK'

            if text.lower() in ['/status', '状态']:
                ctrl = get_controller(sender_id, self._make_reply_callback(incoming))
                status = ctrl.get_status()
                self.reply_text(
                    f"📊 状态: {status['status']}\n"
                    f"Agent: {status['agent']}\n"
                    f"步骤: {status['state']}\n"
                    f"等待输入: {'是' if status['waiting'] else '否'}",
                    incoming,
                )
                return AckMessage.STATUS_OK, 'OK'

            # ── 业务消息 ──
            reply_cb = self._make_reply_callback(incoming)
            ctrl = get_controller(sender_id, reply_cb)

            if ctrl.status.value == 'waiting_user':
                ctrl.resume(text)
            elif ctrl.status.value in ('idle', 'completed', 'error'):
                ctrl.submit(text)
            else:
                self.reply_text(
                    "⏳ 上一个任务还在执行中...\n发 /reset 可重置。",
                    incoming,
                )

            return AckMessage.STATUS_OK, 'OK'

        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
            return AckMessage.STATUS_OK, 'OK'

    def _make_reply_callback(self, incoming: ChatbotMessage):
        """创建 HFSM Controller 的回调函数。"""
        handler = self

        def reply_callback(user_id, message, card_data=None):
            """HFSM Controller 调用此函数发送消息。"""
            # 获取最新 incoming_message
            msg_obj = handler._webhooks.get(user_id, incoming)

            if card_data and card_data.get('buttons'):
                title = card_data.get('title', '请确认')
                handler.reply_markdown(title, message, msg_obj)
            else:
                # 超长分段
                if len(message) > 4000:
                    chunks = [message[i:i+4000]
                              for i in range(0, len(message), 4000)]
                    for chunk in chunks:
                        handler.reply_text(chunk, msg_obj)
                else:
                    handler.reply_text(message, msg_obj)

        return reply_callback


def start_bot():
    """启动钉钉机器人。"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    )

    app_key = os.environ.get('DINGTALK_APP_KEY', '')
    app_secret = os.environ.get('DINGTALK_APP_SECRET', '')

    if not app_key or not app_secret:
        print("❌ 请在 .env 中设置 DINGTALK_APP_KEY 和 DINGTALK_APP_SECRET")
        sys.exit(1)

    logger.info(f"🚀 钉钉机器人启动 (AppKey: {app_key[:8]}...)")

    credential = dingtalk_stream.Credential(app_key, app_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    client.register_callback_handler(
        ChatbotMessage.TOPIC,
        HFSMBotHandler(),
    )

    logger.info("✅ 连接钉钉服务器...")
    client.start_forever()


if __name__ == '__main__':
    start_bot()
