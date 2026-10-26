"""Probe SnowLuma's OneBot API: what actions exist, and what history looks like."""

import asyncio
import json
import sys

import websockets

URL = "ws://127.0.0.1:3001/"
TARGET = 2306680581


async def main() -> int:
    async with websockets.connect(URL, open_timeout=10, max_size=None) as ws:
        echo = 0

        async def call(action: str, **params):
            nonlocal echo
            echo += 1
            await ws.send(json.dumps({"action": action, "params": params, "echo": echo}))
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=30)
                try:
                    data = json.loads(raw)
                except Exception:
                    continue
                if data.get("echo") == echo:
                    return data

        for action in ("get_version_info", "get_login_info"):
            resp = await call(action)
            print(action, "->", json.dumps(resp, ensure_ascii=False)[:300])

        for params in (
            {"user_id": TARGET, "count": 20},
            {"user_id": TARGET, "count": 20, "message_seq": 0},
        ):
            try:
                resp = await call("get_friend_msg_history", **params)
                print("get_friend_msg_history", params, "-> status=", resp.get("status"),
                      "retcode=", resp.get("retcode"))
                body = resp.get("data")
                if body:
                    msgs = body.get("messages") if isinstance(body, dict) else body
                    print("  消息数:", len(msgs) if isinstance(msgs, list) else type(msgs))
                    if isinstance(msgs, list) and msgs:
                        print("  样例:", json.dumps(msgs[0], ensure_ascii=False)[:500])
                    break
                else:
                    print("  data 为空:", json.dumps(resp, ensure_ascii=False)[:200])
            except Exception as exc:  # noqa: BLE001
                print("get_friend_msg_history 失败:", exc)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
