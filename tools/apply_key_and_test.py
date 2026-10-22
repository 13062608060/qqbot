"""Validate a DeepSeek API key, then write it into AstrBot's config.

Usage:
    python tools\\apply_key_and_test.py sk-xxxxxxxx

Steps:
  1) POST a 1-token chat completion to https://api.deepseek.com/v1 to prove the key
     and the model id work;
  2) store the key in data/cmd_config.json -> provider_sources[deepseek_source].key;
  3) tell you to restart AstrBot (the launcher does it).
"""

import json
import pathlib
import sys
import urllib.error
import urllib.request

CFG = pathlib.Path(__file__).resolve().parents[1] / "astrbot" / "data" / "cmd_config.json"
API_BASE = "https://api.deepseek.com/v1"
MODEL = "deepseek-flash"


def probe(key: str) -> tuple[bool, str]:
    body = json.dumps(
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 8,
            "stream": False,
        }
    ).encode()
    req = urllib.request.Request(
        f"{API_BASE}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return True, f"HTTP {resp.status} | reply={text!r} | usage={usage}"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        return False, f"HTTP {exc.code} | {detail}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def store(key: str) -> str:
    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    sources = cfg.get("provider_sources") or []
    if not sources:
        raise SystemExit("no provider_sources in config")
    target = next((s for s in sources if s.get("id") == "deepseek_source"), sources[0])
    target["key"] = [key]
    CFG.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target.get("id", "?")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not argv[1].strip().startswith("sk-"):
        print(__doc__)
        return 2
    key = argv[1].strip()

    ok, info = probe(key)
    print(f"DeepSeek probe: {'OK' if ok else 'FAILED'}")
    print(f"  {info}")

    source_id = store(key)
    print(f"key stored in provider_sources[{source_id}]")
    print("restart AstrBot (stop-all.bat then start-all.bat, or just start-astrbot.bat)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
