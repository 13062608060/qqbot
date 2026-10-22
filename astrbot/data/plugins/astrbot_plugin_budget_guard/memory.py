"""大肥鱼记忆库：把重要事件写在本地，需要时按关键词检索。

目录结构（默认 data\\大肥鱼记忆）：
    global.txt          跨群的重要事
    group_<群号>.txt      群内的事
    user_<QQ>.txt        和某个人的事

每行一条：
    2026-10-22 18:30 | 谁 | 事件内容
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

MAX_LINES = 500
MAX_QUERY_HITS = 5


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


class MemoryStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    # ---------- 文件 ----------

    def path_for(self, scope: str) -> Path:
        scope = (scope or "global").strip()
        if scope.startswith("group_"):
            name = "group_" + re.sub(r"\D", "", scope) or "group_unknown"
        elif scope.startswith("user_"):
            name = "user_" + re.sub(r"\D", "", scope)
        elif scope.isdigit():
            name = f"group_{scope}"
        else:
            name = "global"
        return self.root / f"{name}.txt"

    # ---------- 写入 ----------

    def append(self, text: str, scope: str = "global", who: str = "") -> str:
        text = (text or "").strip().replace("\n", " ")
        if not text:
            return "内容为空，没记。"
        path = self.path_for(scope)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        if path.exists():
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        # 简单去重：同一句话不重复记
        if any(text in line for line in lines[-50:]):
            return "这条已经记过了。"
        lines.append(f"{_now()} | {who or '未知'} | {text}")
        lines = lines[-MAX_LINES:]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return f"记下了（{path.name}）：{text}"

    # ---------- 检索 ----------

    @staticmethod
    def _tokens(query: str) -> list[str]:
        query = re.sub(r"\s+", "", query or "")
        tokens = {query[i : i + 2] for i in range(len(query) - 1)}
        tokens.update(w for w in re.findall(r"[\u4e00-\u9fa5]{2,4}", query))
        return [t for t in tokens if len(t) >= 2]

    def search(self, query: str, scope: str = "global", limit: int = MAX_QUERY_HITS) -> list[str]:
        tokens = self._tokens(query)
        if not tokens:
            return []
        files = [self.path_for(scope)]
        global_file = self.path_for("global")
        if global_file not in files:
            files.append(global_file)

        scored: list[tuple[int, str]] = []
        for path in files:
            if not path.exists():
                continue
            for idx, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines()):
                if not line.strip():
                    continue
                score = sum(line.count(tok) for tok in tokens)
                if score:
                    scored.append((score * 1000 - idx, line))
        scored.sort(reverse=True)
        if scored:
            return [line for _, line in scored[:limit]]

        # 没命中就退回"最近几条"，让模型自己判断有没有用
        recent: list[str] = []
        for path in files:
            if not path.exists():
                continue
            lines = [ln for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
            recent.extend(lines[-limit:])
        return recent[-limit:]
