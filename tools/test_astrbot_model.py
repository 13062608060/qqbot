"""Verify AstrBot's model wiring end-to-end via its own dashboard API.

1) login -> JWT
2) POST /api/v1/providers/test  (does the configured deepseek provider answer?)
3) POST /api/v1/chat            (does a real chat turn produce a reply?)
"""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:6185"
USER = "astrbot"
PASSWORD = "Flushdns97!"


def call(path: str, payload: dict | None = None, token: str | None = None, timeout: int = 120):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode(errors="replace")
            return resp.status, body
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")


def main() -> int:
    status, body = call("/api/v1/auth/login", {"username": USER, "password": PASSWORD})
    print(f"login: HTTP {status}")
    if status != 200:
        print(body[:400])
        return 1
    token = json.loads(body)["data"]["token"]

    status, body = call("/api/v1/providers", None, token)
    if status == 200:
        data = json.loads(body).get("data") or []
        items = data if isinstance(data, list) else data.get("providers", [])
        print("providers:", [(p.get("id"), p.get("model"), p.get("enable")) for p in items])
    else:
        print("providers:", status, body[:300])

    status, body = call("/api/v1/providers/test", {"provider_id": "deepseek"}, token, timeout=180)
    print(f"provider test: HTTP {status}")
    print("  ", body[:600].replace("\n", " "))

    status, body = call(
        "/api/v1/chat",
        {"message": "用一句话介绍你自己，20字以内", "enable_streaming": False, "username": "qatest"},
        token,
        timeout=180,
    )
    print(f"chat: HTTP {status}")
    print("  ", body[:800].replace("\n", " "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
