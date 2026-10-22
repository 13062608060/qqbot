"""Exercise the budget plugin: /budget, a normal message, then /budget again."""

import asyncio
import json
import sys
import time

import websockets

URL = "ws://127.0.0.1:6199/ws"
SELF_ID = 10001
USER_ID = 20002

STEPS = ["/budget", "你好，随便聊两句", "/budget"]


def text_of(message) -> str:
    if isinstance(message, str):
        return message
    return "".join(
        seg.get("data", {}).get("text", "")
        for seg in (message or [])
        if seg.get("type") == "text"
    )


async def main() -> int:
    headers = {"X-Self-ID": str(SELF_ID), "X-Client-Role": "Universal"}
    async with websockets.connect(URL, additional_headers=headers, open_timeout=10, max_size=None) as ws:
        await ws.send(json.dumps({
            "post_type": "meta_event", "meta_event_type": "lifecycle",
            "sub_type": "connect", "time": int(time.time()), "self_id": SELF_ID,
        }))
        await asyncio.sleep(1)

        for idx, prompt in enumerate(STEPS, start=1):
            await ws.send(json.dumps({
                "post_type": "message", "message_type": "private", "sub_type": "friend",
                "message_id": 200 + idx, "user_id": USER_ID,
                "message": [{"type": "text", "data": {"text": prompt}}],
                "raw_message": prompt, "font": 0,
                "sender": {"user_id": USER_ID, "nickname": "tester"},
                "time": int(time.time()), "self_id": SELF_ID,
            }))
            print(f"\n>>> {prompt}")

            deadline = time.time() + 45
            got = False
            while time.time() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=max(1, deadline - time.time()))
                except asyncio.TimeoutError:
                    break
                payload = json.loads(raw)
                if "action" in payload:
                    params = payload.get("params", {})
                    await ws.send(json.dumps({
                        "status": "ok", "retcode": 0, "data": {"message_id": 999}, "echo": payload.get("echo"),
                    }))
                    if "message" in params:
                        print(f"<<< {text_of(params['message'])}")
                        got = True
                        break
            if not got:
                print("<<< （没有回复）")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
