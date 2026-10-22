"""尝试还原被 GBK/UTF-8 双重编码破坏的源码。"""

from pathlib import Path

SRC = Path(r"D:\deepseek-work\qqbot\astrbot\data\plugins\astrbot_plugin_budget_guard\main.py")
OUT = SRC.with_suffix(".recovered.py")

raw = SRC.read_text(encoding="utf-8", errors="replace")
try:
    gbk_bytes = raw.encode("gbk")
    mode = "strict"
except UnicodeEncodeError:
    gbk_bytes = raw.encode("gbk", errors="replace")
    mode = "replace"

try:
    fixed = gbk_bytes.decode("utf-8", errors="replace")
    print("decode ok")
except Exception as exc:  # noqa: BLE001
    fixed = raw
    print("decode failed:", exc)

OUT.write_text(fixed, encoding="utf-8")
print("gbk mode:", mode, "| 输出:", OUT)
print("前 5 行：")
print("\n".join(fixed.splitlines()[:5]))
print("坏字符数(?):", fixed.count("\ufffd"))
