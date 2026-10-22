"""End-to-end test: fake OneBot client -> AstrBot -> DeepSeek -> action reply.

Connects to the reverse-WS endpoint exactly like SnowLuma does, sends a private
message event, answers the resulting action requests, and prints the bot reply.
"""

import asyncio
import json
import sys
import time

import websockets

URL = "ws://127.0.0.1:6199/ws"
SELF_ID = 10001
USER_ID = 20002


def text_of(message) -> str:
    if isinstance(message, str):
        return message
    parts = []
    for seg in message or []:
        if seg.get("type") == "text":
            parts.append(seg.get("data", {}).get("text", ""))
        elif seg.get("type") == "image":
            parts.append("[图片]")
    return "".join(parts)


async def main() -> int:
    headers = {"X-Self-ID": str(SELF_ID), "X-Client-Role": "Universal"}
    async with websockets.connect(URL, additional_headers=headers, open_timeout=10, max_size=None) as ws:
        print(f"connected {URL}")
        await ws.send(json.dumps({
            "post_type": "meta_event",
            "meta_event_type": "lifecycle",
            "sub_type": "connect",
            "time": int(time.time()),
            "self_id": SELF_ID,
        }))

        event = {
            "post_type": "message",
            "message_type": "private",
            "sub_type": "friend",
            "message_id": 11,
            "user_id": USER_ID,
            "message": [{"type": "text", "data": {"text": "你好，一句话介绍下你自己"}}],
            "raw_message": "你好，一句话介绍下你自己",
            "font": 0,
            "sender": {"user_id": USER_ID, "nickname": "tester"},
            "time": int(time.time()),
            "self_id": SELF_ID,
        }
        await ws.send(json.dumps(event))
        print("sent private message event, waiting for bot action ...")

        deadline = time.time() + 90
        while time.time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=max(1, deadline - time.time()))
            except asyncio.TimeoutError:
                break
            try:
                payload = json.loads(raw)
            except Exception:
                print("non-json:", raw[:200])
                continue

            if "action" in payload:
                action = payload["action"]
                echo = payload.get("echo")
                params = payload.get("params", {})
                if "message" in params:
                    print(f"ACTION {action} -> {text_of(params.get('message'))!r}")
                else:
                    print(f"ACTION {action} params={str(params)[:120]}")
                await ws.send(json.dumps({"status": "ok", "retcode": 0, "data": {"message_id": 99}, "echo": echo}))
                if action in ("send_private_msg", "send_msg"):
                    print("BOT REPLY RECEIVED")
                    return 0
            else:
                print("event:", payload.get("post_type"), payload.get("message_type", ""))
        print("timeout: no bot reply")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
