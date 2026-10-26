"""给插件加「主动私聊」：定时挑时间给指定人发一句话。

实现方式：在类里追加方法 + 在 on_astrbot_loaded 里起一个后台任务。
为了不破坏现有 main.py，本脚本做文本插入。
"""

import io
import sys
from pathlib import Path

SRC = Path(r"D:\deepseek-work\qqbot\astrbot\data\plugins\astrbot_plugin_budget_guard\main.py")
text = SRC.read_text(encoding="utf-8")

# 1) 配置默认值
if '"proactive"' not in text:
    text = text.replace(
        '    "mixed_mode_umos": {},',
        '    "mixed_mode_umos": {},\n'
        '    "proactive": {"enabled": False, "quiet_start": 0, "quiet_end": 8, "targets": []},\n'
        '    "proactive_pool": ["在干嘛", "睡了没", "忙啥呢", "人呢"],',
    )

# 2) 方法：插在 "    # ---------- 工具 ----------" 之前
METHODS = '''
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

    # ---------- 工具 ----------'''

if "_proactive_tick" not in text:
    text = text.replace("    # ---------- 工具 ----------", METHODS, 1)

# 3) 启动任务
if "self._proactive_loop" not in text:
    text = text.replace(
        '        logger.info("[budget] 已启用群聊关键词加权插话")',
        '        logger.info("[budget] 已启用群聊关键词加权插话")\n'
        '        try:\n'
        '            import asyncio as _asyncio\n'
        '            _asyncio.create_task(self._proactive_loop())\n'
        '            logger.info("[proactive] 主动私聊调度已启动")\n'
        '        except Exception as exc:  # noqa: BLE001\n'
        '            logger.warning("[proactive] 启动失败: %s", exc)',
    )

SRC.write_text(text, encoding="utf-8")
print("patched, size:", len(text))
