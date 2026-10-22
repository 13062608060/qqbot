import sys
sys.path.insert(0, r"D:\deepseek-work\qqbot\astrbot\data\plugins\astrbot_plugin_budget_guard")
from memory import MemoryStore
m = MemoryStore(r"D:\deepseek-work\qqbot\astrbot\data\大肥鱼记忆")
for q in ["你还记得我那只猫叫什么吗？是什么猫？", "我的猫", "团子"]:
    print(q, "->", m.search(q, "global"))
