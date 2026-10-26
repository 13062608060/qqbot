"""按「回合」聚合消息（同一个人连续发、间隔短），再抽她→我的问答对。"""

import json
from pathlib import Path

HIST = Path(r"D:\deepseek-work\qqbot\data\history_deep.json")
TARGET = "3392926635"
SELF = 1044846381
GAP = 180  # 同一人连续发言合并的间隔（秒）

data = json.loads(HIST.read_text(encoding="utf-8"))
msgs = sorted(data["chats"].get(TARGET, []), key=lambda m: m.get("time") or 0)


def text_of(m):
    return "".join(
        (seg.get("data") or {}).get("text", "")
        for seg in (m.get("message") or [])
        if seg.get("type") == "text"
    ).strip()


turns = []  # (sender, text, start_time)
for m in msgs:
    sender = str(m.get("user_id"))
    txt = text_of(m)
    ts = m.get("time") or 0
    if not txt:
        continue
    if turns and turns[-1][0] == sender and ts - turns[-1][2] <= GAP:
        turns[-1][1] += txt
        turns[-1][2] = ts
    else:
        turns.append([sender, txt, ts])

pairs = []
for i in range(len(turns) - 1):
    if turns[i][0] == str(SELF) and turns[i + 1][0] == str(SELF):
        continue
    if turns[i][0] != str(SELF) and turns[i + 1][0] == str(SELF):
        q, a = turns[i][1], turns[i + 1][1]
        if q and a:
            pairs.append((q, a))

print("回合数:", len(turns), "| 问答对:", len(pairs))
short = [p for p in pairs if len(p[1]) <= 10]
print("短答对:", len(short), "\n")
for q, a in short[:35]:
    print(f"  她：{q[:24]:<26} → 我：{a}")

Path(r"D:\deepseek-work\qqbot\data\qa_pairs.json").write_text(
    json.dumps([{"q": q, "a": a} for q, a in pairs], ensure_ascii=False, indent=1),
    encoding="utf-8",
)
