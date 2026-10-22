"""Group message WITH an @ (creates the group conversation), used to test chime-in."""

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


async def run(group_id: int, user_id: int, text: str, mention: bool) -> int:
    headers = {"X-Self-ID": str(SELF_ID), "X-Client-Role": "Universal"}
    chain = []
    if mention:
        chain.append({"type": "at", "data": {"qq": str(SELF_ID)}})
    chain.append({"type": "text", "data": {"text": text}})
    async with websockets.connect(URL, additional_headers=headers, open_timeout=10, max_size=None) as ws:
        await ws.send(json.dumps({
            "post_type": "meta_event", "meta_event_type": "lifecycle",
            "sub_type": "connect", "time": int(time.time()), "self_id": SELF_ID,
        }))
        await asyncio.sleep(1)
        await ws.send(json.dumps({
            "post_type": "message", "message_type": "group", "sub_type": "normal",
            "message_id": int(time.time()) % 100000, "group_id": group_id, "user_id": user_id,
            "message": chain, "raw_message": text, "font": 0,
            "sender": {"user_id": user_id, "nickname": f"u{user_id}", "card": ""},
            "time": int(time.time()), "self_id": SELF_ID,
        }))
        deadline = time.time() + 45
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
                print(f"群 {group_id} {'@' if mention else '无@'} <<< {text_of(payload['params']['message'])}")
                return 0
        print(f"群 {group_id} {'@' if mention else '无@'} <<< （没有回复）")
        return 1


if __name__ == "__main__":
    mention = "--at" in sys.argv
    argv = [a for a in sys.argv[1:] if a != "--at"]
    sys.exit(asyncio.run(run(int(argv[0]), int(argv[1]), argv[2], mention)))
