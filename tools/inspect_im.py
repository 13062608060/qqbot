import json

SPEC = r"D:\deepseek-work\qqbot\tools\_openapi.json"
spec = json.load(open(SPEC, encoding="utf-8"))
op = spec["paths"]["/api/v1/im/messages"]["post"]
schema = op["requestBody"]["content"]["application/json"]["schema"]
ref = schema.get("$ref")
print("ref:", ref)
if ref:
    model = spec["components"]["schemas"][ref.split("/")[-1]]
    print("required:", model.get("required"))
    for key, val in model.get("properties", {}).items():
        kind = val.get("type") or val.get("anyOf") or val.get("$ref")
        print(" -", key, kind, "|", (val.get("description") or "")[:70])
