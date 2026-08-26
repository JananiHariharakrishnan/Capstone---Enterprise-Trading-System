# tests/test_transform.py

import json
from pathlib import Path

import pytest

from analytics_etl.transform import transform


FIXTURES = Path(__file__).parent.parent / "fixtures"


def read_fixture(name):
    with (FIXTURES / name).open(
        "r",
        encoding="utf-8",
    ) as fh:
        return json.load(fh)


def test_valid_input_transforms_to_expected_output():

    raw = read_fixture("infy.json")

    result = transform(
        {
            "INFY.NS": raw,
        }
    )

    assert result

    row = result[0]

    assert row["symbol"] == "INFY.NS"
    assert isinstance(row["open"], float)
    assert isinstance(row["high"], float)
    assert isinstance(row["low"], float)
    assert isinstance(row["close"], float)


def test_missing_required_field_is_rejected():

    raw = {
        "data": {
            "symbol": "INFY.NS",
            "candles": [
                {
                    "date": "2026-08-26",
                    "open": 100,
                    "high": 110,
                    "low": 90,
                    # close missing
                }
            ],
        }
    }

    result = transform(
        {
            "INFY.NS": raw,
        }
    )

    assert result == []


def test_out_of_range_value_is_rejected():

    raw = {
        "data": {
            "symbol": "INFY.NS",
            "candles": [
                {
                    "date": "2026-08-26",
                    "open": -100,
                    "high": 110,
                    "low": 90,
                    "close": 100,
                }
            ],
        }
    }

    result = transform(
        {
            "INFY.NS": raw,
        }
    )

    assert result == []


def test_rejects_a_high_below_a_low():

    raw = {
        "data": {
            "symbol": "INFY.NS",
            "candles": [
                {
                    "date": "2026-08-26",
                    "open": 100,
                    "high": 90,
                    "low": 110,
                    "close": 100,
                }
            ],
        }
    }

    result = transform(
        {
            "INFY.NS": raw,
        }
    )

    assert result == []


def test_empty_dataset_handled_without_error():

    result = transform(
        {
            "INFY.NS": {
                "data": {
                    "symbol": "INFY.NS",
                    "candles": [],
                }
            }
        }
    )

    assert result == []