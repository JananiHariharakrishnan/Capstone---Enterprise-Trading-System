import pandas as pd

from analytics_etl.charts import create_dashboard_from_database
from analytics_etl.load import load


def test_dashboard_reads_metrics_from_duckdb(tmp_path):
    data = pd.DataFrame(
        {
            "symbol": [
                "INFY.NS", "INFY.NS", "INFY.NS",
                "RELIANCE.NS", "RELIANCE.NS", "RELIANCE.NS",
            ],
            "date": pd.to_datetime(
                [
                    "2026-07-01", "2026-07-02", "2026-07-03",
                    "2026-07-01", "2026-07-02", "2026-07-03",
                ]
            ).date,
            "open": [100.0, 105.0, 110.0, 200.0, 198.0, 202.0],
            "high": [101.0, 106.0, 111.0, 201.0, 199.0, 203.0],
            "low": [99.0, 104.0, 109.0, 199.0, 197.0, 201.0],
            "close": [105.0, 110.0, 112.0, 198.0, 202.0, 204.0],
            "volume": [1000, 1100, 1200, 2000, 2100, 2200],
            "synthetic": [False, False, False, False, False, False],
            "daily_change": [5.0, 5.0, 2.0, -2.0, 4.0, 2.0],
            "daily_change_pct": [5.0, 4.76, 1.82, -1.0, 2.02, 0.99],
        }
    )
    database = tmp_path / "analytics.duckdb"
    dashboard = tmp_path / "dashboard.html"

    load(data, database)
    create_dashboard_from_database(database, str(dashboard))

    assert dashboard.exists()
    html = dashboard.read_text(encoding="utf-8")
    assert "KEY INSIGHTS" in html
    assert "Strongest performance" in html
