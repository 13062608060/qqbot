import json
import sqlite3

DB = r"D:\deepseek-work\qqbot\astrbot\data\data_v4.db"
db = sqlite3.connect(DB)
cur = db.cursor()
cur.execute("SELECT user_id, content FROM conversations WHERE user_id LIKE '%1044846381%'")
for umo, content in cur.fetchall():
    data = json.loads(content) if content else []
    print(umo, "条目:", len(data))
    for i, item in enumerate(data):
        body = json.dumps(item, ensure_ascii=False)
        flag = ""
        if "results" in body or "tool" in body.lower():
            flag = " <== 含工具/搜索结果"
        print(f"{i:>2} role={item.get('role')} len={len(body)}{flag}")
        print("   ", body[:160].replace("\n", " "))
