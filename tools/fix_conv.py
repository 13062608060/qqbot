"""把 3392926635 的所有会话行都绑到 xdd，并打印 preferences。"""

import sqlite3

DB = r"D:\deepseek-work\qqbot\astrbot\data\data_v4.db"
db = sqlite3.connect(DB)
cur = db.cursor()
cur.execute("UPDATE conversations SET persona_id='xdd' WHERE user_id LIKE '%3392926635%'")
db.commit()
print("updated rows:", cur.rowcount)

cur.execute("SELECT conversation_id, persona_id, LENGTH(content) FROM conversations WHERE user_id LIKE '%3392926635%'")
for r in cur.fetchall():
    print(r)

cur.execute("SELECT scope, scope_id, key, value FROM preferences WHERE scope_id LIKE '%3392926635%'")
for r in cur.fetchall():
    print("pref:", r)
