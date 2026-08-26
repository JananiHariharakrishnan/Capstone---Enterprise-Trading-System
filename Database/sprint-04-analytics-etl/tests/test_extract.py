# tests/test_extract.py

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from analytics_etl.extract import (
    RateLimitError,
    SymbolRequestError,
    _request,
)


def test_429_is_rate_limited():

    response = Mock()
    response.status_code = 429
    response.headers = {
        "Retry-After": "120"
    }

    with patch(
        "analytics_etl.extract.requests.get",
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
        "analytics_etl.extract.requests.get",
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
        "analytics_etl.extract.requests.get",
        side_effect=[
            __import__("requests").exceptions.Timeout(),
            __import__("requests").exceptions.ConnectionError(),
            response,
        ],
    ) as request, patch("analytics_etl.extract.time.sleep") as sleep:
        result = _request(
            "INFY.NS",
            "2026-08-01",
            "2026-08-26",
            "fake-test-key",
        )

    assert result == {"data": {"candles": []}}
    assert request.call_count == 3
    assert [call.args[0] for call in sleep.call_args_list] == [1, 2]


def test_extract_skips_a_4xx_symbol_and_continues(tmp_path: Path):
    bad = SymbolRequestError("BAD.NS: HTTP 404: symbol not found")
    good = {"data": {"symbol": "INFY.NS", "candles": []}}

    with patch("analytics_etl.extract.CACHE_DIR", tmp_path), patch(
        "analytics_etl.extract._get_api_key", return_value="fake-test-key"
    ), patch("analytics_etl.extract._request", side_effect=[bad, good]):
        result = __import__("analytics_etl.extract", fromlist=["extract"]).extract(
            symbols=["BAD.NS", "INFY.NS"]
        )

    assert result == {"INFY.NS": good}