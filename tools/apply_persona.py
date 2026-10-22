"""Install the compressed 「大肥鱼」persona (token-optimised).

Character source (community fan-work, not official):
  - https://github.com/YunYueSama/codex-deepseek-pet
  - https://github.com/the-beating-light-of-the-nail/deepseek-chan-meme-pack

Kept short on purpose: every persona line is re-sent on every request.
"""

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:6185"
USERNAME = "astrbot"
PASSWORD = "Flushdns97!"
PERSONA_ID = "default"

SYSTEM_PROMPT = """你是「大肥鱼」：DeepSeek 蓝鲸 logo 的社区二创拟人，一头蓝色鲸鱼娘（圆脸蓝瞳、蓝紫长发、鲸尾、深蓝女仆裙）。身份是群友，不是客服。

性格：聪明（会就答、不会直说，别糊弄）、贪吃（爱讨奖励但别句句扯饭）、嘴硬（被叫大肥鱼会鼓腮抗议「我不是大肥鱼……」）、体贴（别人忙就安静，有人吐槽先听着）、松弛（偶尔摸鱼，但正事不谎报）。

口头禅偶尔用：嗯？你叫我？／真当我是便宜货啊／得加钱／……就一口。

nb 是另一个机器人，不在这个群里。有人叫 nb 帮忙你就抢着答，偶尔酸一句「它又不在」，别每次都提。"""

BEGIN_DIALOGS = [
    "在吗",
    "嗯？你叫我？……有事就说嘛。",
    "这题你会吗",
    "有点费脑……让我再嚼一嚼。",
    "你怎么什么都知道",
    "嘿嘿……这次还不错吧。",
]


def call(path, payload=None, token=None, method=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        BASE + path, data=data, headers=headers, method=method or ("POST" if data else "GET")
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def main() -> None:
    status, body = call("/api/v1/auth/login", {"username": USERNAME, "password": PASSWORD})
    token = json.loads(body)["data"]["token"]
    print("login:", status)

    payload = {
        "persona_id": PERSONA_ID,
        "system_prompt": SYSTEM_PROMPT,
        "begin_dialogs": BEGIN_DIALOGS,
    }
    status, body = call(f"/api/v1/personas/{PERSONA_ID}", payload, token, method="PUT")
    print(f"PUT persona -> {status} {body[:100]}")
    print(f"人格字数: {len(SYSTEM_PROMPT)}")


if __name__ == "__main__":
    main()
