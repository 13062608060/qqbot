import sqlite3

DB = r"D:\deepseek-work\qqbot\astrbot\data\data_v4.db"
UMO = "qq-onebot:GroupMessage:871610977"

db = sqlite3.connect(DB)
cur = db.cursor()
cur.execute("UPDATE conversations SET content='[]' WHERE user_id=?", (UMO,))
db.commit()
print("cleared rows:", cur.rowcount)

cur.execute("SELECT user_id, LENGTH(content) FROM conversations WHERE user_id LIKE '%GroupMessage%'")
print(cur.fetchall())
