import json
import sqlite3

DB = r"D:\deepseek-work\qqbot\astrbot\data\data_v4.db"
db = sqlite3.connect(DB)
cur = db.cursor()
cur.execute("SELECT content FROM conversations WHERE user_id LIKE '%20002%'")
for (content,) in cur.fetchall():
    data = json.loads(content) if content else []
    print("条目:", len(data))
    for item in data[-6:]:
        text = json.dumps(item, ensure_ascii=False)
        print(item.get("role"), "|", text[:300])
