import sqlite3

db = sqlite3.connect(r"D:\deepseek-work\qqbot\astrbot\data\data_v4.db")
cur = db.cursor()
cur.execute("SELECT user_id, persona_id FROM conversations WHERE user_id LIKE '%1044846381%'")
for r in cur.fetchall():
    print(r)
