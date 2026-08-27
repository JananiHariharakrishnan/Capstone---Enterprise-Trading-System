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

INSTRUMENT_NAMES = {

}


def _exchange_for_symbol(symbol: str) -> str:
    if symbol.endswith(".NS"):
        return "NSE"
    if symbol.endswith(".BO"):
        return "BSE"
    if symbol.startswith("FX:"):
        return "FX"
    if symbol.startswith("X:"):
        return "CRYPTO"
    return "US"


def _create_schema(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS dim_account (
            account_key BIGINT NOT NULL,
            account_id VARCHAR(32) NOT NULL,
            holder_name VARCHAR(255) NOT NULL,
            status VARCHAR(20) NOT NULL,
            effective_date DATE NOT NULL,
            end_date DATE,
            is_current BOOLEAN NOT NULL,
            source_id BIGINT NOT NULL,
            loaded_at TIMESTAMP NOT NULL,
            CONSTRAINT pk_dim_account PRIMARY KEY (account_key)
        );

        CREATE TABLE IF NOT EXISTS dim_instrument (
            instrument_key BIGINT NOT NULL,
            symbol VARCHAR(20) NOT NULL,
            name VARCHAR(255) NOT NULL,
            asset_class VARCHAR(20) NOT NULL,
            currency CHAR(3) NOT NULL,
            exchange VARCHAR(20),
            tradable BOOLEAN NOT NULL,
            loaded_at TIMESTAMP NOT NULL,
            CONSTRAINT pk_dim_instrument PRIMARY KEY (instrument_key),
            CONSTRAINT uq_dim_instrument_symbol UNIQUE (symbol)
        );

        CREATE TABLE IF NOT EXISTS dim_date (
            date_key INTEGER NOT NULL,
            full_date DATE NOT NULL,
            day INTEGER NOT NULL,
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            quarter INTEGER NOT NULL,
            day_of_week INTEGER NOT NULL,
            day_name VARCHAR(9) NOT NULL,
            month_name VARCHAR(9) NOT NULL,
            is_weekday BOOLEAN NOT NULL,
            CONSTRAINT pk_dim_date PRIMARY KEY (date_key),
            CONSTRAINT uq_dim_date_full_date UNIQUE (full_date)
        );

        CREATE TABLE IF NOT EXISTS fact_trades (
            trade_key BIGINT NOT NULL,
            account_key BIGINT NOT NULL,
            instrument_key BIGINT NOT NULL,
            date_key INTEGER NOT NULL,
            side VARCHAR(4) NOT NULL,
            quantity INTEGER NOT NULL,
            price DECIMAL(18, 2) NOT NULL,
            status VARCHAR(20) NOT NULL,
            executed_price DECIMAL(18, 2),
            trade_value DECIMAL(18, 2) NOT NULL,
            source_order_id VARCHAR(36) NOT NULL,
            created_at TIMESTAMP NOT NULL,
            loaded_at TIMESTAMP NOT NULL,
            CONSTRAINT pk_fact_trades PRIMARY KEY (trade_key),
            CONSTRAINT uq_fact_trades_source UNIQUE (source_order_id),
            CONSTRAINT fk_fact_trades_account FOREIGN KEY (account_key)
                REFERENCES dim_account (account_key),
            CONSTRAINT fk_fact_trades_instrument FOREIGN KEY (instrument_key)
                REFERENCES dim_instrument (instrument_key),
            CONSTRAINT fk_fact_trades_date FOREIGN KEY (date_key)
                REFERENCES dim_date (date_key)
        );

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
        );
        """
    )


def _load_dimensions(connection: duckdb.DuckDBPyConnection, data: pd.DataFrame) -> None:
    if data.empty:
        return

    loaded_at = pd.Timestamp.now()
    instruments = pd.DataFrame(
        {
            "instrument_key": data["symbol"].drop_duplicates().map(
                lambda symbol: abs(hash(symbol))
            ),
            "symbol": data["symbol"].drop_duplicates().tolist(),
        }
    )
    instruments["name"] = instruments["symbol"]
    instruments["asset_class"] = "EQUITY"
    instruments["currency"] = "INR"
    instruments["exchange"] = instruments["symbol"].map(_exchange_for_symbol)
    instruments["tradable"] = True
    instruments["loaded_at"] = loaded_at
    connection.register("etl_instruments", instruments)
    connection.execute(
        """
         INSERT INTO dim_instrument
         SELECT instrument_key, symbol, name, asset_class, currency,
             exchange, tradable, loaded_at
         FROM etl_instruments
         ON CONFLICT (symbol) DO UPDATE SET
             name = EXCLUDED.name,
             asset_class = EXCLUDED.asset_class,
             currency = EXCLUDED.currency,
             exchange = EXCLUDED.exchange,
             tradable = EXCLUDED.tradable,
             loaded_at = EXCLUDED.loaded_at
        """
    )
    connection.unregister("etl_instruments")

    dates = pd.DataFrame({"full_date": data["date"].drop_duplicates()})
    dates["full_date"] = pd.to_datetime(dates["full_date"])
    dates["date_key"] = dates["full_date"].dt.strftime("%Y%m%d").astype(int)
    dates["day"] = dates["full_date"].dt.day
    dates["month"] = dates["full_date"].dt.month
    dates["year"] = dates["full_date"].dt.year
    dates["quarter"] = dates["full_date"].dt.quarter
    dates["day_of_week"] = dates["full_date"].dt.dayofweek + 1
    dates["day_name"] = dates["full_date"].dt.day_name()
    dates["month_name"] = dates["full_date"].dt.month_name()
    dates["is_weekday"] = dates["full_date"].dt.dayofweek < 5
    connection.register("etl_dates", dates)
    connection.execute(
        """
         INSERT INTO dim_date
         SELECT date_key, full_date, day, month, year, quarter,
             day_of_week, day_name, month_name, is_weekday
         FROM etl_dates
         ON CONFLICT (full_date) DO UPDATE SET
             day = EXCLUDED.day,
             month = EXCLUDED.month,
             year = EXCLUDED.year,
             quarter = EXCLUDED.quarter,
             day_of_week = EXCLUDED.day_of_week,
             day_name = EXCLUDED.day_name,
             month_name = EXCLUDED.month_name,
             is_weekday = EXCLUDED.is_weekday
        """
    )
    connection.unregister("etl_dates")


def load(data: pd.DataFrame, database_path: Path = DATABASE_PATH) -> int:
    """Load candles and their dimensions into the analytical DuckDB store."""
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")

    missing_columns = set(COLUMNS) - set(data.columns)
    if missing_columns:
        raise ValueError(f"Missing columns: {sorted(missing_columns)}")

    connection = duckdb.connect(str(database_path))
    try:
        _create_schema(connection)

        if data.empty:
            return 0

        _load_dimensions(connection, data)

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
