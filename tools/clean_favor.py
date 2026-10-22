"""清理好感度存档：删掉测试号，压缩事件到"有分量 + 最近 20 条"。"""

import re
import sys
from pathlib import Path

ROOT = Path(r"D:\deepseek-work\qqbot\astrbot\data\大肥鱼好感度列表")
TEST_IDS = {"20002", "30003", "40004"}
EVENT_RE = re.compile(r"\(([+-]\d+)\)\s*$")

for path in sorted(ROOT.glob("*.txt")):
    qq = path.stem
    if qq in TEST_IDS:
        path.unlink()
        print(f"deleted {path.name} (测试号)")
        continue

    lines = path.read_text(encoding="utf-8").splitlines()
    head, events, in_events = [], [], False
    for line in lines:
        if line.startswith("事件:"):
            in_events = True
            head.append(line)
            continue
        if in_events and line.startswith("-"):
            m = EVENT_RE.search(line)
            if m and abs(int(m.group(1))) >= 2:
                events.append(line)
        elif not in_events:
            head.append(line)

    events = events[-20:]
    out = "\n".join(head + events) + "\n"
    path.write_text(out, encoding="utf-8")
    print(f"{path.name}: 保留事件 {len(events)} 条")
