from fastapi.testclient import TestClient
from langgraph_fabric_api.app import _extract_user_id, app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_extract_user_id_no_token():
    assert _extract_user_id(None) == "local-user"


def test_extract_user_id_preferred_username():
    # JWT payload: {"preferred_username": "alice@example.com", "sub": "abc123"}
    token = "header.eyJwcmVmZXJyZWRfdXNlcm5hbWUiOiAiYWxpY2VAZXhhbXBsZS5jb20iLCAic3ViIjogImFiYzEyMyJ9.sig"
    assert _extract_user_id(token) == "alice@example.com"


def test_extract_user_id_falls_back_to_sub():
    # JWT payload: {"sub": "abc123"}
    token = "header.eyJzdWIiOiAiYWJjMTIzIn0.sig"
    assert _extract_user_id(token) == "abc123"


def test_extract_user_id_invalid_token():
    assert _extract_user_id("not-a-jwt") == "unknown"
