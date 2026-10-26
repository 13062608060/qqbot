"""抓取主号与四个好友最近约 1000 条聊天，统计表情与我的说话样本。"""

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
PAGES = 10
OUT = Path(r"D:\deepseek-work\qqbot\data\history_dump.json")
SAMPLES = Path(r"D:\deepseek-work\qqbot\data\my_messages.txt")


async def fetch_chat(ws, uid: int) -> list:
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
    seq = None
    for _ in range(PAGES):
        params = {"user_id": uid, "count": PAGE}
        if seq is not None:
            params["message_seq"] = seq
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
        seqs = [m.get("message_seq") for m in msgs if m.get("message_seq") is not None]
        if not seqs:
            break
        seq = min(seqs)
        if resp.get("status") != "ok":
            break
    return list(collected.values())


async def main() -> int:
    out = {"chats": {}}
    async with websockets.connect(WS, open_timeout=10, max_size=None) as ws:
        for uid in TARGETS:
            try:
                msgs = await fetch_chat(ws, uid)
            except Exception as exc:  # noqa: BLE001
                print(uid, "抓取失败:", exc)
                msgs = []
            out["chats"][str(uid)] = msgs
            print(f"{uid}: {len(msgs)} 条")

    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")

    mine, theirs = [], []
    sticker_counter = Counter()
    sticker_samples = {}
    seg_types = Counter()

    for uid, msgs in out["chats"].items():
        for m in msgs:
            sender = m.get("user_id")
            for seg in m.get("message") or []:
                t = seg.get("type")
                seg_types[t] = seg_types.get(t, 0) + 1
                data = seg.get("data") or {}
                if t == "text":
                    txt = (data.get("text") or "").strip()
                    if txt:
                        (mine if sender == SELF else theirs).append(txt)
                elif t in ("mface", "face", "image"):
                    if sender == SELF:
                        key = data.get("emoji_id") or data.get("emoticon_id") or data.get("id") or data.get("file") or data.get("url", "")[-40:]
                        sticker_counter[(t, str(key))] += 1
                        sticker_samples.setdefault((t, str(key)), data)

    print("\n消息段分布:", dict(seg_types))
    print("我发文字:", len(mine), "| 对方文字:", len(theirs))
    print("我的表情种类:", len(sticker_counter), "总次数:", sum(sticker_counter.values()))

    SAMPLES.write_text("\n".join(mine), encoding="utf-8")
    print("我的原话已存:", SAMPLES)

    print("\n我的表情 TOP20：")
    for (t, k), c in sticker_counter.most_common(20):
        print(f"  {t:6} {k[:50]:50} ×{c}")
        print("         ", json.dumps(sticker_samples[(t, k)], ensure_ascii=False)[:160])

    Path(r"D:\deepseek-work\qqbot\data\stickers.json").write_text(
        json.dumps(
            {"counter": {f"{t}|{k}": c for (t, k), c in sticker_counter.items()},
             "samples": {f"{t}|{k}": v for (t, k), v in sticker_samples.items()}},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
