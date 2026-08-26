# analytics_etl/load.py

from pathlib import Path

import duckdb


DATABASE_PATH = Path("analytics.duckdb")


def load(data):
    """
    Write transformed candle data to DuckDB.

    This is the only ETL step that writes to the analytical store.
    """

    con = duckdb.connect(str(DATABASE_PATH))

    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS market_candles (
                symbol VARCHAR,
                date DATE,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume BIGINT,
                synthetic BOOLEAN,
                daily_change DOUBLE,
                daily_change_pct DOUBLE,
                PRIMARY KEY (symbol, date)
            )
            """
        )

        if not data:
            return

        con.executemany(
            """
            INSERT OR REPLACE INTO market_candles (
                symbol,
                date,
                open,
                high,
                low,
                close,
                volume,
                synthetic,
                daily_change,
                daily_change_pct
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["symbol"],
                    row["date"],
                    row["open"],
                    row["high"],
                    row["low"],
                    row["close"],
                    row["volume"],
                    row["synthetic"],
                    row["daily_change"],
                    row["daily_change_pct"],
                )
                for row in data
            ],
        )

    finally:
        con.close()