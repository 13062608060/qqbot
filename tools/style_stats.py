"""分析 1120 条原话，输出可直接喂给模型的风格统计。"""

import json
import re
from collections import Counter
from pathlib import Path

SRC = Path(r"D:\deepseek-work\qqbot\data\my_messages_deep.txt")
OUT = Path(r"D:\deepseek-work\qqbot\data\style_stats.json")

lines = [l.strip() for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
total = len(lines)

lengths = [len(l) for l in lines]
buckets = Counter()
for n in lengths:
    if n <= 2:
        buckets["1-2字"] += 1
    elif n <= 5:
        buckets["3-5字"] += 1
    elif n <= 10:
        buckets["6-10字"] += 1
    elif n <= 20:
        buckets["11-20字"] += 1
    else:
        buckets["20字以上"] += 1

punct = Counter()
for ch in "，。？！…、~ ":
    punct[ch] = sum(l.count(ch) for l in lines)

end_with_punct = sum(1 for l in lines if l and l[-1] in "，。？！…、~")
no_punct = sum(1 for l in lines if not re.search(r"[，。？！…、]", l))
english = Counter(w for l in lines for w in re.findall(r"[A-Za-z]{2,}", l))
emoji = Counter(ch for l in lines for ch in l if ord(ch) > 0x1F000)

# 高频短语（2-6 字滑窗，出现 >= 8 次）
phrase = Counter()
for l in lines:
    for n in range(2, 7):
        for i in range(len(l) - n + 1):
            sub = l[i : i + n]
            if re.search(r"[\u4e00-\u9fa5]", sub):
                phrase[sub] += 1

profanity = sum(1 for l in lines if any(w in l for w in ("他妈", "tm", "卧槽", "草", "几把", "操")))
question = sum(1 for l in lines if l.endswith("？") or l == "?" or "吗" in l or "啥" in l)

stats = {
    "总数": total,
    "长度分布": dict(buckets),
    "平均长度": round(sum(lengths) / total, 1),
    "最长": max(lengths),
    "标点": dict(punct),
    "结尾带标点": end_with_punct,
    "完全无标点": no_punct,
    "英文词": dict(english.most_common(15)),
    "emoji": dict(emoji.most_common(10)),
    "高频短语": {p: c for p, c in phrase.most_common(40) if c >= 8},
    "带脏话": profanity,
    "疑问句": question,
    "样例_短": [l for l in lines if len(l) <= 4][:30],
    "样例_长": sorted(lines, key=len, reverse=True)[:10],
}
OUT.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in stats.items() if not k.startswith("样例")}, ensure_ascii=False, indent=2)[:2000])
