import json

from app.config import Settings
from app.modules.nk_exchange.adapters import NkApiAdapter, TransportResponse
from app.modules.nk_exchange.domain import (
    build_nk_feed,
    normalize_feed_status,
    validate_nk_feed_contract,
)

PAYLOAD = {
    "card_id": "card-1",
    "name": "Футболка",
    "category_code": "6109",
    "gtin": "4600000000015",
    "attributes": {"brand": "Лаб", "color": "чёрный", "ignored": "value"},
    "rd_data": {"number": "ЕАЭС N RU Д-RU.РА01.А.00001/26", "date": "2026-01-10"},
}


class FakeTransport:
    def __init__(self, response: TransportResponse):
        self.response = response
        self.calls = []

    def request(self, method, url, headers, body, timeout):
        self.calls.append((method, url, headers, body, timeout))
        return self.response


def test_build_feed_uses_only_verified_attribute_mapping():
    feed = build_nk_feed(
        PAYLOAD, {"color": "123", "rd_number_date": "23557"}, {"6109": 77}
    )

    assert feed["good_name"] == "Футболка"
    assert feed["categories"] == [77]
    assert feed["good_attrs"] == [
        {"attr_id": "123", "attr_value": "чёрный"},
        {
            "attr_id": "23557",
            "attr_value": "ЕАЭС N RU Д-RU.РА01.А.00001/26:::2026-01-10",
        },
    ]
    assert feed["identified_by"][0]["level"] == "trade-unit"
    assert "ignored" not in json.dumps(feed, ensure_ascii=False)


def test_contract_rejects_structurally_invalid_feed():
    try:
        validate_nk_feed_contract(
            {
                "gtin": "4600000000015",
                "tnved": "6109",
                "good_name": "Футболка",
                "brand": "Лаб",
                "categories": ["not-an-integer"],
                "identified_by": [{}],
                "good_attrs": [{"attr_id": "123", "attr_value": "чёрный"}],
            }
        )
    except ValueError as exc:
        assert "categories" in str(exc)
    else:
        raise AssertionError("Некорректный контракт должен быть отклонён")


def test_api_adapter_submits_feed_and_returns_processing():
    transport = FakeTransport(
        TransportResponse(
            200,
            b'{"apiversion":3,"result":{"feed_id":"2131"}}',
            {},
        )
    )
    settings = Settings(
        _env_file=None,
        nk_api_enabled=True,
        nk_api_key="secret",
        nk_attribute_map={"color": "123"},
        nk_category_map={"6109": 77},
    )

    result = NkApiAdapter(settings, transport).send(PAYLOAD, "idem-1234")

    assert result.status == "processing"
    assert result.external_id == "2131"
    method, url, headers, body, timeout = transport.calls[0]
    assert method == "POST"
    assert "/v3/feed?" in url and "apikey=secret" in url
    assert headers["Content-Type"].startswith("application/json")
    assert json.loads(body)["good_attrs"][0]["attr_id"] == "123"
    assert timeout == 15


def test_api_adapter_marks_rate_limit_as_retryable():
    transport = FakeTransport(
        TransportResponse(429, b'{"error":{"message":"limit"}}', {"Retry-After": "60"})
    )
    settings = Settings(
        _env_file=None,
        nk_api_enabled=True,
        nk_api_key="secret",
        nk_attribute_map={"color": "123"},
        nk_category_map={"6109": 77},
    )

    result = NkApiAdapter(settings, transport).send(PAYLOAD, "idem-1234")

    assert result.status == "failed"
    assert result.error_code == "NK_HTTP_429"
    assert result.retryable is True


def test_api_adapter_masks_secrets_echoed_by_remote():
    transport = FakeTransport(
        TransportResponse(
            400,
            b'{"error":"bad","debug":{"apikey":"secret","token":"bearer"}}',
            {},
        )
    )
    settings = Settings(
        _env_file=None,
        nk_api_enabled=True,
        nk_api_key="secret",
        nk_attribute_map={"color": "123"},
        nk_category_map={"6109": 77},
    )

    result = NkApiAdapter(settings, transport).send(PAYLOAD, "idem-1234")

    assert result.response["body"]["debug"] == {"apikey": "***", "token": "***"}


def test_normalize_feed_status_and_error():
    result = normalize_feed_status(
        {
            "result": {
                "feed_id": 42,
                "status": "Moderated",
                "item": [
                    {
                        "attribute_id": 2716,
                        "status_code": 5,
                        "message": "Неверный объём",
                    }
                ],
            }
        }
    )

    assert result.status == "failed"
    assert result.external_id == "42"
    assert result.error_code == "5"
    assert result.error == "Неверный объём"
