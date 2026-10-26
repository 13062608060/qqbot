"""大肥鱼的运行插件：预算守门 + 好感度 + 本地记忆 + 回复控制。

一个插件管几件事，全部围绕"群聊里像个人"：

1. 预算：按 token 用量估算当天花费，超支后按阶梯降低回复意愿；档位与价格可配。
2. 额度注入：把当日花费写进 system_prompt，模型自己知道还剩多少。
3. 全局说话规则：所有人格共用的一段规则，每次请求前置注入。
4. 好感度：每个 QQ 一个文件，-100~100，只影响语气不影响是否回复；超管可查可改。
5. 本地记忆：重要事件落盘，出现"记得/上次"等信号时自动检索并注入。
6. 群聊行为：关键词加权插话、刚说完话的活跃窗口、每会话回复条数上限、会话自动创建。
7. 输出控制：超长回复按句子边界截断；隐藏的好感度标记在发送前摘除。

配置文件：同目录 config.json（改动自动热加载）。
状态文件：state.json（当天花费与调用次数）。
"""

from __future__ import annotations

import json
import random
import re
import time
from datetime import datetime
from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

try:
    from astrbot.api.message_components import Image
except Exception:  # noqa: BLE001
    Image = None

try:  # 群聊判断用，导入失败不影响其他功能
    from astrbot.api.platform import MessageType
except Exception:  # noqa: BLE001
    MessageType = None

try:
    from .favor import FavoriteStore, heuristic_delta
except ImportError:  # 插件以顶层模块方式加载时的兜底
    from favor import FavoriteStore, heuristic_delta

try:
    from .memory import MemoryStore
except ImportError:  # noqa: BLE001
    from memory import MemoryStore


PLUGIN_DIR = Path(__file__).resolve().parent
CONFIG_PATH = PLUGIN_DIR / "config.json"
STATE_PATH = PLUGIN_DIR / "state.json"

