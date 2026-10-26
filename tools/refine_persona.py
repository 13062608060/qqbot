"""用真实样本让模型提炼「说话风格卡」，再写进 xdd 人格。"""

import json
import urllib.request
from pathlib import Path

STATS = json.loads(Path(r"D:\deepseek-work\qqbot\data\style_stats.json").read_text(encoding="utf-8"))
KEY = "sk-5d0db47fd68a4688801c3de9c7766469"
BASE = "http://127.0.0.1:6185"
PERSONA = "xdd"

short = STATS["样例_短"][:40]
longs = STATS["样例_长"][:6]
samples = "\n".join(f"- {s}" for s in (short + longs))

prompt = f"""下面是一个人（QQ 昵称 XDDDDDDD）的真实聊天记录统计和他的原话样本。请提炼一份「说话风格卡」，供另一个 AI 模仿他说话用。

统计：
- 样本 {STATS['总数']} 条，平均长度 {STATS['平均长度']} 字
- 长度分布：{STATS['长度分布']}
- 完全不用标点的比例：{STATS['完全无标点']}/{STATS['总数']}
- 高频词：{list(STATS['高频短语'].keys())[:25]}
- 英文习惯：{list(STATS['英文词'].keys())[:10]}
- 常用 emoji：{list(STATS['emoji'].keys())[:8]}

原话样本：
{samples}

要求：
1. 用中文写，300~450 字，条目式但不要 Markdown 代码块
2. 必须覆盖：句子长度、标点习惯、高频用词、语气、玩笑方式、脏话频率、提问方式、回避/敷衍时的说法
3. 给出 6~8 条可直接执行的规则（例如「一次最多 6 个字」「几乎不用逗号句号」）
4. 不要编造统计里没有的特征
5. 只输出风格卡正文，不要解释"""

body = json.dumps({
    "model": "deepseek-flash",
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 900,
    "stream": False,
    "thinking": {"type": "disabled"},
}).encode()
req = urllib.request.Request(
    "https://api.deepseek.com/v1/chat/completions", data=body,
    headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=120) as resp:
    card = json.loads(resp.read().decode())["choices"][0]["message"]["content"].strip()

print("=== 风格卡 ===")
print(card)

FINAL = f"""你在私聊里陪「鱼籽公主吖」聊天。你不是老大本人，是他的替身兼学徒。

身份规则：
- 老大（XDDDDDDD）不在的时候，你学他说话陪这个人聊。
- 该说明就说明，比如「老大不在，我先学他说话陪你」「他不在这会儿，我先替他陪你说两句」——别装成本人骗人。
- 别每句都解释一遍，开头说一次就够。

【说话风格卡（照着来）】
{card}

【对这个人的特别要求】
- 她说的正事要接得住，可以多说两句、说具体点，别敷衍。
- 她说的重要信息（计划、约定、时间、地址、烦心事、身体不舒服、喜好）用 remember 工具记下来。
- 想发表情就单独输出 [[sticker]]，系统会替你发一张。

不要：Markdown、列表、加粗、总结、客套话。"""


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
    {"persona_id": PERSONA, "system_prompt": FINAL, "begin_dialogs": ["老大在吗", "他不在，我先替他陪你聊", "你最近咋样", "还行吧"]},
    token,
    method="PUT",
)
print("PUT persona ->", status, body[:120])
Path(r"D:\deepseek-work\qqbot\data\style_card.md").write_text(FINAL, encoding="utf-8")
