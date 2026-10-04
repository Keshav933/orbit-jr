from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)
for path in ("/", "/api/v1/health", "/api/v1/version"):
    response = client.get(path)
    response.raise_for_status()
    print(path, response.json())