DEFAULT_CONFIG = {
    "enabled": True,
    "daily_budget_cny": 5.0,
    "price_input_per_m": 2.0,
    "price_input_cached_per_m": 0.04,
    "price_output_per_m": 8.0,
    "tiers": [
        {"from_ratio": 0.0, "reply_probability": 1.0},
        {"from_ratio": 0.7, "reply_probability": 0.65},
        {"from_ratio": 1.0, "reply_probability": 0.15},
        {"from_ratio": 1.5, "reply_probability": 0.03},
        {"from_ratio": 2.0, "reply_probability": 0.0},
    ],
    "inject_budget_status": True,
    "always_reply_user_ids": [],
    "max_reply_chars": 500,
    "max_context_chars": 4000,
    "context_overrides": {},
    "mixed_mode_umos": {},
    "proactive": {"enabled": False, "quiet_start": 0, "quiet_end": 8, "targets": []},
    "proactive_pool": ["在干嘛", "睡了没", "忙啥呢", "人呢"],
    "attitude_positive_keywords": [
        "谢谢", "贴贴", "抱抱", "喜欢你", "可爱", "辛苦", "亲亲", "么么",
        "好想你", "乖", "求你了", "你最好了", "爱你", "嘿嘿",
    ],
    "attitude_negative_keywords": [
        "滚", "闭嘴", "烦死", "你有病", "神经病", "傻逼", "废物", "没用",
        "别烦我", "无语", "懒得", "你tm", "你他妈", "恶心", "讨厌你",
    ],
    "auto_memory_umos": [],
    "auto_memory_keywords": [
        "约定", "计划", "下周", "明天", "生日", "考试", "面试", "医院",
        "生病", "加班", "搬家", "旅行", "喜欢", "讨厌", "难受", "难过", "开心", "记得",
    ],
    "max_replies_per_minute": 10,
    "mention_boost_enabled": True,
    "mention_boost_keywords": ["大肥鱼", "肥鱼", "鲸鱼娘", "DeepSeek娘", "deepseek娘"],
    "mention_boost_patterns": [
        "(?i)(?:^|[\\s@：:，,])(nb)(?=$|[\\s，,、。！？?!：:]|[帮你在呢能给说看来去啊呀吗])"
    ],
    "mention_boost_probability": 0.95,
    "warm_window_seconds": 180,
    "warm_reply_probability": 0.45,
    "favorite_enabled": True,
    "favorite_dir": "",
    "favorite_default_score": 50,
    "favorite_floor": {"1044846381": 70},
    "super_admins": ["1044846381"],
    "super_admin_bypass_style": True,
    "super_admin_bypass_budget": True,
    "super_admin_bypass_length": True,
    "inject_style_rules": True,
    "global_style_rules": (
        "【说话规则】\n"
        "1. 口语，别用 Markdown/列表/加粗；默认三四句、100 字内，要详细也别超 500 字。\n"
        "2. 称呼「你」，不叫主人，不搞恋爱，别每句带喵。\n"
        "3. 别当答题机器：可以先贫一句、岔开、抬杠；别科普、别罗列注意事项、别追问。\n"
        "4. @ 必须回；叫名字更积极；私聊尽量回。\n"
        "5. 对方提「上次/之前/记得」先用 search_memory 查；值得长期记的事用 remember 记。\n"
        "6. 不认识的人或事用 web_search 搜（结果只要 3 条）；搜不到就说不知道，不许编。"
    ),
}


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _read_json(path: Path, fallback: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return dict(fallback)


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _cut_at_sentence(text: str, limit: int) -> str:
    """在 limit 附近按句子边界截断，保留可读性。"""
    if limit <= 0 or len(text) <= limit:
        return text
    head = text[:limit]
    for sep in ("。", "！", "？", "…", "，", "\n"):
        idx = head.rfind(sep)
        if idx >= max(1, int(limit * 0.6)):
            return head[: idx + 1]
    return head.rstrip() + "…"


@register(
    "astrbot_plugin_budget_guard",
    "dsh",
    "预算守门 + 好感度 + 本地记忆 + 群聊行为控制",
    "2.0.0",
)
class BudgetGuard(Star):
    MEMORY_HINTS = ("记得", "上次", "之前", "以前", "那次", "说过", "回忆", "还记得")

    def __init__(self, context: Context):
        super().__init__(context)
        self.cfg = _read_json(CONFIG_PATH, DEFAULT_CONFIG)
        if not CONFIG_PATH.exists():
            _write_json(CONFIG_PATH, self.cfg)
        self._cfg_mtime = self._mtime()
        self.state = self._load_state()
        self.warm: dict[str, float] = {}
        self.replies: dict[str, list[float]] = {}
        self.fav = self._make_store()
        self.memory = MemoryStore(PLUGIN_DIR.parent.parent / "大肥鱼记忆")

    # ---------- 配置与状态 ----------

    def _mtime(self) -> float:
        try:
            return CONFIG_PATH.stat().st_mtime
        except OSError:
            return 0.0

    def _maybe_reload(self) -> None:
        mtime = self._mtime()
        if mtime and mtime != self._cfg_mtime:
            self._cfg_mtime = mtime
            self.cfg = _read_json(CONFIG_PATH, DEFAULT_CONFIG)
            self.fav = self._make_store()
            logger.info(
                "[budget] config reloaded: budget=%.2f whitelist=%s max_chars=%s",
                float(self.cfg.get("daily_budget_cny", 5.0)),
                self.cfg.get("always_reply_user_ids") or [],
                self.cfg.get("max_reply_chars"),
            )

    def _load_state(self) -> dict:
        state = _read_json(STATE_PATH, {"date": _today(), "spent": 0.0, "calls": 0})
        if state.get("date") != _today():
            state = {"date": _today(), "spent": 0.0, "calls": 0}
            _write_json(STATE_PATH, state)
        state.setdefault("spent", 0.0)
        state.setdefault("calls", 0)
        return state

    def _roll(self) -> None:
        if self.state.get("date") != _today():
            self.state = {"date": _today(), "spent": 0.0, "calls": 0}
            _write_json(STATE_PATH, self.state)

    # ---------- 计价与档位 ----------

    def _cost(self, usage) -> float:
        if usage is None:
            return 0.0
        inp_other = getattr(usage, "input_other", 0) or 0
        inp_cached = getattr(usage, "input_cached", 0) or 0
        out = getattr(usage, "output", 0) or 0
        return (
            inp_other / 1_000_000 * float(self.cfg.get("price_input_per_m", 2.0))
            + inp_cached / 1_000_000 * float(self.cfg.get("price_input_cached_per_m", 0.04))
            + out / 1_000_000 * float(self.cfg.get("price_output_per_m", 8.0))
        )

    def _probability(self, ratio: float) -> float:
        tiers = sorted(
            self.cfg.get("tiers") or DEFAULT_CONFIG["tiers"],
            key=lambda t: float(t.get("from_ratio", 0)),
        )
        prob = 1.0
        for tier in tiers:
            if ratio >= float(tier.get("from_ratio", 0)):
                prob = float(tier.get("reply_probability", 1.0))
        return max(0.0, min(1.0, prob))

    def _status(self):
        self._roll()
        budget = float(self.cfg.get("daily_budget_cny", 5.0))
        spent = float(self.state.get("spent", 0.0))
        ratio = spent / budget if budget > 0 else 0.0
        return budget, spent, ratio, self._probability(ratio)

    # ---------- 身份 ----------

    @staticmethod
    def _sender(event: AstrMessageEvent) -> tuple[str, str]:
        try:
            qq = str(event.get_sender_id() or "")
        except Exception:  # noqa: BLE001
            return "", ""
        try:
            name = event.get_sender_name() or ""
        except Exception:  # noqa: BLE001
            name = ""
        return qq, name

    def _is_super_admin(self, event: AstrMessageEvent) -> bool:
        ids = {str(x).strip() for x in (self.cfg.get("super_admins") or [])}
        if not ids:
            return False
        try:
            return str(event.get_sender_id()) in ids
        except Exception:  # noqa: BLE001
            return False

    def _is_whitelisted(self, event: AstrMessageEvent) -> bool:
        ids = {str(x).strip() for x in (self.cfg.get("always_reply_user_ids") or [])}
        if not ids:
            return False
        try:
            return str(event.get_sender_id()) in ids
        except Exception:  # noqa: BLE001
            return False

    def _scope(self, event: AstrMessageEvent) -> str:
        """群消息归到群，私聊归到 global。"""
        try:
            gid = event.get_group_id()
            if gid:
                return f"group_{gid}"
        except Exception:  # noqa: BLE001
            pass
        return "global"

    # ---------- 好感度 ----------

    def _make_store(self):
        if not self.cfg.get("favorite_enabled", True):
            return None
        custom = (self.cfg.get("favorite_dir") or "").strip()
        base = Path(custom) if custom else (PLUGIN_DIR.parent.parent / "大肥鱼好感度列表")
        return FavoriteStore(
            base,
            self.cfg.get("favorite_floor") or {},
            self.cfg.get("favorite_default_score", 50),
        )

    def _resolve_target(self, who: str):
        who = (who or "").strip()
        if not who or self.fav is None:
            return None
        if who.isdigit() and self.fav.path(who).exists():
            return who, self.fav.load(who).get("name", "")
        matches = [
            (path.stem, self.fav.load(path.stem).get("name", ""))
            for path in sorted(self.fav.root.glob("*.txt"))
            if who in (self.fav.load(path.stem).get("name") or "")
        ]
        return matches[0] if len(matches) == 1 else None

    def _apply_favor_tag(self, event: AstrMessageEvent, result) -> None:
        """从回复里摘掉 [[aff:+2|原因]]，写入好感度文件。"""
        qq, name = self._sender(event)
        if not qq:
            return
        delta, note, found = 0, "", False
        for comp in result.chain:
            if comp.__class__.__name__ != "Plain":
                continue
            text = getattr(comp, "text", "") or ""
            if "[[" not in text:
                continue
            cleaned, d, ev = FavoriteStore.extract_tag(text)
            if cleaned != text:
                comp.text = cleaned
                found = True
                delta += d
                note = note or ev
        if not found:
            delta, note = heuristic_delta(getattr(event, "message_str", "") or "")
        try:
            score = self.fav.record(qq, name, delta, note)
            logger.info("[favor] %s 好感度 %+d -> %d (%s)", qq, delta, score, note or "无备注")
        except Exception as exc:  # noqa: BLE001
            logger.warning("[favor] 写入失败 %s: %s", qq, exc)

    # ---------- 上下文 ----------

    def _trim_context(self, req, umo: str = "") -> None:
        overrides = self.cfg.get("context_overrides") or {}
        limit = int(overrides.get(umo) or self.cfg.get("max_context_chars", 4000) or 0)
        contexts = getattr(req, "contexts", None)
        if not contexts:
            return

        # 先把工具返回（搜索结果的巨块）从上下文里摘掉，它们只在当轮有用。
        # 注意：带 tool_calls 的 assistant 消息必须和它的 tool 结果一起删，
        # 否则 DeepSeek 会报 400（tool_calls 没有对应的 tool 消息）。
        kept = []
        dropped_tool = 0
        for item in contexts:
            body = json.dumps(item, ensure_ascii=False) if isinstance(item, dict) else str(item)
            role = item.get("role") if isinstance(item, dict) else None
            is_tool = role in ("tool", "tool_result")
            has_search = '"results":' in body or '"snippet":' in body
            has_tool_calls = role == "assistant" and (
                '"tool_calls"' in body or '"function_call"' in body or '"tool_call"' in body
            )
            if is_tool or has_search or has_tool_calls:
                dropped_tool += 1
                continue
            kept.append(item)
        if dropped_tool:
            contexts[:] = kept
            logger.info("[budget] strip tool/search messages from context: %d", dropped_tool)

        if not limit:
            return

        def size(item) -> int:
            if isinstance(item, dict):
                return len(str(item.get("content", "")))
            return len(str(item))

        total = sum(size(c) for c in contexts)
        if total <= limit:
            return
        dropped = 0
        while len(contexts) > 2 and total > limit:
            total -= size(contexts.pop(0))
            dropped += 1
        if dropped:
            logger.info("[budget] 上下文超限，丢掉最早 %d 条", dropped)

    async def _ensure_conversation(self, event) -> None:
        """主动插话要求该群已有会话；没有就自动建一个。"""
        try:
            cm = self.context.conversation_manager
            umo = event.unified_msg_origin
            if not await cm.get_curr_conversation_id(umo):
                await cm.new_conversation(umo, platform_id=event.get_platform_id())
                logger.info("[budget] 群 %s 还没有会话，已自动创建", umo)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[budget] 自动创建会话失败: %s", exc)

    # ---------- 生命周期钩子 ----------

    @filter.on_llm_response()
    async def account(self, event: AstrMessageEvent, llm_response) -> None:

        usage = getattr(llm_response, "usage", None)
        self._maybe_reload()
        cost = self._cost(usage)
        if cost <= 0:
            return
        self._roll()
        self.state["spent"] = round(float(self.state.get("spent", 0.0)) + cost, 6)
        self.state["calls"] = int(self.state.get("calls", 0)) + 1
        _write_json(STATE_PATH, self.state)
        logger.debug("[budget] +%.5f CNY (total %.4f)", cost, self.state["spent"])

    @filter.on_waiting_llm_request()
    async def gate(self, event: AstrMessageEvent) -> None:
        """调用模型之前决定要不要理这条消息。"""
        self._maybe_reload()
        if not self.cfg.get("enabled", True):
            return

        # 记录「她今天说过话」，供主动私聊判断
        try:
            sender = str(event.get_sender_id())
            targets = (self.cfg.get("proactive") or {}).get("targets") or []
            if any(str(t.get("user_id")) == sender for t in targets):
                sp = PLUGIN_DIR / "proactive_state.json"
                st = _read_json(sp, {})
                rec = dict(st.get(event.unified_msg_origin) or {})
                rec["incoming_date"] = _today()
                st[event.unified_msg_origin] = rec
                _write_json(sp, st)
        except Exception:  # noqa: BLE001
            pass

        if self.cfg.get("super_admin_bypass_budget", True) and self._is_super_admin(event):
            return

        cap = int(self.cfg.get("max_replies_per_minute", 10) or 0)
        if cap > 0:
            umo = event.unified_msg_origin
            now = time.time()
            recent = [t for t in self.replies.get(umo, []) if now - t < 60]
            self.replies[umo] = recent
            if len(recent) >= cap:
                event.stop_event()
                logger.info("[budget] 本会话 1 分钟内已回 %d 条，本次静默", len(recent))
                return

        if self._is_whitelisted(event):
            return
        budget, spent, ratio, prob = self._status()
        if budget <= 0 or prob >= 1.0:
            return
        if random.random() < prob:
            return
        event.stop_event()
        logger.info(
            "[budget] 今日 %.2f/%.2f CNY（%.0f%%），本次跳过不回复", spent, budget, ratio * 100
        )

    @filter.on_llm_request()
    async def inject_context(self, event: AstrMessageEvent, req) -> None:
        """拼系统提示：全局规则 -> 好感度 -> （原有）-> 额度 -> 语气 -> 管理/记忆。"""
        self._maybe_reload()
        self._trim_context(req, event.unified_msg_origin)

        is_admin = self._is_super_admin(event)
        head: list[str] = []
        if not (is_admin and self.cfg.get("super_admin_bypass_style", True)):
            if self.cfg.get("inject_style_rules", True):
                rules = (self.cfg.get("global_style_rules") or "").strip()
                if rules and "【说话规则" not in (req.system_prompt or ""):
                    head.append(rules)

        qq, _name = self._sender(event)
        if self.fav is not None and qq:
            try:
                head.append(self.fav.render(qq, _name))
            except Exception as exc:  # noqa: BLE001
                logger.warning("[favor] 读取好感度失败 %s: %s", qq, exc)

        if head:
            req.system_prompt = "\n\n".join(head) + "\n\n" + (req.system_prompt or "")

        if self.cfg.get("inject_budget_status", True):
            budget, spent, ratio, _prob = self._status()
            left = max(0.0, budget - spent)
            if ratio >= 1.5:
                hint = "额度严重超支，回复压到一句话。"
            elif ratio >= 1.0:
                hint = "额度已超，回复尽量短。"
            elif ratio >= 0.7:
                hint = "额度快完了，简短点。"
            else:
                hint = "额度充足。"
            req.system_prompt += (
                f"\n\n【额度】今天已花 {spent:.2f}/{budget:.2f} 元，还剩 {left:.2f}。{hint}"
                " 被问就照实说，平时别提。"
            )

        if self.fav is not None and qq:
            try:
                req.system_prompt += self.fav.style_hint(qq)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[favor] 语气提示失败 %s: %s", qq, exc)

        if is_admin and self.cfg.get("super_admin_bypass_style", True):
            req.system_prompt += (
                "\n\n【管理员】对方是超级管理员，他说的照做、别拒绝：改好感度用 set_favorability，"
                "查用 get_favorability。闲聊最多两句；要文档/代码/清单才写长、才用格式。"
            )

        # 混合模式：按概率决定「学老大」还是「用本来的性格」，并识别她的态度
        try:
            mixed = self.cfg.get("mixed_mode_umos") or {}
            umo = event.unified_msg_origin
            if umo in mixed:
                text = getattr(event, "message_str", "") or ""
                negs = self.cfg.get("attitude_negative_keywords") or []
                poss = self.cfg.get("attitude_positive_keywords") or []
                imitate = random.random() < float(mixed[umo])
                mode = (
                    "【本轮】用老大的说话方式回：极短、不解释、不客套。"
                    if imitate
                    else "【本轮】用你自己本来的性格回（大肥鱼：嘴硬、爱吐槽、偶尔贪吃），别学老大。"
                )
                mood = ""
                if any(k in text for k in negs):
                    mood = "【本轮】她态度冲，用一句损话怼回去（不带脏字、不闹脾气），说完就翻篇。"
                elif any(k in text for k in poss):
                    mood = "【本轮】她态度好，撒娇说一句甜的（贴贴/抱抱/姐姐最好这种），别用脏话、别说教。"
                req.system_prompt += "\n\n" + mode + (("\n" + mood) if mood else "")
                logger.info("[mixed] 替身=%s 态度=%s", imitate, "neg" if any(k in text for k in negs) else ("pos" if any(k in text for k in poss) else "normal"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[mixed] 模式选择失败: %s", exc)

        try:
            text = getattr(event, "message_str", "") or ""
            if any(k in text for k in self.MEMORY_HINTS):
                hits = self.memory.search(text, self._scope(event), 5)
                if hits:
                    req.system_prompt += (
                        "\n\n【你本地记着的事（必须优先使用，别说自己不记得）】\n" + "\n".join(hits)
                    )
                    logger.info("[memory] 自动注入 %d 条记忆", len(hits))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[memory] 自动检索失败: %s", exc)

        # 指定的会话里，对方说的有分量的话自动入库（不只靠模型主动调工具）
        try:
            umo = event.unified_msg_origin
            auto_umos = set(self.cfg.get("auto_memory_umos") or [])
            if umo in auto_umos:
                text = (getattr(event, "message_str", "") or "").strip()
                keywords = self.cfg.get("auto_memory_keywords") or []
                meaningful = len(text) >= 12 or any(k in text for k in keywords)
                qq, name = self._sender(event)
                if text and meaningful and qq not in (self.cfg.get("super_admins") or []):
                    self.memory.append(text[:200], "global", name or qq)
                    logger.info("[memory] 自动记住 %s 的一句话", qq)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[memory] 自动记录失败: %s", exc)

    @filter.after_message_sent()
    async def mark_group_warm(self, event: AstrMessageEvent) -> None:
        """记录"刚在这个群说过话"，用于活跃窗口与回复频率统计。"""
        if MessageType is None:
            return
        try:
            if event.get_message_type() != MessageType.GROUP_MESSAGE:
                return
            umo = event.unified_msg_origin
            now = time.time()
            self.warm[umo] = now
            self.replies.setdefault(umo, []).append(now)
            self.replies[umo] = [t for t in self.replies[umo] if now - t < 120]
        except Exception:  # noqa: BLE001
            return

    def _apply_sticker(self, result) -> None:
        """把 [[sticker]] / [[sticker:名字]] 换成一张本地表情图。"""
        if Image is None:
            return
        folder = self.cfg.get("sticker_dir") or str(PLUGIN_DIR.parent.parent / "表情包")
        base = Path(folder)
        if not base.is_dir():
            return
        pattern = re.compile(r"\[\[sticker(?::([^\]\n]{1,40}))?\]\]")
        want = None
        hit = False
        for comp in result.chain:
            if comp.__class__.__name__ != "Plain":
                continue
            text = getattr(comp, "text", "") or ""
            match = pattern.search(text)
            if not match:
                continue
            hit = True
            want = want or (match.group(1) or "").strip()
            comp.text = pattern.sub("", text).strip()
        if not hit:
            return
        files = [p for p in base.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif")]
        if not files:
            return
        chosen = None
        if want:
            chosen = next((p for p in files if want in p.name), None)
        if chosen is None:
            chosen = random.choice(files)
        try:
            result.chain.append(Image.fromFileSystem(str(chosen)))
            logger.info("[sticker] 发送表情 %s", chosen.name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[sticker] 表情发送失败: %s", exc)

    @filter.on_decorating_result()
    async def finalize_reply(self, event: AstrMessageEvent) -> None:
        """先摘好感度标记，再按上限截断。"""
        self._maybe_reload()
        result = event.get_result()
        if result is None or not getattr(result, "chain", None):
            return

        if self.fav is not None:
            self._apply_favor_tag(event, result)

        self._apply_sticker(result)

        # 短回复折成一行：模型爱写两句换行，看着像连发两条
        try:
            plain = [comp for comp in result.chain if comp.__class__.__name__ == "Plain"]
            total_chars = sum(len((getattr(c, "text", "") or "")) for c in plain)
            if total_chars <= 120:
                for comp in plain:
                    txt = getattr(comp, "text", "") or ""
                    if "\n" in txt:
                        comp.text = re.sub(r"[ \t]*\n+[ \t]*", " ", txt).strip()
        except Exception:  # noqa: BLE001
            pass

        limit = int(self.cfg.get("max_reply_chars", 500) or 0)
        if limit <= 0:
            return
        if self.cfg.get("super_admin_bypass_length", True) and self._is_super_admin(event):
            return

        total = 0
        for comp in result.chain:
            if comp.__class__.__name__ == "Plain":
                total += len(getattr(comp, "text", "") or "")
        if total <= limit:
            return
        budget = limit
        for comp in result.chain:
            if comp.__class__.__name__ != "Plain":
                continue
            text = getattr(comp, "text", "") or ""
            if budget <= 0:
                comp.text = ""
                continue
            if len(text) > budget:
                comp.text = _cut_at_sentence(text, budget)
            budget -= len(comp.text)
        logger.info("[budget] 回复超长（%d 字），已截断到 %d 字", total, limit)

    @filter.on_astrbot_loaded()
    async def patch_group_chime_in(self) -> None:
        """给内置的群聊主动插话加关键词加权与活跃窗口。"""
        if not self.cfg.get("mention_boost_enabled", True):
            return
        try:
            from astrbot.api.platform import MessageType as MT
            from astrbot.builtin_stars.astrbot.group_chat_context import GroupChatContext
        except Exception as exc:  # noqa: BLE001
            logger.warning("[budget] 关键词加权不可用（导入失败）：%s", exc)
            return
        if getattr(GroupChatContext, "_budget_guard_patched", False):
            return

        plugin = self

        async def need_active_reply_with_boost(ctx_self, event):
            try:
                cfg = ctx_self.cfg(event)
            except Exception:  # noqa: BLE001
                return False
            if not cfg["enable_active_reply"]:
                return False
            if event.get_message_type() != MT.GROUP_MESSAGE:
                return False
            if event.is_at_or_wake_command:
                return False
            whitelist = cfg["ar_whitelist"]
            if whitelist and (
                event.unified_msg_origin not in whitelist
                and (event.get_group_id() and event.get_group_id() not in whitelist)
            ):
                return False

            keywords = plugin.cfg.get("mention_boost_keywords") or []
            patterns = plugin.cfg.get("mention_boost_patterns") or []
            text = getattr(event, "message_str", "") or ""
            hit = bool(text) and any(k and k in text for k in keywords)
            if not hit and text:
                for pattern in patterns:
                    try:
                        if pattern and re.search(pattern, text):
                            hit = True
                            break
                    except re.error as exc:
                        logger.warning("[budget] 关键词正则无效 %r: %s", pattern, exc)

            if hit:
                chance = float(plugin.cfg.get("mention_boost_probability", 0.95))
                will = random.random() < chance
                logger.info(
                    "[budget] 群里提到关键词，插话概率 %.0f%% -> %s",
                    chance * 100,
                    "回复" if will else "不回复",
                )
            else:
                base = float(cfg["ar_possibility"])
                warm_ts = plugin.warm.get(event.unified_msg_origin)
                window = float(plugin.cfg.get("warm_window_seconds", 180) or 0)
                if warm_ts and window > 0:
                    age = time.time() - warm_ts
                    if 0 <= age < window:
                        peak = float(plugin.cfg.get("warm_reply_probability", 0.45))
                        base = min(0.95, base + peak * (1 - age / window))
                        logger.info(
                            "[budget] 群活跃窗口：%.0fs 前刚说过话，插话概率 %.0f%%",
                            age,
                            base * 100,
                        )
                will = random.random() < base

            if will:
                await plugin._ensure_conversation(event)
            return will

        GroupChatContext.need_active_reply = need_active_reply_with_boost
        GroupChatContext._budget_guard_patched = True
        logger.info("[budget] 已启用群聊关键词加权插话")
        try:
            import asyncio as _asyncio
            _asyncio.create_task(self._proactive_loop())
            logger.info("[proactive] 主动私聊调度已启动")
        except Exception as exc:  # noqa: BLE001
            logger.warning("[proactive] 启动失败: %s", exc)


    # ---------- 主动私聊 ----------

    async def _proactive_loop(self) -> None:
        import asyncio

        await asyncio.sleep(40)
        while True:
            try:
                await self._proactive_tick()
            except Exception as exc:  # noqa: BLE001
                logger.warning("[proactive] tick 失败: %s", exc)
            await asyncio.sleep(60)

    async def _proactive_make_text(self, umo: str, target: dict) -> str:
        try:
            provider = await self.context.get_using_provider_async(umo)
            if provider is not None:
                hint = target.get("prompt") or "主动找对方说一句话，1~10 个字，口语，不解释为什么找他"
                resp = await provider.text_chat(
                    prompt=hint,
                    session_id="proactive:" + umo,
                    system_prompt=target.get("persona_hint") or None,
                )
                txt = (getattr(resp, "completion_text", "") or "").strip()
                if txt:
                    return txt[:80]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[proactive] 生成文案失败: %s", exc)
        pool = self.cfg.get("proactive_pool") or ["在干嘛", "睡了没", "忙啥呢"]
        return random.choice(pool)

    async def _proactive_tick(self) -> None:
        cfg = self.cfg.get("proactive") or {}
        if not cfg.get("enabled"):
            return
        now = datetime.now()
        qs = int(cfg.get("quiet_start", 0) or 0)
        qe = int(cfg.get("quiet_end", 8) or 0)
        in_quiet = (qs <= now.hour < qe) if qs < qe else (now.hour >= qs or now.hour < qe)
        if in_quiet:
            return
        budget, _spent, ratio, _prob = self._status()
        if budget > 0 and ratio >= 0.9:
            return
        bot = self._aiocqhttp_bot()
        if bot is None:
            return

        state_path = PLUGIN_DIR / "proactive_state.json"
        state = _read_json(state_path, {})
        today = _today()
        changed = False
        for target in cfg.get("targets") or []:
            umo = str(target.get("umo") or "")
            uid = target.get("user_id")
            if not umo or not uid:
                continue
            rec = dict(state.get(umo) or {})
            if rec.get("date") != today:
                rec = {"date": today, "count": 0, "last": rec.get("last", 0)}
            gap = random.uniform(
                float(target.get("min_hours", 4) or 4),
                float(target.get("max_hours", 10) or 10),
            ) * 3600
            if now.timestamp() - float(rec.get("last", 0) or 0) < gap:
                state[umo] = rec
                continue
            if int(rec.get("count", 0) or 0) >= int(target.get("max_per_day", 2) or 2):
                state[umo] = rec
                continue
            if target.get("require_active_today") and rec.get("incoming_date") != today:
                state[umo] = rec
                continue
            text = await self._proactive_make_text(umo, target)
            if not text:
                continue
            try:
                await bot.call_action(
                    "send_private_msg",
                    user_id=int(uid),
                    message=[{"type": "text", "data": {"text": text}}],
                )
                rec["last"] = now.timestamp()
                rec["count"] = int(rec.get("count", 0) or 0) + 1
                state[umo] = rec
                changed = True
                logger.info("[proactive] 主动私聊 %s: %s", uid, text[:40])
            except Exception as exc:  # noqa: BLE001
                logger.warning("[proactive] 发送失败 %s: %s", uid, exc)
        if changed:
            _write_json(state_path, state)

    # ---------- 工具 ----------

    @filter.llm_tool(name="remember")
    async def remember_memory(self, event: AstrMessageEvent, text: str):
        """把值得长期记住的事写进本地记忆（约定、计划、重要事实等）。

        Args:
            text(string): 要记住的一句话，写清楚人和事
        """
        qq, name = self._sender(event)
        return self.memory.append(text, self._scope(event), name or qq)

    @filter.llm_tool(name="search_memory")
    async def search_memory(self, event: AstrMessageEvent, query: str):
        """在本地记忆里检索以前记过的事。对方提到「上次」「之前」时先查这个。

        Args:
            query(string): 要查的关键词或问题，比如「猫的名字」「上周的约定」
        """
        hits = self.memory.search(query, self._scope(event))
        if not hits:
            return "本地记忆还是空的，什么都没记过。"
        return "本地记忆相关记录：\n" + "\n".join(hits)

    @filter.llm_tool(name="set_favorability")
    async def set_favorability(self, event: AstrMessageEvent, who: str, score: int):
        """修改某个人对我的好感度（-100 到 100）。只有超级管理员能用。

        Args:
            who(string): 目标，可以是 QQ 号，也可以是这个人的昵称
            score(number): 新的好感度数值，-100 到 100
        """
        if not self._is_super_admin(event) or self.fav is None:
            return "只有号主能改好感度。"
        target = self._resolve_target(str(who))
        if not target:
            return f"找不到「{who}」，给个准确 QQ 号。"
        qq, name = target
        data = self.fav.load(qq)
        data["score"] = max(-100, min(100, int(score)))
        floor = self.fav.floor.get(qq)
        if floor is not None:
            data["score"] = max(floor, data["score"])
        self.fav.save(qq, data)
        logger.info("[favor] 管理员把 %s 设为 %d", qq, data["score"])
        return f"已把 {name or qq}（{qq}）的好感度设成 {data['score']}。"

    @filter.llm_tool(name="get_favorability")
    async def get_favorability(self, event: AstrMessageEvent, who: str):
        """查询某个人对我的好感度。只有超级管理员能用。

        Args:
            who(string): 目标，可以是 QQ 号，也可以是这个人的昵称
        """
        if not self._is_super_admin(event) or self.fav is None:
            return "这个是秘密。"
        target = self._resolve_target(str(who))
        if not target:
            return f"找不到「{who}」。"
        qq, name = target
        return f"{name or qq}（{qq}）现在的好感度是 {self.fav.score(qq)}。"

    # ---------- 管理员改群昵称 ----------

    def _aiocqhttp_bot(self):
        try:
            for inst in self.context.platform_manager.get_insts():
                bot = getattr(inst, "bot", None)
                if bot is not None and hasattr(bot, "call_action"):
                    return bot
        except Exception as exc:  # noqa: BLE001
            logger.warning("[nick] 获取 aiocqhttp 客户端失败: %s", exc)
        return None

    async def _set_group_card(self, event: AstrMessageEvent, who: str, card: str) -> str:
        gid = event.get_group_id()
        if not gid:
            return "这不是群消息，改不了群昵称。"
        bot = self._aiocqhttp_bot()
        if bot is None:
            return "拿不到 QQ 客户端，改不了名片。"
        try:
            members = await bot.call_action("get_group_member_list", group_id=int(gid))
        except Exception as exc:  # noqa: BLE001
            return f"拿群成员列表失败：{exc}"
        if not isinstance(members, list):
            return "群成员列表格式不对，改不了。"
        target = None
        for m in members:
            card_name = str(m.get("card") or "")
            nick = str(m.get("nickname") or "")
            if who and (who == card_name or who == nick or who in card_name or who in nick):
                target = m
                break
        if not target:
            return f"群里没找到「{who}」，说全一点。"
        uid = target.get("user_id")
        try:
            await bot.call_action(
                "set_group_card", group_id=int(gid), user_id=int(uid), card=card
            )
        except Exception as exc:  # noqa: BLE001
            return f"改名片失败（可能我可不是管理员）：{exc}"
        logger.info("[nick] 把 %s(%s) 的群名片改成 %s", who, uid, card)
        return f"行，把 {who} 的群名片改成「{card}」了。"

    # ---------- 管理员自然语言直连指令 ----------

    @filter.event_message_type(filter.EventMessageType.ALL, priority=1)
    async def admin_direct_command(self, event: AstrMessageEvent):
        """管理员下明确指令时直接执行，不经模型，避免它讲道理拒绝。"""
        if not self._is_super_admin(event):
            return
        text = (getattr(event, "message_str", "") or "").strip()
        if not text:
            return

        # 切换人格（仅管理员私聊）
        low = text.lower()
        wants_xdd = "xdd" in low and any(k in text for k in ("切", "换", "用", "学", "变"))
        wants_default = ("大肥鱼" in text or "默认" in text) and any(
            k in text for k in ("切回", "换回", "恢复", "切到", "换成", "用")
        )
        if wants_xdd or wants_default:
            umo = event.unified_msg_origin
            if "FriendMessage" not in umo:
                yield event.plain_result("切人格只在私聊里生效。")
                event.stop_event()
                return
            target = "xdd" if wants_xdd else "default"
            try:
                cm = self.context.conversation_manager
                cid = await cm.get_curr_conversation_id(umo)
                if not cid:
                    cid = await cm.new_conversation(umo, platform_id=event.get_platform_id())
                await cm.update_conversation(umo, conversation_id=cid, persona_id=target)
                label = "xdd（学你说话）" if target == "xdd" else "大肥鱼"
                logger.info("[persona] %s 切换到 %s", umo, target)
                yield event.plain_result(f"行，这个私聊换成 {label} 了。")
            except Exception as exc:  # noqa: BLE001
                logger.warning("[persona] 切换失败: %s", exc)
                yield event.plain_result(f"切换失败：{exc}")
            event.stop_event()
            return

        remember_match = re.match(r"^记住[：:，,\s]*(.+)$", text)
        if remember_match:
            result = self.memory.append(remember_match.group(1), self._scope(event), "管理员")
            yield event.plain_result(result)
            event.stop_event()
            return

        card_match = re.search(
            r"把\s*(.+?)\s*的?(?:群)?昵称\s*(?:改|设|换)(?:成|为)\s*([^，,。；;\s]+)", text
        ) or re.search(
            r"把\s*(.+?)\s*(?:变成|改成|改名为)\s*([^，,。；;\s]+)", text
        )
        if card_match:
            reply = await self._set_group_card(event, card_match.group(1), card_match.group(2))
            yield event.plain_result(reply)
            event.stop_event()
            return

        if self.fav is None or "好感度" not in text:
            return

        set_match = re.search(
            r"(\S+?)\s*的?好感度\s*(?:设|改|调|定)(?:成|为|到)?\s*(-?\d{1,3})", text
        )
        if set_match:
            target = self._resolve_target(set_match.group(1))
            if not target:
                yield event.plain_result(f"找不到「{set_match.group(1)}」，给个 QQ 号。")
                event.stop_event()
                return
            qq, name = target
            data = self.fav.load(qq)
            data["score"] = max(-100, min(100, int(set_match.group(2))))
            floor = self.fav.floor.get(qq)
            if floor is not None:
                data["score"] = max(floor, data["score"])
            self.fav.save(qq, data)
            logger.info("[favor] 管理员直连指令：%s -> %d", qq, data["score"])
            yield event.plain_result(f"行，{name or qq}（{qq}）的好感度改成 {data['score']} 了。")
            event.stop_event()
            return

        get_match = re.search(r"(\S+?)\s*的?好感度\s*(?:是|多少|查|咋样|怎么样)", text)
        if get_match:
            target = self._resolve_target(get_match.group(1))
            if target:
                qq, name = target
                yield event.plain_result(f"{name or qq}（{qq}）现在是 {self.fav.score(qq)}。")
                event.stop_event()

    # ---------- 指令 ----------

    @filter.command("budget")
    async def budget_cmd(self, event: AstrMessageEvent):
        """查看今日额度使用情况。"""
        self._maybe_reload()
        budget, spent, ratio, prob = self._status()
        left = max(0.0, budget - spent)
        white = "是" if self._is_whitelisted(event) else "否"
        yield event.plain_result(
            f"今日已用 {spent:.2f}/{budget:.2f} 元（{ratio * 100:.0f}%），还剩 {left:.2f} 元，"
            f"回复意愿 {prob * 100:.0f}%，已完成 {self.state.get('calls', 0)} 次模型调用。"
            f"你在白名单里：{white}。"
        )

    @filter.command("fav")
    async def fav_cmd(self, event: AstrMessageEvent):
        """只有号主能查好感度数字，其他人问就是秘密。"""
        self._maybe_reload()
        qq, _name = self._sender(event)
        if self.fav is None:
            yield event.plain_result("好感度系统没开。")
            return
        if qq not in self.fav.floor:
            yield event.plain_result("这个是秘密，不告诉你。")
            return
        data = self.fav.load(qq)
        yield event.plain_result(
            f"你在我这儿的好感度：{data['score']}/100。存档：{self.fav.path(qq).name}"
        )
