import json
import urllib.request

import jsonschema

schema = json.load(urllib.request.urlopen(
    "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json"))
doc = json.load(open("server.json", encoding="utf-8"))

jsonschema.validate(doc, schema)
print("server.json is schema-valid")

print(f"  name        {doc['name']}")
print(f"  version     {doc['version']}")
print(f"  description {len(doc['description'])}/100 chars")
print(f"  title       {len(doc['title'])}/100 chars")
print(f"  remotes     {len(doc['remotes'])}")
print(f"  packages    {len(doc['packages'])}")
print(f"  remote url  {doc['remotes'][0]['url']}")

assert doc["remotes"], "remotes must not be empty"
assert doc["remotes"][0]["type"] == "streamable-http"
assert doc["remotes"][0]["url"].startswith("https://")
print("\nOK — the registry entry points at a real remote endpoint")
