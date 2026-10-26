from pathlib import Path

p = Path(r"D:\deepseek-work\qqbot\astrbot\data\logs\astrbot.log")
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
hits = [l for l in lines if "sticker" in l.lower()]
print("\n".join(h[:170] for h in hits[-8:]))
