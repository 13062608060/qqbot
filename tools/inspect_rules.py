import json

SPEC = r"D:\deepseek-work\qqbot\tools\_openapi.json"
spec = json.load(open(SPEC, encoding="utf-8"))

for path, method in [
    ("/api/v1/sessions/rules", "post"),
    ("/api/v1/sessions/rules", "get"),
]:
    op = spec["paths"][path][method]
    print("==", method.upper(), path, "|", op.get("summary"))
    body = op.get("requestBody")
    if body:
        schema = body["content"]["application/json"]["schema"]
        ref = schema.get("$ref")
        if ref:
            model = spec["components"]["schemas"][ref.split("/")[-1]]
            print("  必填:", model.get("required"))
            for key, val in model.get("properties", {}).items():
                kind = val.get("type") or val.get("anyOf") or val.get("$ref")
                print("   -", key, kind, "|", (val.get("description") or "")[:60])
        else:
            print("  schema:", schema)
