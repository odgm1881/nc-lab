from fastapi.testclient import TestClient

from app.config import settings


def test_health_endpoints_and_correlation_id(client: TestClient) -> None:
    live = client.get("/api/health/live", headers={"x-correlation-id": "test-request"})
    assert live.status_code == 200
    assert live.json()["status"] == "ok"
    assert live.headers["x-correlation-id"] == "test-request"

    ready = client.get("/api/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"

    metrics = client.get("/api/metrics")
    assert metrics.status_code == 200
    assert "nklab_http_requests_total" in metrics.text


def test_import_rejects_file_over_limit(auth_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_upload_bytes", 8)
    response = auth_client.post(
        "/api/import/preview",
        files={"file": ("too-large.csv", b"123456789", "text/csv")},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
