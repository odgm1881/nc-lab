from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.core import observability
from app.core.observability import FixedWindowRateLimiter, RequestMetrics


def test_rate_limiter_releases_key_after_window() -> None:
    limiter = FixedWindowRateLimiter()
    assert limiter.allow("ip:login", 2, now=0)
    assert limiter.allow("ip:login", 2, now=1)
    assert not limiter.allow("ip:login", 2, now=2)
    assert limiter.allow("ip:login", 2, now=61)


def test_prometheus_metrics_do_not_include_paths_or_payloads() -> None:
    metrics = RequestMetrics()
    metrics.observe("GET", 200, 0.125)
    rendered = metrics.render()
    assert 'nklab_http_requests_total{method="GET",status="200"} 1' in rendered
    assert 'nklab_http_request_duration_seconds_sum{method="GET"} 0.125000' in rendered


def test_login_and_token_share_one_rate_limit_budget(monkeypatch) -> None:
    app = FastAPI()

    @app.post("/api/auth/login", status_code=204)
    def login() -> None:
        return None

    @app.post("/api/auth/token", status_code=204)
    def token() -> None:
        return None

    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "auth_rate_limit_per_minute", 1)
    monkeypatch.setattr(observability, "auth_rate_limiter", FixedWindowRateLimiter())
    observability.register_request_logging(app)

    client = TestClient(app)
    assert client.post("/api/auth/login").status_code == 204
    response = client.post("/api/auth/token")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
