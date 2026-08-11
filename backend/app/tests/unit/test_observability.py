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
