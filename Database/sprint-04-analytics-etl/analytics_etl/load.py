from pathlib import Path

import duckdb
import pandas as pd


DATABASE_PATH = Path("analytics.duckdb")
COLUMNS = [
    "symbol",
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "synthetic",
    "daily_change",
    "daily_change_pct",
]


def load(data: pd.DataFrame, database_path: Path = DATABASE_PATH) -> int:
    """Store a cleaned candle DataFrame in DuckDB and return row count."""
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")

    missing_columns = set(COLUMNS) - set(data.columns)
    if missing_columns:
        raise ValueError(f"Missing columns: {sorted(missing_columns)}")

    connection = duckdb.connect(str(database_path))
    try:
        connection.execute(
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

        if data.empty:
            return 0

        connection.register("cleaned_candles", data[COLUMNS])
        connection.execute(
            """
            INSERT OR REPLACE INTO market_candles
            SELECT * FROM cleaned_candles
            """
        )
        return len(data)
    finally:
        connection.close()
