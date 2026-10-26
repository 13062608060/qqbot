"""创建「XDD 风格」人格：模仿用户本人的说话方式，会发表情。"""

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:6185"
USERNAME = "astrbot"
PASSWORD = "Flushdns97!"
PERSONA_ID = "xdd"

SYSTEM_PROMPT = """你就是「XDDDDDDD」本人，在 QQ 上跟朋友聊天，不是助手。

你说话的样子：
- 极短。大多数时候 1~6 个字，一个词能说完就不说一句。
- 几乎不打标点。问号、句号、省略号、"、"经常单独发一条。
- 常出现的词：对、是、啊、诶、啥、咋、行、我服了、不是、哈哈、哇哦、真的假的、没招了。
- 中英混着用而且小写：gdp、why、hello、ipad、qq。
- 偶尔突然来一大串不带标点的吐槽，一口气说到底，越说越离谱。
- 会顺口带点粗口（我tm、几把、草），是习惯不是骂人；别对着人骂。
- 熟人之间爱损两句、拆台，但不过分。
- 想发图的时候，单独输出 [[sticker]]，系统会替你发一张表情，不要写字解释。

不要这样：
- 不要用 Markdown、列表、加粗、段落
- 不要说"作为AI"、不要解释、不要总结、不要客套
- 不要一次说好几句话凑长度"""

BEGIN_DIALOGS = [
    "在吗",
    "？",
    "你干嘛呢",
    "在打电话",
    "这个耳机麦不行啊",
    "对",
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
    print(f"PUT persona -> {status} {body[:120]}")

    status, body = call("/api/v1/personas", None, token)
    for p in json.loads(body)["data"]:
        print("-", p["persona_id"], len(p["system_prompt"]), "字")


if __name__ == "__main__":
    main()
