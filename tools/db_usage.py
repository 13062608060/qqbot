import json
import sqlite3

DB = r"D:\deepseek-work\qqbot\astrbot\data\data_v4.db"
db = sqlite3.connect(DB)
cur = db.cursor()
cur.execute(
    "SELECT user_id, token_usage, content, created_at, updated_at FROM conversations ORDER BY token_usage DESC"
)
for umo, usage, content, created, updated in cur.fetchall():
    try:
        data = json.loads(content) if content else []
    except Exception:  # noqa: BLE001
        data = []
    chars = sum(len(json.dumps(x, ensure_ascii=False)) for x in data)
    print(f"{umo:<45} tokens={usage:<8} 轮数={len(data)//2:<3} 字数={chars:<7} 更新={updated[:16]}")
