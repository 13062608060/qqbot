from pathlib import Path

p = Path(r"D:\deepseek-work\qqbot\astrbot\data\logs\astrbot.log")
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
idx = [i for i, l in enumerate(lines) if "11:47:3" in l]
start = max(0, (idx[0] if idx else len(lines)) - 6)
print("\n".join(l[:200] for l in lines[start : start + 25]))
