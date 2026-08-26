# tests/test_extract.py

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