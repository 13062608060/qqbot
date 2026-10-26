"""清理记忆库：去掉回填时混进来的碎话和脏话。"""

import re
from pathlib import Path

MEM = Path(r"D:\deepseek-work\qqbot\astrbot\data\大肥鱼记忆\global.txt")
NOISE = ("他妈", "卧槽", "操", "傻", "滚", "爆了", "草")
KEEP_MIN = 12

lines = MEM.read_text(encoding="utf-8").splitlines()
kept, dropped = [], 0
for line in lines:
    if "| 鱼籽公主吖 |" not in line:
        kept.append(line)
        continue
    content = line.split("|", 2)[-1].strip()
    if len(content) < KEEP_MIN or any(w in content for w in NOISE):
        dropped += 1
        continue
    kept.append(line)

MEM.write_text("\n".join(kept) + "\n", encoding="utf-8")
print(f"删除 {dropped} 条，保留 {len(kept)} 行")
print("\n".join(kept[-5:]))
