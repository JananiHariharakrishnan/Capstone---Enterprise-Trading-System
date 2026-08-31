# tests/test_extract.py

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from analytics_etl.errors import (
    NetworkError,
    PayloadError,
    RateLimitError,
    ServerError,
    SymbolRequestError,
)
from analytics_etl.pipeline.extract import _request


def test_429_is_rate_limited():

    response = Mock()
    response.status_code = 429
    response.headers = {
        "Retry-After": "120"
    }

    with patch(
        "analytics_etl.pipeline.extract.requests.get",
        return_value=response,
    ):

        with pytest.raises(RateLimitError):
            _request(
                "INFY.NS",
                "2026-08-01",
                "2026-08-26",
                "fake-test-key",
            )


def test_4xx_fails_symbol():

    response = Mock()
    response.status_code = 404
    response.text = "symbol not found"

    with patch(
        "analytics_etl.pipeline.extract.requests.get",
        return_value=response,
    ):

        with pytest.raises(SymbolRequestError):
            _request(
                "BAD.NS",
                "2026-08-01",
                "2026-08-26",
                "fake-test-key",
            )


def test_network_error_retries_with_growing_backoff():
    response = Mock(status_code=200)
    response.json.return_value = {"data": {"candles": []}}

    with patch(
        "analytics_etl.pipeline.extract.requests.get",
        side_effect=[
            __import__("requests").exceptions.Timeout(),
            __import__("requests").exceptions.ConnectionError(),
            response,
        ],
    ) as request, patch("analytics_etl.pipeline.extract.time.sleep") as sleep:
        result = _request(
            "INFY.NS",
            "2026-08-01",
            "2026-08-26",
            "fake-test-key",
        )

    assert result == {"data": {"candles": []}}
    assert request.call_count == 3
    assert [call.args[0] for call in sleep.call_args_list] == [1, 2]


def test_network_error_after_retries_is_classified():
    with patch(
        "analytics_etl.pipeline.extract.requests.get",
        side_effect=__import__("requests").exceptions.Timeout(),
    ), patch("analytics_etl.pipeline.extract.time.sleep"):
        with pytest.raises(NetworkError):
            _request(
                "INFY.NS",
                "2026-08-01",
                "2026-08-26",
                "fake-test-key",
            )


def test_extract_skips_a_4xx_symbol_and_continues(tmp_path: Path):
    bad = SymbolRequestError("BAD.NS: HTTP 404: symbol not found")
    good = {"data": {"symbol": "INFY.NS", "candles": []}}

    with patch("analytics_etl.pipeline.extract.CACHE_DIR", tmp_path), patch(
        "analytics_etl.pipeline.extract._get_api_key", return_value="fake-test-key"
    ), patch("analytics_etl.pipeline.extract._request", side_effect=[bad, good]):
        result = __import__("analytics_etl.pipeline.extract", fromlist=["extract"]).extract(
            symbols=["BAD.NS", "INFY.NS"]
        )

    assert result == {"INFY.NS": good}


def test_invalid_json_response_is_classified():
    response = Mock(status_code=200)
    response.json.side_effect = ValueError("not json")

    with patch("analytics_etl.pipeline.extract.requests.get", return_value=response):
        with pytest.raises(PayloadError):
            _request("INFY.NS", "2026-08-01", "2026-08-26", "fake-test-key")


def test_server_error_after_retries_is_classified():
    response = Mock(status_code=503)

    with patch("analytics_etl.pipeline.extract.requests.get", return_value=response), patch(
        "analytics_etl.pipeline.extract.time.sleep"
    ):
        with pytest.raises(ServerError):
            _request("INFY.NS", "2026-08-01", "2026-08-26", "fake-test-key")


def test_corrupt_cache_is_ignored_and_replaced(tmp_path: Path):
    cache_file = tmp_path / "INFY.NS_2026-08-01_2026-08-26.json"
    cache_file.write_text("not json", encoding="utf-8")
    good = {"data": {"symbol": "INFY.NS", "candles": []}}

    with patch("analytics_etl.pipeline.extract.CACHE_DIR", tmp_path), patch(
        "analytics_etl.pipeline.extract._get_api_key", return_value="fake-test-key"
    ), patch("analytics_etl.pipeline.extract._request", return_value=good):
        result = __import__("analytics_etl.pipeline.extract", fromlist=["extract"]).extract(
            symbols=["INFY.NS"],
            start_date="2026-08-01",
            end_date="2026-08-26",
        )

    assert result == {"INFY.NS": good}
    assert cache_file.read_text(encoding="utf-8").startswith("{")
