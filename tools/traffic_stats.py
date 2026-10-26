from collections import Counter
from pathlib import Path

p = Path(r"D:\deepseek-work\qqbot\astrbot\data\logs\astrbot.log")
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

incoming = Counter()
replies = Counter()
for l in lines:
    if "16:" not in l and "15:" not in l:
        continue
    if "[qq-onebot(aiocqhttp)]" in l and "event_bus" in l:
        incoming["events"] += 1
    if "Prepare to send" in l:
        replies["sent"] += 1

print("近两小时 事件:", incoming["events"], "| 发出:", replies["sent"])

# 按小时
per = Counter()
sent = Counter()
for l in lines:
    if "[qq-onebot(aiocqhttp)]" in l and "event_bus" in l:
        per[l[12:17]] += 1
    if "Prepare to send" in l:
        sent[l[12:17]] += 1
print("按分钟段（前20）:")
for k in sorted(per)[-12:]:
    print(f"  {k}: 事件 {per[k]:3d}  回复 {sent[k]:2d}")
