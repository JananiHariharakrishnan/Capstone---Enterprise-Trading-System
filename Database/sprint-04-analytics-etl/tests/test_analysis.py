import pandas as pd
import pytest

from analytics_etl.analysis import (
    calculate_total_return,
    calculate_volatility,
    calculate_max_drawdown,
    compare_securities,
)


@pytest.fixture
def sample_data():
    return pd.DataFrame(
        {
            "symbol": [
                "INFY.NS",
                "INFY.NS",
                "INFY.NS",
                "INFY.NS",
            ],
            "date": pd.to_datetime(
                [
                    "2026-07-01",
                    "2026-07-02",
                    "2026-07-03",
                    "2026-07-06",
                ]
            ),
            "close": [
                100.0,
                105.0,
                102.0,
                110.0,
            ],
        }
    )


def test_total_return(sample_data):
    result = calculate_total_return(sample_data)

    assert result == pytest.approx(10.0)


def test_volatility(sample_data):
    result = calculate_volatility(sample_data)

    assert result > 0


def test_max_drawdown(sample_data):
    result = calculate_max_drawdown(sample_data)

    assert result == pytest.approx(-2.857142857, rel=1e-5)


def test_compare_securities(sample_data):
    reliance = sample_data.copy()
    reliance["symbol"] = "RELIANCE.NS"

    tata = sample_data.copy()
    tata["symbol"] = "TATASTEEL.BO"

    result = compare_securities(
        {
            "INFY.NS": sample_data,
            "RELIANCE.NS": reliance,
            "TATASTEEL.BO": tata,
        }
    )

    assert len(result) == 3
    assert set(result["symbol"]) == {
        "INFY.NS",
        "RELIANCE.NS",
        "TATASTEEL.BO",
    }
    
def test_create_market_dashboard(tmp_path, sample_data):
    from analytics_etl.analysis.charts import create_market_dashboard

    metrics = compare_securities(
        {
            "INFY.NS": sample_data,
            "RELIANCE.NS": sample_data.assign(
                symbol="RELIANCE.NS"
            ),
            "TATASTEEL.BO": sample_data.assign(
                symbol="TATASTEEL.BO"
            ),
        }
    )

    output = tmp_path / "dashboard.html"

    create_market_dashboard(metrics, str(output))

    assert output.exists()
    assert output.stat().st_size > 0

