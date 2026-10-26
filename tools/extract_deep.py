"""深挖：用 message_id 锚点翻页，尽量多取四个人的历史。"""

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

import websockets

WS = "ws://127.0.0.1:3002/"
TARGETS = [2306680581, 3392926635, 3154331493, 1076717418]
SELF = 1044846381
PAGE = 100
MAX_PAGES = 12
OUT = Path(r"D:\deepseek-work\qqbot\data\history_deep.json")
SAMPLES = Path(r"D:\deepseek-work\qqbot\data\my_messages_deep.txt")
STICKERS = Path(r"D:\deepseek-work\qqbot\data\stickers_deep.json")


async def fetch_chat(ws, uid: int) -> dict:
    echo = 0

    async def call(action, **params):
        nonlocal echo
        echo += 1
        await ws.send(json.dumps({"action": action, "params": params, "echo": echo}))
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=60)
            try:
                data = json.loads(raw)
            except Exception:
                continue
            if data.get("echo") == echo:
                return data

    collected: dict = {}
    anchor = None
    for page in range(MAX_PAGES):
        params = {"user_id": uid, "count": PAGE}
        if anchor is not None:
            params["message_id"] = anchor
        resp = await call("get_friend_msg_history", **params)
        msgs = (resp.get("data") or {}).get("messages") or []
        new = 0
        for m in msgs:
            mid = m.get("message_id")
            if mid not in collected:
                collected[mid] = m
                new += 1
        if not msgs or new == 0:
            break
        oldest = min(msgs, key=lambda x: x.get("time") or 0)
        anchor = oldest.get("message_id")
        if anchor is None:
            break
    return collected


async def main() -> int:
    out = {"chats": {}}
    async with websockets.connect(WS, open_timeout=10, max_size=None) as ws:
        for uid in TARGETS:
            try:
                chats = await fetch_chat(ws, uid)
            except Exception as exc:  # noqa: BLE001
                print(uid, "失败:", exc)
                chats = {}
            out["chats"][str(uid)] = list(chats.values())
            print(f"{uid}: {len(chats)} 条")

    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")

    mine, theirs = [], []
    stickers = Counter()
    sticker_data = {}
    for uid, msgs in out["chats"].items():
        for m in msgs:
            sender = m.get("user_id")
            for seg in m.get("message") or []:
                t = seg.get("type")
                data = seg.get("data") or {}
                if t == "text":
                    txt = (data.get("text") or "").strip()
                    if txt:
                        (mine if sender == SELF else theirs).append(txt)
                elif t in ("mface", "face", "image") and sender == SELF:
                    key = data.get("emoji_id") or data.get("emoticon_id") or data.get("id") or data.get("file") or (data.get("url") or "")[-40:]
                    stickers[(t, str(key))] += 1
                    sticker_data.setdefault((t, str(key)), data)

    SAMPLES.write_text("\n".join(mine), encoding="utf-8")
    STICKERS.write_text(
        json.dumps(
            {"counter": {f"{t}|{k}": c for (t, k), c in stickers.items()},
             "samples": {f"{t}|{k}": v for (t, k), v in sticker_data.items()}},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    print(f"我的文字 {len(mine)} 条 | 对方文字 {len(theirs)} 条 | 我的表情 {len(stickers)} 种")
    print("样本:", SAMPLES)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
