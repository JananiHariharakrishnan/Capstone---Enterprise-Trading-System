from pathlib import Path

import duckdb

from analytics_etl.analysis import (
    compare_securities,
    summarize_data,
)
from analytics_etl.charts import create_market_dashboard


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(__file__).resolve().with_name("analytics.duckdb")

SYMBOLS = [
    "INFY.NS",
        "RELIANCE.NS",
        "TATASTEEL.BO",
        "ICICIBANK.NS"
]


def load_market_data():
    """
    Load non-synthetic market candle data from DuckDB
    and restrict all securities to their common date range.
    """

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"DuckDB database not found: {DATABASE_PATH}\n"
            "Run the ETL pipeline first."
        )

    connection = duckdb.connect(
        str(DATABASE_PATH),
        read_only=True,
    )

    try:
        placeholders = ", ".join("?" for _ in SYMBOLS)

        query = f"""
            SELECT
                symbol,
                date,
                "close"
            FROM main.market_candles
            WHERE symbol IN ({placeholders})
              AND synthetic = FALSE
            ORDER BY symbol, date
        """

        df = connection.execute(
            query,
            SYMBOLS,
        ).df()

    finally:
        connection.close()

    if df.empty:
        raise ValueError(
            "No non-synthetic market data found for the requested symbols."
        )

    # Make sure every requested symbol exists.
    for symbol in SYMBOLS:
        if df[df["symbol"] == symbol].empty:
            raise ValueError(
                f"No non-synthetic data found for {symbol}."
            )

    # ---------------------------------------------------------
    # Determine common date range
    # ---------------------------------------------------------

    date_ranges = (
        df.groupby("symbol")["date"]
        .agg(["min", "max"])
    )

    common_start = date_ranges["min"].max()
    common_end = date_ranges["max"].min()

    if common_start > common_end:
        raise ValueError(
            "The requested securities have no overlapping date range."
        )

    print("\nCommon analysis period:")
    print(f"  {common_start} → {common_end}")

    # ---------------------------------------------------------
    # Restrict all securities to common period
    # ---------------------------------------------------------

    df = df[
        (df["date"] >= common_start)
        & (df["date"] <= common_end)
    ].copy()

    data = {}

    for symbol in SYMBOLS:
        symbol_df = (
            df[df["symbol"] == symbol]
            .sort_values("date")
            .copy()
        )

        if symbol_df.empty:
            raise ValueError(
                f"No data remains for {symbol} "
                "after applying the common date range."
            )

        data[symbol] = symbol_df

    return data

def main():
    print("=== ANALYSIS START ===")

    print("\nDatabase:")
    print(DATABASE_PATH)

    print("\nSymbols:")
    for symbol in SYMBOLS:
        print(f"  - {symbol}")

    # ---------------------------------------------------------
    # Load real ETL output from DuckDB
    # ---------------------------------------------------------

    data = load_market_data()

    # ---------------------------------------------------------
    # Calculate financial metrics
    # ---------------------------------------------------------

    metrics = compare_securities(data)

    print("\n=== ANALYSIS RESULTS ===")
    print(metrics.to_string(index=False))

    # ---------------------------------------------------------
    # Calculate supporting dataset statistics
    # ---------------------------------------------------------

    summary = summarize_data(data)

    print("\n=== DATASET SUMMARY ===")
    print(summary.to_string(index=False))

    # ---------------------------------------------------------
    # Generate HTML dashboard
    # ---------------------------------------------------------

    output_path = (
        PROJECT_ROOT
        / "artefacts"
        / "market_dashboard.html"
    )

    create_market_dashboard(
        metrics,
        str(output_path),
    )

    print("\nDashboard created:")
    print(output_path)

    print("\n=== ANALYSIS COMPLETE ===")


if __name__ == "__main__":
    main()