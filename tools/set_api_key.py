"""Set the DeepSeek (or any OpenAI-compatible) API key in AstrBot's config.

Usage:
    python tools\\set_api_key.py sk-xxxxxxxx

Writes into data/cmd_config.json -> provider_sources[0].key (AstrBot v4.29 layout).
Restart AstrBot afterwards (or use the WebUI: 模型提供商 -> deepseek -> API Key).
"""

import json
import pathlib
import sys

CFG = pathlib.Path(__file__).resolve().parents[1] / "astrbot" / "data" / "cmd_config.json"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    key = argv[1].strip()
    if not key:
        print("empty key")
        return 2

    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    sources = cfg.get("provider_sources") or []
    if not sources:
        print("no provider_sources in config; create the provider in the WebUI first")
        return 1

    target = next((s for s in sources if s.get("id") == "deepseek_source"), sources[0])
    target["key"] = [key]
    CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"api key written to provider_sources[{target.get('id')}]; restart AstrBot to apply")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
