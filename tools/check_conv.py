import json
import sqlite3

DB = r"D:\deepseek-work\qqbot\astrbot\data\data_v4.db"
db = sqlite3.connect(DB)
cur = db.cursor()
cur.execute("SELECT user_id, conversation_id, persona_id, updated_at FROM conversations WHERE user_id LIKE '%3392926635%'")
rows = cur.fetchall()
print("rows:", len(rows))
for r in rows:
    print(r)
