import hashlib
import json

CFG = r"D:\deepseek-work\qqbot\astrbot\data\cmd_config.json"
cfg = json.load(open(CFG, encoding="utf-8-sig"))
dash = cfg["dashboard"]
stored = dash["pbkdf2_password"]
_, iters, salt, digest = stored.split("$")
print("stored pbkdf2:", stored)
print("digest len:", len(digest), "| salt len:", len(salt))

candidates = {
    "Flushdns97!": "Flushdns97!",
    "xZgL3zjm...": "xZgL3zjm4K2rzwTBhmDXagEF",
    "md5(Flushdns97!)": hashlib.md5(b"Flushdns97!").hexdigest(),
    "md5(xZgL3...)": hashlib.md5(b"xZgL3zjm4K2rzwTBhmDXagEF").hexdigest(),
}
for label, cand in candidates.items():
    h = hashlib.pbkdf2_hmac("sha256", cand.encode(), bytes.fromhex(salt), int(iters)).hex()
    print(f"{label:20} -> {'MATCH' if h == digest else 'no'}")

print("config md5:", dash.get("password"))
print("md5(Flushdns97!) =", hashlib.md5(b"Flushdns97!").hexdigest())
