import httpx
import uuid
import traceback

delivery_id = str(uuid.uuid4())
print(f"Using delivery_id: {delivery_id}")

payload = {
    "action": "opened",
    "installation": {"id": 12345},
    "repository": {
        "owner": {"login": "prerna020"},
        "name": "DevBrief"
    },
    "pull_request": {
        "number": 99,
        "user": {"login": "prerna020"},
        "head": {"sha": "abc123test"}
    }
}

headers = {
    "X-GitHub-Event": "pull_request",
    "X-GitHub-Delivery": delivery_id,
}

try:
    r = httpx.post("http://localhost:8000/webhook", json=payload, headers=headers, timeout=30.0)
    print(f"Status: {r.status_code}")
    print(f"Headers: {dict(r.headers)}")
    print(f"Body: {r.text}")
except Exception as e:
    print(f"Exception: {e}")
    traceback.print_exc()
