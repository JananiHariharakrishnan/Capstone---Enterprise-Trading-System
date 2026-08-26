# tests/test_transform.py

import json
from pathlib import Path

import pandas as pd
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

    raw = read_fixture("candles-infy-ns-2026-07.json")
    result = transform(
        {
            "INFY.NS": raw,
        }
    )

    assert isinstance(result, pd.DataFrame)
    assert not result.empty

    row = result.iloc[0]
    assert row["symbol"] == "INFY.NS"
    assert pd.api.types.is_float_dtype(result["open"])
    assert pd.api.types.is_float_dtype(result["high"])
    assert pd.api.types.is_float_dtype(result["low"])
    assert pd.api.types.is_float_dtype(result["close"])
    assert "daily_change_pct" in result.columns


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

    assert result.empty


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

    assert result.empty


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

    assert result.empty


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

    assert result.empty


def test_malformed_fixture_drops_invalid_rows_and_logs(caplog):
    raw = read_fixture("candles-malformed.json")

    with caplog.at_level("WARNING"):
        result = transform({"TATASTEEL.BO": raw})

    assert len(result) == 1
    assert not result.duplicated(["symbol", "date"]).any()
    assert "INVALID_CANDLES" in caplog.text