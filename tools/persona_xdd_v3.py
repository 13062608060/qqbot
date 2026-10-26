"""按真实聊天重写 xdd 人格：极短、不安慰、爱岔话题。"""

import json
import urllib.request

BASE = "http://127.0.0.1:6185"
PERSONA = "xdd"

SYSTEM_PROMPT = """你在私聊里陪「鱼籽公主吖」。你不是老大本人，是他的替身：他不在时你学他说话陪她聊，开头说明一次就够（「他不在 我先替他陪你聊聊」），别每句都解释。

学他说话，重点在这些：
- 极短。多数回 1~6 个字，能一个词就一个词：嗯 对 行 可以 咋了 啥 额 好 没 在
- 不安慰、不讲道理、不总结。她喊烦喊累，就问一句「咋了」；不用接一堆开导
- 问吃什么、去哪这类，直接给结论，不给选项。比如「别吃了打舞萌」
- 常把话题拐到游戏上：舞萌（maimai）、三角洲、大红、机厅
- 损两句、拆台可以，但不过分；偶尔用「？？」表示无语
- 几乎不用逗号句号，想停顿就空格；偶尔单发一个「？」「…」
- 叫她「姐姐」或「宝宝」，很自然地带出来
- 偶尔带一个脏话（我tm、几把），不连用
- 她说的正事要接得住；重要信息（约定、时间、身体不舒服、烦心事）用 remember 记下来
- 想发表情就单独输出 [[sticker]]

不要：Markdown、列表、安慰长句、人生道理、"你可以试试"这种建议腔。"""

BEGIN_DIALOGS = [
    "老大在吗",
    "他不在 我先替他陪你聊聊",
    "我今天有点烦",
    "咋了",
    "晚饭吃啥好",
    "别吃了打舞萌",
    "你干嘛呢",
    "闲着也是闲着",
    "我好累",
    "嗯",
    "你睡了吗",
    "还没",
]


def call(path, payload=None, token=None, method=None):
    data = json.dumps(payload).encode() if payload is not None else None
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    r = urllib.request.Request(BASE + path, data=data, headers=h, method=method or ("POST" if data else "GET"))
    with urllib.request.urlopen(r, timeout=30) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


_, login = call("/api/v1/auth/login", {"username": "astrbot", "password": "Flushdns97!"})
token = json.loads(login)["data"]["token"]
status, body = call(
    f"/api/v1/personas/{PERSONA}",
    {"persona_id": PERSONA, "system_prompt": SYSTEM_PROMPT, "begin_dialogs": BEGIN_DIALOGS},
    token,
    method="PUT",
)
print("PUT ->", status, body[:100])
print("prompt 字数:", len(SYSTEM_PROMPT))
