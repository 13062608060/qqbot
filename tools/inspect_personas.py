import json
import urllib.request

BASE = "http://127.0.0.1:6185"
SPEC = r"D:\deepseek-work\qqbot\tools\_openapi.json"


def call(path, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return getattr(exc, "code", 0), str(exc)


status, body = call("/api/v1/auth/login", {"username": "astrbot", "password": "Flushdns97!"})
token = json.loads(body)["data"]["token"]

status, body = call("/api/v1/personas", None, token)
print("personas:", status)
data = json.loads(body).get("data")
print(json.dumps(data, ensure_ascii=False, indent=2)[:1500])

spec = json.load(open(SPEC, encoding="utf-8"))
schema = spec["paths"]["/api/v1/personas"]["post"]["requestBody"]["content"]["application/json"]["schema"]
ref = schema.get("$ref")
model = spec["components"]["schemas"][ref.split("/")[-1]]
print("\n== Persona 字段 ==")
print("required:", model.get("required"))
for key, val in model.get("properties", {}).items():
    kind = val.get("type") or val.get("anyOf") or val.get("$ref")
    desc = (val.get("description") or "")[:60]
    print(" -", key, "|", kind, "|", desc)
