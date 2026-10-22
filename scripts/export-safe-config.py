#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从真实的 astrbot\\data\\cmd_config.json 生成可安全提交的 cmd_config.example.json。

真实配置里有 DeepSeek API Key 和控制台密码，绝不能进仓库；但配置项本身（人设、
模型参数、白名单、T2I 模板等）又很值得版本化。所以这里做一次「脱敏导出」：

    sk-xxxx...                 -> sk-REPLACE_WITH_YOUR_KEY
    键名含 api_key/password/
    token/secret 的非空字符串   -> <REDACTED>

用法（在本目录执行）：
    ..\\runtime\\python\\cpython-3.12.15-windows-x86_64-none\\python.exe scripts\\export-safe-config.py

之后把 astrbot\\data\\cmd_config.example.json 一起提交即可。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "astrbot" / "data" / "cmd_config.json"
DST = ROOT / "astrbot" / "data" / "cmd_config.example.json"

SECRET_KEY = re.compile(r"(?i)(api_key|apikey|password|passwd|token|secret)")
API_KEY = re.compile(r"^sk-[A-Za-z0-9_\-]{6,}$")


def scrub(obj, path=""):
    if isinstance(obj, dict):
        return {k: scrub(v, f"{path}/{k}") for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub(v, f"{path}/{i}") for i, v in enumerate(obj)]
    if isinstance(obj, str):
        if API_KEY.match(obj):
            return "sk-REPLACE_WITH_YOUR_KEY"
        if obj and SECRET_KEY.search(path):
            return "<REDACTED>"
    return obj


def main() -> int:
    if not SRC.exists():
        print(f"找不到 {SRC}", file=sys.stderr)
        return 1
    data = json.loads(SRC.read_text(encoding="utf-8-sig"))
    clean = scrub(data)
    DST.write_text(
        json.dumps(clean, ensure_ascii=False, indent=4) + "\n", encoding="utf-8"
    )
    print(f"已生成 {DST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
