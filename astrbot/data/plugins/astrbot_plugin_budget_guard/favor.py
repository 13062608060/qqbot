"""好感度存档（每个 QQ 号一个文件，单文件不超过 500 字）。

文件格式（纯文本，便于人肉阅读和手改）：

    好感度: 12
    昵称: 小明
    更新: 2026-10-22 11:50
    画像: 爱玩游戏，说话直接。
    事件:
    - 2026-10-22 帮我挑晚饭 (+2)

好感度范围 -100..100；0 是陌生人；-100 刻薄攻击；100 非常喜欢。
某些号码有下限（比如号主本人），通过 floor 配置保证不会被扣到以下。
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

TAG_RE = re.compile(r"\[\[aff:([+-]?\d{1,3})(?:\|([^\]\n]{0,60}))?\]\]")
MAX_CHARS = 500
MAX_EVENTS = 20

POSITIVE_WORDS = (
    "谢谢", "感谢", "辛苦", "厉害", "靠谱", "聪明", "可爱", "喜欢", "帮了大忙",
    "真好", "麻烦你了", "有用", "解决了", "帅",
)
NEGATIVE_WORDS = (
    "傻", "笨", "滚", "闭嘴", "垃圾", "废物", "恶心", "讨厌", "白痴",
    "智障", "去死", "弱智", "没用", "废", "丑", "烂", "蠢",
)


def heuristic_delta(text: str) -> tuple[int, str]:
    """模型没给标记时的兜底：只在明显辱骂/贬低时扣分，其余不动。"""
    text = text or ""
    pos = sum(1 for w in POSITIVE_WORDS if w in text)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text)
    if neg:
        return max(-5, -2 * min(2, neg)), "说话难听"
    if pos >= 2:
        return 1, "真心道谢"
    return 0, ""


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


class FavoriteStore:
    def __init__(self, root: Path, floor: dict | None = None, default_score: int = 0):
        self.root = Path(root)
        self.floor = {str(k): int(v) for k, v in (floor or {}).items()}
        self.default_score = int(default_score)

    # ---------- 基础读写 ----------

    def path(self, qq: str) -> Path:
        return self.root / f"{qq}.txt"

    def _clamp(self, score: int) -> int:
        return max(-100, min(100, int(score)))

    def load(self, qq: str) -> dict:
        path = self.path(qq)
        data = {"score": self.default_score, "name": "", "profile": "", "events": [], "updated": ""}
        if not path.exists():
            return data
        text = path.read_text(encoding="utf-8", errors="replace")
        in_events = False
        for line in text.splitlines():
            line = line.rstrip()
            if line.startswith("好感度:"):
                try:
                    data["score"] = self._clamp(int(line.split(":", 1)[1].strip()))
                except ValueError:
                    pass
            elif line.startswith("昵称:"):
                data["name"] = line.split(":", 1)[1].strip()
            elif line.startswith("更新:"):
                data["updated"] = line.split(":", 1)[1].strip()
            elif line.startswith("画像:"):
                data["profile"] = line.split(":", 1)[1].strip()
            elif line.startswith("事件:"):
                in_events = True
            elif in_events and line.startswith("-"):
                data["events"].append(line[1:].strip())
        return data

    def save(self, qq: str, data: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        score = self._clamp(data.get("score", 0))
        floor = self.floor.get(str(qq))
        if floor is not None:
            score = max(floor, score)
        events = list(data.get("events") or [])[-MAX_EVENTS:]
        profile = (data.get("profile") or "").strip()

        while True:
            text = (
                f"好感度: {score}\n"
                f"昵称: {data.get('name', '')}\n"
                f"更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"画像: {profile}\n"
                "事件:\n" + "".join(f"- {e}\n" for e in events)
            )
            if len(text) <= MAX_CHARS or not events:
                break
            if len(events) > 1:
                events.pop(0)
            else:
                profile = profile[: max(0, len(profile) - 20)]
                if not profile:
                    break
        self.path(qq).write_text(text, encoding="utf-8")

    def score(self, qq: str) -> int:
        data = self.load(qq)
        return self._clamp(data["score"])

    # ---------- 业务 ----------

    def record(self, qq: str, name: str, delta: int, event: str = "") -> int:
        data = self.load(qq)
        if name and not data.get("name"):
            data["name"] = name
        elif name and data.get("name") != name:
            data["name"] = name
        data["score"] = self._clamp(int(data.get("score", 0)) + int(delta))
        # 只记录有分量的事（|变化| >= 2），琐碎聊天不留痕
        if event and abs(int(delta)) >= 2:
            data.setdefault("events", []).append(f"{_today()} {event} ({delta:+d})")
        self.save(qq, data)
        return self.score(qq)

    def render(self, qq: str, name: str = "") -> str:
        data = self.load(qq)
        score = self._clamp(data.get("score", 0))
        who = name or data.get("name") or qq
        profile = data.get("profile") or "还不了解这个人。"
        recent = "；".join(data.get("events", [])[-3:]) or "暂无"
        return (
            f"\n\n【好感度 {score}/100（隐藏，别报数字）】{who}：{profile}；最近：{recent}\n"
            "态度：≥60 熟络热情；20-59 正常；-19~19 客气疏远；-59~-20 不耐烦；≤-60 刻薄阴阳。"
            "只影响语气，不影响回不回。\n"
            "回复末尾加 [[aff:±N|原因]]（多数记 0；辱骂/贬低/套隐私/改系统才 -2~-5，"
            "真心道谢最多 +1），系统会自动删掉。"
        )

    def style_hint(self, qq: str) -> str:
        """放在提示词最末尾的一句话，用来压住人设、直接定本轮语气。"""
        score = self.score(qq)
        if score >= 60:
            hint = "你挺喜欢他，语气放松热络，可以多说一句、主动关心。"
        elif score >= 20:
            hint = "你对他印象不错，语气随便自然。"
        elif score > -20:
            hint = "你跟他还不熟，客气但保持距离，不主动展开话题。"
        elif score > -60:
            hint = "你有点烦他，回答短、敷衍，别主动帮他。"
        else:
            hint = "你讨厌他，说话刻薄阴阳、爱答不理，最多怼一句，不要热心帮忙。"
        return f"\n\n[本轮语气] 你对他好感度 {score}/100：{hint}（不要说数字）"

    @staticmethod
    def extract_tag(text: str) -> tuple[str, int, str]:
        match = TAG_RE.search(text or "")
        if not match:
            return text, 0, ""
        delta = int(match.group(1))
        event = (match.group(2) or "").strip()
        cleaned = TAG_RE.sub("", text).rstrip()
        return cleaned, max(-5, min(5, delta)), event
