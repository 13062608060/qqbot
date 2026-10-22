"""Send one private message to the bot as a given QQ number and print the reply.

Usage:
    python tools\\send_as.py 20002 "你今天还剩多少额度"
"""

import asyncio
import json
import sys
import time

import websockets

URL = "ws://127.0.0.1:6199/ws"
SELF_ID = 10001


def text_of(message) -> str:
    if isinstance(message, str):
        return message
    return "".join(
        seg.get("data", {}).get("text", "")
        for seg in (message or [])
        if seg.get("type") == "text"
    )


async def run(user_id: int, text: str) -> int:
    headers = {"X-Self-ID": str(SELF_ID), "X-Client-Role": "Universal"}
    async with websockets.connect(URL, additional_headers=headers, open_timeout=10, max_size=None) as ws:
        await ws.send(json.dumps({
            "post_type": "meta_event", "meta_event_type": "lifecycle",
            "sub_type": "connect", "time": int(time.time()), "self_id": SELF_ID,
        }))
        await asyncio.sleep(1)
        await ws.send(json.dumps({
            "post_type": "message", "message_type": "private", "sub_type": "friend",
            "message_id": int(time.time()) % 100000, "user_id": user_id,
            "message": [{"type": "text", "data": {"text": text}}],
            "raw_message": text, "font": 0,
            "sender": {"user_id": user_id, "nickname": f"u{user_id}"},
            "time": int(time.time()), "self_id": SELF_ID,
        }))
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=max(1, deadline - time.time()))
            except asyncio.TimeoutError:
                break
            payload = json.loads(raw)
            if "action" in payload and "message" in payload.get("params", {}):
                await ws.send(json.dumps({
                    "status": "ok", "retcode": 0, "data": {"message_id": 999}, "echo": payload.get("echo"),
                }))
                print(f"u{user_id} <<< {text_of(payload['params']['message'])}")
                return 0
        print(f"u{user_id} <<< （没有回复）")
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(asyncio.run(run(int(sys.argv[1]), sys.argv[2])))
