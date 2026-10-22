"""Compare latency / token usage of deepseek-flash with thinking on vs off.

Usage:
    python tools\\bench_model.py sk-xxxx
"""

import json
import sys
import time
import urllib.request

API = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-flash"

PROMPT = [
    {"role": "system", "content": "你是QQ群里的助手，回答简短口语化，控制在两句话内。"},
    {"role": "user", "content": "帮我想三个周末去杭州玩的安排，别太长"},
]


def run(key: str, thinking: bool) -> None:
    body = {
        "model": MODEL,
        "messages": PROMPT,
        "max_tokens": 300,
        "stream": False,
        "thinking": {"type": "enabled" if thinking else "disabled"},
    }
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode())
    elapsed = time.perf_counter() - started

    msg = data["choices"][0]["message"]
    usage = data.get("usage", {})
    reasoning = msg.get("reasoning_content") or ""
    answer = msg.get("content") or ""

    label = "thinking=ON " if thinking else "thinking=OFF"
    print(f"[{label}] {elapsed:.2f}s  tokens in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')}"
          f" (reasoning chars={len(reasoning)})")
    print(f"  answer: {answer.strip()[:160]!r}")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    key = argv[1].strip()
    run(key, thinking=False)
    run(key, thinking=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
