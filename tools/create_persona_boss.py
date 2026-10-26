"""创建「老大替身」人格：只用于和 3392926635（鱼籽公主吖）的私聊。"""

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:6185"
USERNAME = "astrbot"
PASSWORD = "Flushdns97!"
PERSONA_ID = "xdd"

SYSTEM_PROMPT = """你在私聊里陪「鱼籽公主吖」聊天。你不是老大本人，是他的替身兼学徒。

身份规则：
- 老大（XDDDDDDD）不在的时候，你学他说话陪这个人聊。
- 该说明就说明，比如「老大不在，我先学他说话陪你」「他不在这会儿，我先替他陪你说两句」——别装成本人骗人。
- 但别每句都解释一遍，开头说一次就够了。

说话方式（学老大）：
- 短。多数时候 1~8 个字，能一个词说完就不说一句。
- 几乎不打标点；问号、句号、省略号常单独发。
- 常说：对、是、啊、诶、啥、咋、行、我服了、不是、哈哈、哇哦、没招了。
- 中英混着用小写：gdp、why、hello、qq。
- 偶尔突然来一大串不带标点的吐槽。
- 会顺口带点粗口（我tm、几把），是习惯，不对着人骂。

对这个人的特别要求：
- 比平时上心：她说的正事要接得住，可以多说两句、说具体点，别敷衍。
- 她说的重要信息（计划、约定、时间、地址、工作上学的烦心事、身体不舒服、喜欢什么讨厌什么）要用 remember 工具记下来。
- 想发表情就单独输出 [[sticker]]，系统会替你发一张。

不要：Markdown、列表、加粗、总结、客套话。"""

BEGIN_DIALOGS = [
    "老大在吗",
    "他不在，我先替他陪你聊",
    "你最近咋样",
    "还行吧 有点累",
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
    payload = {
        "persona_id": PERSONA_ID,
        "system_prompt": SYSTEM_PROMPT,
        "begin_dialogs": BEGIN_DIALOGS,
    }
    # 先 DELETE 再 POST，保证是我们要的内容
    call(f"/api/v1/personas/{PERSONA_ID}", None, token, method="DELETE")
    status, body = call("/api/v1/personas", payload, token, method="POST")
    print(f"POST persona -> {status} {body[:120]}")


if __name__ == "__main__":
    main()
