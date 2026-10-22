"""Inspect AstrBot OpenAPI schemas for the chat / login / provider-test endpoints."""

import json
import pathlib

SPEC = pathlib.Path(__file__).with_name("_openapi.json")


def deref(spec, node):
    ref = node.get("$ref")
    if ref:
        return spec["components"]["schemas"][ref.split("/")[-1]], ref.split("/")[-1]
    return node, None


def show(spec, path, method):
    op = spec["paths"][path][method]
    print(f"== {method.upper()} {path}")
    params = [(p.get("name"), p.get("in"), p.get("required")) for p in op.get("parameters", [])]
    if params:
        print("  params:", params)
    body = op.get("requestBody")
    if not body:
        print("  body: none")
        return
    schema = body["content"]["application/json"]["schema"]
    model, name = deref(spec, schema)
    if name:
        print(f"  body model: {name} | required: {model.get('required')}")
        for key, val in model.get("properties", {}).items():
            kind = val.get("type") or ("anyOf" if "anyOf" in val else None) or val.get("$ref")
            print(f"   - {key}: {kind} default={val.get('default')}")
    else:
        print("  schema:", schema)


def main() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    for path, method in [
        ("/api/v1/chat", "post"),
        ("/api/v1/auth/login", "post"),
        ("/api/v1/providers/test", "post"),
    ]:
        if path in spec["paths"]:
            show(spec, path, method)


if __name__ == "__main__":
    main()
