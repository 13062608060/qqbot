"""把旧默认值(0)创建的好感度，迁移到新默认(50)。"""

import re
from pathlib import Path

ROOT = Path(r"D:\deepseek-work\qqbot\astrbot\data\大肥鱼好感度列表")
KEEP = {"1044846381"}  # 号主不迁移

for path in sorted(ROOT.glob("*.txt")):
    if path.stem in KEEP:
        continue
    text = path.read_text(encoding="utf-8")
    m = re.search(r"好感度:\s*(-?\d+)", text)
    if not m:
        continue
    score = int(m.group(1))
    if score < 50:
        text = re.sub(r"好感度:\s*-?\d+", f"好感度: 50", text, count=1)
        path.write_text(text, encoding="utf-8")
        print(f"{path.name}: {score} -> 50")
    else:
        print(f"{path.name}: {score} (保持)")
