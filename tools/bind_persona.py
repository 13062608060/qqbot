"""给 3392926635 的私聊预建会话，并绑定 xdd 人格。"""

import sqlite3
import uuid
from datetime import datetime, timezone

DB = r"D:\deepseek-work\qqbot\astrbot\data\data_v4.db"
UMO = "qq-onebot:FriendMessage:3392926635"
PERSONA = "xdd"

now = datetime.now(timezone.utc).isoformat(sep=" ")
db = sqlite3.connect(DB)
cur = db.cursor()

cur.execute("SELECT conversation_id FROM conversations WHERE user_id=?", (UMO,))
row = cur.fetchone()
if row:
    cur.execute(
        "UPDATE conversations SET persona_id=?, updated_at=? WHERE user_id=?", (PERSONA, now, UMO)
    )
    print("已更新现有会话:", row[0], "-> persona", PERSONA)
else:
    cur.execute("SELECT COALESCE(MAX(inner_conversation_id), 0) + 1 FROM conversations")
    inner = cur.fetchone()[0]
    cid = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO conversations (created_at, updated_at, inner_conversation_id, conversation_id,"
        " platform_id, user_id, content, title, persona_id, token_usage)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (now, now, inner, cid, "qq-onebot", UMO, "[]", None, PERSONA, 0),
    )
    print("已新建会话:", cid, "persona", PERSONA)

db.commit()
cur.execute("SELECT user_id, conversation_id, persona_id FROM conversations WHERE user_id=?", (UMO,))
print(cur.fetchall())
