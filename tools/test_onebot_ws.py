"""Smoke-test AstrBot's OneBot v11 reverse-WS endpoint (as a fake SnowLuma client)."""

import asyncio
import json
import sys
import time

import websockets

URL = "ws://127.0.0.1:6199/ws"
SELF_ID = 10001


async def main() -> int:
    headers = {
        "X-Self-ID": str(SELF_ID),
        "X-Client-Role": "Universal",
        "User-Agent": "OneBot/11 smoke-test",
    }
    try:
        async with websockets.connect(URL, additional_headers=headers, open_timeout=10) as ws:
            print(f"connected: {URL}")
            event = {
                "post_type": "meta_event",
                "meta_event_type": "lifecycle",
                "sub_type": "connect",
                "time": int(time.time()),
                "self_id": SELF_ID,
            }
            await ws.send(json.dumps(event))
            print(f"sent lifecycle meta_event: {event}")
            try:
                reply = await asyncio.wait_for(ws.recv(), timeout=5)
                print(f"reply: {reply[:400]}")
            except asyncio.TimeoutError:
                print("no reply within 5s (normal for a pure event report)")
            await asyncio.sleep(1)
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED: {type(exc).__name__}: {exc}")
        return 1
    print("OK: handshake accepted")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
