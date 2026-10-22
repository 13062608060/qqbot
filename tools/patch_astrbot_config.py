"""Patch AstrBot cmd_config.json: add OneBot v11 platform + DeepSeek provider.

Idempotent: re-running replaces the managed entries by id and leaves the rest untouched.
"""

import json
import pathlib
import sys

CFG = pathlib.Path(__file__).resolve().parents[1] / "astrbot" / "data" / "cmd_config.json"

PLATFORM_ID = "qq-onebot"
PROVIDER_ID = "deepseek"

PLATFORM = {
    "id": PLATFORM_ID,
    "type": "aiocqhttp",
    "enable": True,
    # Only accept the reverse-WS client from this machine (SnowLuma runs locally).
    "ws_reverse_host": "127.0.0.1",
    "ws_reverse_port": 6199,
    "ws_reverse_token": "",
}

PROVIDER = {
    "id": PROVIDER_ID,
    "provider": "deepseek",
    "type": "openai_chat_completion",
    "provider_type": "chat_completion",
    "enable": True,
    "key": [],
    "api_base": "https://api.deepseek.com/v1",
    "model": "deepseek-flash",
    "max_context_tokens": 0,
    "timeout": 120,
    "proxy": "",
    "custom_headers": {},
}


def main() -> int:
    if not CFG.exists():
        print(f"missing config: {CFG}")
        return 1

    original = CFG.read_text(encoding="utf-8-sig")
    cfg = json.loads(original)

    platforms = [p for p in cfg.get("platform", []) if p.get("id") != PLATFORM_ID]
    platforms.append(PLATFORM)
    cfg["platform"] = platforms

    providers = [p for p in cfg.get("provider", []) if p.get("id") != PROVIDER_ID]
    providers.append(PROVIDER)
    cfg["provider"] = providers

    # WebUI should not listen on the LAN by default.
    cfg.setdefault("dashboard", {})["host"] = "127.0.0.1"

    # Group chat: answer when @-mentioned, keep "/" as the explicit command prefix.
    cfg["wake_prefix"] = ["/"]
    settings = cfg.setdefault("platform_settings", {})
    settings["reply_with_mention"] = True

    backup = CFG.with_suffix(".json.bak")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")

    CFG.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"patched: platform={PLATFORM_ID} provider={PROVIDER_ID} -> {CFG}")
    print(f"backup: {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
