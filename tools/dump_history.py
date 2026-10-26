"""从 SnowLuma 的 OneBot 接口读取主号与指定好友的聊天记录，统计表情与说话样本。"""

import asyncio
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import websockets

URL = "ws://127.0.0.1:3002/"
TARGETS = [2306680581, 3392926635, 3154331493, 1076717418]
SELF = 1044846381
OUT = Path(r"D:\deepseek-work\qqbot\data\history_dump.json")
LIMIT = 1000


async def main() -> int:
    result = {"login": None, "chats": {}}
    async with websockets.connect(URL, open_timeout=10, max_size=None) as ws:
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

        login = await call("get_login_info")
        result["login"] = login.get("data")
        print("当前账号:", json.dumps(login.get("data"), ensure_ascii=False))

        for uid in TARGETS:
            resp = await call("get_friend_msg_history", user_id=uid, count=LIMIT)
            data = resp.get("data") or {}
            msgs = data.get("messages") if isinstance(data, dict) else None
            info = {"status": resp.get("status"), "wording": resp.get("wording"), "count": 0}
            if msgs:
                info["count"] = len(msgs)
                result["chats"][str(uid)] = msgs
            else:
                info["wording"] = info["wording"] or "无数据"
            print(uid, "->", info)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    print("已保存:", OUT)

    # 统计
    seg_types = Counter()
    my_texts = []
    my_stickers = Counter()
    for uid, msgs in result["chats"].items():
        for m in msgs:
            sender = m.get("user_id") or (m.get("sender") or {}).get("user_id")
            for seg in m.get("message") or []:
                t = seg.get("type")
                seg_types[t] += 1
                if sender == SELF and t in ("mface", "face", "image"):
                    data = seg.get("data") or {}
                    key = data.get("emoji_id") or data.get("emoticon_id") or data.get("id") or data.get("file") or "?"
                    my_stickers[(t, str(key)[:40])] += 1
                if sender == SELF and t == "text":
                    txt = (seg.get("data") or {}).get("text") or ""
                    if txt.strip():
                        my_texts.append(txt.strip())

    print("\n消息段类型:", dict(seg_types))
    print("我发的表情种类:", len(my_stickers), "次数:", sum(my_stickers.values()))
    for (t, k), c in my_stickers.most_common(15):
        print(f"   {t:6} {k:42} ×{c}")
    print("\n我发的文字条数:", len(my_texts))
    for t in my_texts[:25]:
        print("   ", t[:60])
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
