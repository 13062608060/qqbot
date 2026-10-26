import json
import sqlite3

DB = r"D:\deepseek-work\qqbot\astrbot\data\data_v4.db"
db = sqlite3.connect(DB)
cur = db.cursor()
cur.execute("SELECT user_id, conversation_id, content, persona_id FROM conversations ORDER BY updated_at DESC LIMIT 6")
rows = cur.fetchall()
for umo, cid, content, persona_id in rows:
    data = json.loads(content) if content else []
    print("==", umo, "| persona:", persona_id, "| 条目:", len(data))
    for item in data[-3:]:
        body = json.dumps(item, ensure_ascii=False)
        print("  ", item.get("role"), "|", body[:160])
