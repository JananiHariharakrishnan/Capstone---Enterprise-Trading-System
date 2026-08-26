# analytics_etl/charts.py

from pathlib import Path

import duckdb
import plotly.express as px


ARTEFACT_DIR = Path("artefacts")
DATABASE_PATH = "analytics.duckdb"


def create_charts():
    ARTEFACT_DIR.mkdir(exist_ok=True)

    con = duckdb.connect(DATABASE_PATH, read_only=True)

    try:

        # ---------------------------------------------------------
        # Chart 1: volume
        # ---------------------------------------------------------

        volume = con.execute(
            """
            SELECT
                date,
                symbol,
                volume
            FROM market_candles
            WHERE volume IS NOT NULL
            ORDER BY date
            """
        ).df()

        fig = px.line(
            volume,
            x="date",
            y="volume",
            color="symbol",
        )

        fig.update_layout(
            title="Daily trading volume across Indian instruments",
            xaxis_title="Trading date",
            yaxis_title="Trading volume (shares)",
        )

        fig.write_html(
            ARTEFACT_DIR / "volume_by_date.html",
            include_plotlyjs=True,
        )

        # ---------------------------------------------------------
        # Chart 2: daily price change
        # ---------------------------------------------------------

        changes = con.execute(
            """
            SELECT
                date,
                symbol,
                daily_change_pct
            FROM market_candles
            ORDER BY date
            """
        ).df()

        fig = px.line(
            changes,
            x="date",
            y="daily_change_pct",
            color="symbol",
        )

        fig.update_layout(
            title="Daily percentage price movement across Indian instruments",
            xaxis_title="Trading date",
            yaxis_title="Daily price change (percent)",
        )

        fig.write_html(
            ARTEFACT_DIR / "price_change.html",
            include_plotlyjs=True,
        )

        # ---------------------------------------------------------
        # Chart 3: average volume
        # ---------------------------------------------------------

        average_volume = con.execute(
            """
            SELECT
                symbol,
                AVG(volume) AS average_volume
            FROM market_candles
            WHERE volume IS NOT NULL
            GROUP BY symbol
            ORDER BY average_volume DESC
            """
        ).df()

        fig = px.bar(
            average_volume,
            x="symbol",
            y="average_volume",
        )

        fig.update_layout(
            title="Average daily trading volume differs across Indian instruments",
            xaxis_title="Instrument",
            yaxis_title="Average daily trading volume (shares)",
        )

        fig.write_html(
            ARTEFACT_DIR / "volume_comparison.html",
            include_plotlyjs=True,
        )

    finally:
        con.close()