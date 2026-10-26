"""把 3392926635 说过的重要的话回填进记忆库，并下载我的表情图。"""

import json
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\deepseek-work\qqbot")
HIST = ROOT / "data" / "history_deep.json"
MEM = ROOT / "astrbot" / "data" / "大肥鱼记忆" / "global.txt"
STK = ROOT / "data" / "stickers_deep.json"
DST = ROOT / "astrbot" / "data" / "表情包"

TARGET = "3392926635"
KEYWORDS = ("约定", "计划", "下周", "明天", "生日", "考试", "面试", "医院", "生病", "加班",
            "搬家", "旅行", "喜欢", "讨厌", "难受", "难过", "开心", "记得", "工作", "上班",
            "学校", "课", "钱", "爸", "妈", "家", "朋友", "感觉")

data = json.loads(HIST.read_text(encoding="utf-8"))
msgs = data["chats"].get(TARGET, [])

rows = []
for m in msgs:
    if str(m.get("user_id")) == "1044846381":
        continue
    for seg in m.get("message") or []:
        if seg.get("type") != "text":
            continue
        txt = (seg.get("data") or {}).get("text", "").strip()
        if not txt:
            continue
        meaningful = len(txt) >= 12 or any(k in txt for k in KEYWORDS)
        if meaningful:
            ts = m.get("time")
            when = datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "未知日期"
            rows.append((when, txt[:160]))

# 去重 + 只留最近 60 条
seen, uniq = set(), []
for when, txt in reversed(rows):
    if txt in seen:
        continue
    seen.add(txt)
    uniq.append((when, txt))
uniq = uniq[:60]

MEM.parent.mkdir(parents=True, exist_ok=True)
existing = MEM.read_text(encoding="utf-8").splitlines() if MEM.exists() else []
added = 0
for when, txt in reversed(uniq):
    line = f"{when} 12:00 | 鱼籽公主吖 | {txt}"
    if any(txt in e for e in existing):
        continue
    existing.append(line)
    added += 1

MEM.write_text("\n".join(existing[-500:]) + "\n", encoding="utf-8")
print(f"回填记忆 {added} 条（候选 {len(rows)} 条，去重后 {len(uniq)} 条）")

# 下载表情
stickers = json.loads(STK.read_text(encoding="utf-8"))["samples"]
ok = 0
for key, datas in stickers.items():
    kind, ident = key.split("|", 1)
    if kind != "image":
        continue
    url = datas.get("url")
    if not url:
        continue
    name = ident if ident.lower().endswith((".png", ".jpg", ".gif")) else f"deep_{ok:03d}.png"
    target = DST / (f"deep_{ok:03d}_" + name)[:70]
    if target.exists():
        ok += 1
        continue
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            target.write_bytes(resp.read())
        ok += 1
    except Exception as exc:  # noqa: BLE001
        print("下载失败", url[:50], exc)

print("表情下载/已存在:", ok)
print("表情包总数:", len(list(DST.glob('*'))))
