# -*- coding: utf-8 -*-
"""
HFSM Agent Server — FastAPI 入口。

支持两种模式：
1. 钉钉机器人模式：python -m server.app --dingtalk
2. HTTP API 模式：  python -m server.app --http

HTTP API 可用于调试或对接其他 IM 平台。
"""

import os
import sys
import argparse
import logging

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, '..', 'core'))

from llm_client import _load_env

_load_env()


def start_http_server(host='0.0.0.0', port=8000):
    """启动 HTTP API 服务（用于调试或对接其他平台）。"""
    try:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel
        import uvicorn
    except ImportError:
        print("❌ 请安装 fastapi + uvicorn:")
        print("   pip install fastapi uvicorn")
        sys.exit(1)

    app = FastAPI(title="HFSM Agent Server", version="2.0")

    class MessageRequest(BaseModel):
        user_id: str
        message: str

    # HTTP 模式的回复存储（调试用）
    _http_replies = {}  # user_id → [messages]

    def _http_reply(user_id, message, card_data=None):
        if user_id not in _http_replies:
            _http_replies[user_id] = []
        _http_replies[user_id].append({
            "message": message,
            "card": card_data,
        })

    @app.post("/chat")
    async def chat(req: MessageRequest):
        """提交需求（非阻塞，后台执行）。"""
        from hfsm_controller import get_controller
        _http_replies[req.user_id] = []
        ctrl = get_controller(req.user_id, _http_reply)
        ctrl.submit(req.message)
        # 等一下让后台线程开始
        import asyncio
        await asyncio.sleep(0.5)
        return JSONResponse({
            "status": "submitted",
            "controller": ctrl.get_status(),
        })

    @app.post("/resume")
    async def resume(req: MessageRequest):
        """用户确认/输入后恢复执行。"""
        from hfsm_controller import get_controller
        ctrl = get_controller(req.user_id, _http_reply)
        ctrl.resume(req.message)
        import asyncio
        await asyncio.sleep(0.5)
        return JSONResponse({
            "status": "resumed",
            "controller": ctrl.get_status(),
        })

    @app.get("/replies/{user_id}")
    async def get_replies(user_id: str):
        """获取后台执行产生的回复（轮询）。"""
        replies = _http_replies.pop(user_id, [])
        from hfsm_controller import get_controller
        ctrl = get_controller(user_id)
        return JSONResponse({
            "replies": replies,
            "controller": ctrl.get_status(),
        })

    @app.post("/reset")
    async def reset(req: MessageRequest):
        """重置用户会话。"""
        from hfsm_controller import reset_controller
        reset_controller(req.user_id)
        return JSONResponse({"message": "会话已重置"})

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "2.0"}

    print(f"🚀 HFSM HTTP Server 启动: http://{host}:{port}")
    print(f"📖 API 文档: http://{host}:{port}/docs")
    uvicorn.run(app, host=host, port=port)


def start_dingtalk():
    """启动钉钉机器人模式。"""
    from dingtalk_bot import start_bot
    start_bot()


def main():
    parser = argparse.ArgumentParser(description='HFSM Agent Server')
    parser.add_argument('--dingtalk', action='store_true',
                        help='启动钉钉机器人模式')
    parser.add_argument('--http', action='store_true',
                        help='启动 HTTP API 模式')
    parser.add_argument('--host', default='0.0.0.0',
                        help='HTTP 监听地址 (默认 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000,
                        help='HTTP 端口 (默认 8000)')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    )

    if args.dingtalk:
        start_dingtalk()
    elif args.http:
        start_http_server(args.host, args.port)
    else:
        # 默认同时启动 HTTP（方便调试）
        print("用法:")
        print("  python app.py --dingtalk   启动钉钉机器人")
        print("  python app.py --http       启动 HTTP API（调试用）")
        print()
        print("默认启动 HTTP 模式...")
        start_http_server(args.host, args.port)


if __name__ == '__main__':
    main()
