import json
import sqlite3

DB = r"D:\deepseek-work\qqbot\astrbot\data\data_v4.db"
db = sqlite3.connect(DB)
cur = db.cursor()

cur.execute(
    "SELECT user_id, conversation_id, content, token_usage FROM conversations "
    "WHERE user_id LIKE '%GroupMessage%'"
)
for umo, cid, content, usage in cur.fetchall():
    print(f"== {umo} | {cid} | tokens={usage}")
    try:
        data = json.loads(content) if content else []
    except Exception:  # noqa: BLE001
        print("  content not json:", str(content)[:200])
        continue
    print(f"  条目数: {len(data)}")
    joined = json.dumps(data, ensure_ascii=False)
    print("  含“周报”:", "周报" in joined)
    for item in data[:6]:
        print("  -", str(item)[:180])
