from pathlib import Path

p = Path(r"D:\deepseek-work\qqbot\astrbot\data\logs\astrbot.log")
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

idx = [i for i, l in enumerate(lines) if "At:2443400384" in l or "@2443400384" in l]
print("被@次数:", len(idx))
for i in idx[-8:]:
    print("---", lines[i][:150])
    for j in range(i, min(i + 6, len(lines))):
        if "Prepare to send" in lines[j] or "budget" in lines[j]:
            print("    ->", lines[j][:150])
