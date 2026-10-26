"""下载聊天记录里我发过的表情图，存进表情包目录。"""

import json
import urllib.request
from pathlib import Path

DATA = Path(r"D:\deepseek-work\qqbot\data\stickers.json")
DST = Path(r"D:\deepseek-work\qqbot\astrbot\data\表情包")
DST.mkdir(parents=True, exist_ok=True)

payload = json.loads(DATA.read_text(encoding="utf-8"))
samples = payload.get("samples", {})

ok = 0
for key, data in samples.items():
    kind, ident = key.split("|", 1)
    if kind != "image":
        continue
    url = data.get("url")
    if not url:
        continue
    name = ident if ident.endswith(".png") else f"me_{ok:02d}.png"
    target = DST / f"me_{ok:02d}_{name}"[:60]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            target.write_bytes(resp.read())
        ok += 1
        print("ok", target.name, target.stat().st_size, "bytes")
    except Exception as exc:  # noqa: BLE001
        print("fail", url[:60], exc)

print("下载成功:", ok)
