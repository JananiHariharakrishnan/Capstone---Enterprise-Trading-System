from pathlib import Path
import logging

import duckdb
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .analysis import compare_securities


logger = logging.getLogger(__name__)


COMPANY_CONFIG = {
    "INFY.NS": {
        "name": "Infosys",
        "color": "#2563EB",
    },
    "RELIANCE.NS": {
        "name": "Reliance Industries",
        "color": "#7C3AED",
    },
    "TATASTEEL.BO": {
        "name": "Tata Steel",
        "color": "#0F766E",
    },
}

COLORS = {
    "background": "#F5F7FA",
    "card": "#FFFFFF",
    "text": "#17202A",
    "muted": "#64748B",
    "grid": "#E5E7EB",
    "positive": "#16A34A",
    "negative": "#DC2626",
    "accent": "#2563EB",
}

DATABASE_PATH = Path("analytics.duckdb")


def company_name(symbol: str) -> str:
    """Return a human-readable company name."""
    return COMPANY_CONFIG.get(
        symbol,
        {"name": symbol},
    )["name"]


def company_color(symbol: str) -> str:
    """Return the company's dashboard colour."""
    return COMPANY_CONFIG.get(
        symbol,
        {"color": COLORS["accent"]},
    )["color"]


def create_dashboard_from_database(
    database_path: Path = DATABASE_PATH,
    output_file: str = "artefacts/market_dashboard.html",
) -> None:
    """Read candles from DuckDB, calculate metrics, and write the dashboard."""
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        candles = connection.execute(
            """
            SELECT symbol, date, close
            FROM market_candles
            ORDER BY symbol, date
            """
        ).df()
    finally:
        connection.close()

    if candles.empty:
        raise ValueError("Cannot create dashboard from an empty market_candles table.")

    securities = {
        symbol: frame.reset_index(drop=True)
        for symbol, frame in candles.groupby("symbol")
    }
    metrics = compare_securities(securities)
    create_market_dashboard(metrics, output_file)


def _base_layout(fig: go.Figure) -> None:
    """Apply the common dashboard visual style."""

    fig.update_layout(
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["card"],
        font=dict(
            family="Arial, sans-serif",
            color=COLORS["text"],
        ),
        margin=dict(
            l=60,
            r=40,
            t=80,
            b=60,
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Arial, sans-serif",
        ),
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showline=False,
        tickfont=dict(
            color=COLORS["muted"],
        ),
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor=COLORS["grid"],
        zeroline=False,
        showline=False,
        tickfont=dict(
            color=COLORS["muted"],
        ),
    )


def _kpi_card(
    title: str,
    value: str,
    subtitle: str,
    accent: str,
) -> str:
    """Create one HTML KPI card."""

    return f"""
    <div style="
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 22px 24px;
        min-width: 190px;
        flex: 1;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
    ">
        <div style="
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.2px;
            color: #64748B;
            margin-bottom: 10px;
        ">
            {title}
        </div>

        <div style="
            font-size: 28px;
            font-weight: 700;
            color: {accent};
            margin-bottom: 5px;
        ">
            {value}
        </div>

        <div style="
            font-size: 13px;
            color: #64748B;
        ">
            {subtitle}
        </div>
    </div>
    """


def _insight_card(
    number: str,
    title: str,
    text: str,
) -> str:
    """Create one analytical insight card."""

    return f"""
    <div style="
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 14px;
        padding: 20px;
        flex: 1;
        min-width: 240px;
    ">
        <div style="
            color: #2563EB;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1px;
            margin-bottom: 8px;
        ">
            {number}
        </div>

        <div style="
            font-size: 15px;
            font-weight: 700;
            color: #17202A;
            margin-bottom: 8px;
        ">
            {title}
        </div>

        <div style="
            font-size: 13px;
            line-height: 1.6;
            color: #64748B;
        ">
            {text}
        </div>
    </div>
    """


def create_market_dashboard(
    metrics: pd.DataFrame,
    output_file: str = "artefacts/market_dashboard.html",
) -> None:
    """
    Create a single professional HTML dashboard containing:

    - KPI summary
    - risk/return scatter plot
    - return ranking
    - volatility comparison
    - maximum drawdown comparison
    - automatically generated insights
    """

    if metrics.empty:
        raise ValueError("Cannot create dashboard from empty metrics.")

    required_columns = {
        "symbol",
        "total_return",
        "volatility",
        "max_drawdown",
    }

    missing = required_columns - set(metrics.columns)

    if missing:
        raise ValueError(
            f"Metrics DataFrame is missing columns: {sorted(missing)}"
        )

    metrics = metrics.copy()

    metrics["company"] = metrics["symbol"].map(company_name)
    metrics["color"] = metrics["symbol"].map(company_color)

    # ---------------------------------------------------------
    # Calculate summary values
    # ---------------------------------------------------------

    best_return = metrics.loc[
        metrics["total_return"].idxmax()
    ]

    highest_volatility = metrics.loc[
        metrics["volatility"].idxmax()
    ]

    largest_drawdown = metrics.loc[
        metrics["max_drawdown"].idxmin()
    ]

    average_return = metrics["total_return"].mean()
    average_volatility = metrics["volatility"].mean()

    # ---------------------------------------------------------
    # Risk / Return scatter
    # ---------------------------------------------------------

    scatter = go.Figure()

    for _, row in metrics.iterrows():
        scatter.add_trace(
            go.Scatter(
                x=[row["volatility"]],
                y=[row["total_return"]],
                mode="markers+text",
                name=row["company"],
                text=[row["company"]],
                textposition="top center",
                marker=dict(
                    size=22,
                    color=row["color"],
                    line=dict(
                        color="white",
                        width=3,
                    ),
                ),
                hovertemplate=(
                    f"<b>{row['company']}</b><br>"
                    "Return: %{y:.2f}%<br>"
                    "Volatility: %{x:.2f}%"
                    "<extra></extra>"
                ),
            )
        )

    scatter.update_layout(
        title=dict(
            text="Risk / Return Landscape",
            font=dict(size=22),
        ),
        xaxis_title="Daily Volatility (%)",
        yaxis_title="Total Return (%)",
        showlegend=False,
        height=480,
    )

    _base_layout(scatter)

    # ---------------------------------------------------------
    # Return ranking
    # ---------------------------------------------------------

    return_data = metrics.sort_values(
        "total_return",
        ascending=True,
    )

    return_chart = go.Figure()

    return_chart.add_trace(
        go.Bar(
            x=return_data["total_return"],
            y=return_data["company"],
            orientation="h",
            marker_color=[
                (
                    COLORS["positive"]
                    if value >= 0
                    else COLORS["negative"]
                )
                for value in return_data["total_return"]
            ],
            text=[
                f"{value:+.2f}%"
                for value in return_data["total_return"]
            ],
            textposition="outside",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Total Return: %{x:.2f}%"
                "<extra></extra>"
            ),
        )
    )

    return_chart.update_layout(
        title=dict(
            text="Return Ranking",
            font=dict(size=20),
        ),
        xaxis_title="Total Return (%)",
        height=380,
        showlegend=False,
    )

    _base_layout(return_chart)

    # ---------------------------------------------------------
    # Volatility
    # ---------------------------------------------------------

    volatility_data = metrics.sort_values(
        "volatility",
        ascending=True,
    )

    volatility_chart = go.Figure()

    volatility_chart.add_trace(
        go.Scatter(
            x=volatility_data["volatility"],
            y=volatility_data["company"],
            mode="markers",
            marker=dict(
                size=16,
                color=[
                    company_color(symbol)
                    for symbol in volatility_data["symbol"]
                ],
            ),
            text=[
                f"{value:.2f}%"
                for value in volatility_data["volatility"]
            ],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Daily Volatility: %{x:.2f}%"
                "<extra></extra>"
            ),
        )
    )

    volatility_chart.update_layout(
        title=dict(
            text="Volatility Profile",
            font=dict(size=20),
        ),
        xaxis_title="Daily Volatility (%)",
        height=380,
        showlegend=False,
    )

    _base_layout(volatility_chart)

    # ---------------------------------------------------------
    # Drawdown
    # ---------------------------------------------------------

    drawdown_data = metrics.sort_values(
        "max_drawdown",
        ascending=False,
    )

    drawdown_chart = go.Figure()

    drawdown_chart.add_trace(
        go.Bar(
            x=drawdown_data["max_drawdown"],
            y=drawdown_data["company"],
            orientation="h",
            marker_color=COLORS["negative"],
            opacity=0.85,
            text=[
                f"{value:.2f}%"
                for value in drawdown_data["max_drawdown"]
            ],
            textposition="outside",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Maximum Drawdown: %{x:.2f}%"
                "<extra></extra>"
            ),
        )
    )

    drawdown_chart.update_layout(
        title=dict(
            text="Maximum Drawdown",
            font=dict(size=20),
        ),
        xaxis_title="Peak-to-Trough Decline (%)",
        height=380,
        showlegend=False,
    )

    _base_layout(drawdown_chart)

    # ---------------------------------------------------------
    # Generate insights
    # ---------------------------------------------------------

    insights = [
        _insight_card(
            "01",
            "Strongest performance",
            (
                f"{company_name(best_return['symbol'])} delivered "
                f"the highest total return at "
                f"<b>{best_return['total_return']:+.2f}%</b>."
            ),
        ),
        _insight_card(
            "02",
            "Highest volatility",
            (
                f"{company_name(highest_volatility['symbol'])} "
                f"experienced the highest daily volatility at "
                f"<b>{highest_volatility['volatility']:.2f}%</b>."
            ),
        ),
        _insight_card(
            "03",
            "Largest drawdown",
            (
                f"{company_name(largest_drawdown['symbol'])} "
                f"recorded the largest peak-to-trough decline at "
                f"<b>{largest_drawdown['max_drawdown']:.2f}%</b>."
            ),
        ),
    ]

    # ---------------------------------------------------------
    # Convert Plotly figures to HTML
    # ---------------------------------------------------------

    scatter_html = scatter.to_html(
        full_html=False,
        include_plotlyjs=True,
    )

    return_html = return_chart.to_html(
        full_html=False,
        include_plotlyjs=False,
    )

    volatility_html = volatility_chart.to_html(
        full_html=False,
        include_plotlyjs=False,
    )

    drawdown_html = drawdown_chart.to_html(
        full_html=False,
        include_plotlyjs=False,
    )

    # ---------------------------------------------------------
    # Build dashboard
    # ---------------------------------------------------------

    dashboard = f"""
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>Indian Securities Analytics</title>

    <style>

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            background: #F5F7FA;
            color: #17202A;
            font-family:
                Arial,
                Helvetica,
                sans-serif;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 28px 60px;
        }}

        .header {{
            margin-bottom: 30px;
        }}

        .eyebrow {{
            color: #2563EB;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 2px;
            margin-bottom: 10px;
        }}

        h1 {{
            margin: 0;
            font-size: 38px;
            letter-spacing: -1.2px;
        }}

        .subtitle {{
            color: #64748B;
            font-size: 15px;
            margin-top: 10px;
        }}

        .kpis {{
            display: flex;
            gap: 16px;
            margin-bottom: 22px;
            flex-wrap: wrap;
        }}

        .section {{
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 18px;
            margin-bottom: 22px;
            overflow: hidden;
            box-shadow:
                0 5px 20px rgba(15, 23, 42, 0.035);
        }}

        .section-content {{
            padding: 8px;
        }}

        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 22px;
            margin-bottom: 22px;
        }}

        .insights {{
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
        }}

        .insights-section {{
            padding: 24px;
        }}

        .section-title {{
            font-size: 12px;
            font-weight: 700;
            color: #64748B;
            letter-spacing: 1.4px;
            margin-bottom: 18px;
        }}

        .footer {{
            text-align: center;
            color: #94A3B8;
            font-size: 12px;
            margin-top: 30px;
        }}

        @media (max-width: 900px) {{
            .grid {{
                grid-template-columns: 1fr;
            }}

            h1 {{
                font-size: 30px;
            }}

            .container {{
                padding: 25px 15px 40px;
            }}
        }}

    </style>
</head>

<body>

<div class="container">

    <div class="header">

        <div class="eyebrow">
            MARKET ANALYTICS
        </div>

        <h1>
            Indian Securities
        </h1>

        <div class="subtitle">
            Performance · Risk · Drawdown
        </div>

    </div>

    <div class="kpis">

        {_kpi_card(
            "BEST RETURN",
            f"{best_return['total_return']:+.2f}%",
            company_name(best_return["symbol"]),
            COLORS["positive"],
        )}

        {_kpi_card(
            "AVERAGE RETURN",
            f"{average_return:+.2f}%",
            "Across analysed securities",
            COLORS["accent"],
        )}

        {_kpi_card(
            "AVG VOLATILITY",
            f"{average_volatility:.2f}%",
            "Daily return volatility",
            COLORS["accent"],
        )}

        {_kpi_card(
            "LARGEST DRAWDOWN",
            f"{largest_drawdown['max_drawdown']:.2f}%",
            company_name(largest_drawdown["symbol"]),
            COLORS["negative"],
        )}

    </div>

    <div class="section">
        <div class="section-content">
            {scatter_html}
        </div>
    </div>

    <div class="grid">

        <div class="section">
            <div class="section-content">
                {return_html}
            </div>
        </div>

        <div class="section">
            <div class="section-content">
                {volatility_html}
            </div>
        </div>

    </div>

    <div class="section">
        <div class="section-content">
            {drawdown_html}
        </div>
    </div>

    <div class="section insights-section">

        <div class="section-title">
            KEY INSIGHTS
        </div>

        <div class="insights">
            {"".join(insights)}
        </div>

    </div>

    <div class="footer">
        Generated from daily security price data ·
        Performance and risk analytics
    </div>

</div>

</body>
</html>
"""

    # ---------------------------------------------------------
    # Write output
    # ---------------------------------------------------------

    Path(output_file).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    Path(output_file).write_text(
        dashboard,
        encoding="utf-8",
    )


def main() -> int:
    """Generate the dashboard from the default DuckDB database."""
    try:
        create_dashboard_from_database()
    except (OSError, duckdb.Error, ValueError) as exc:
        logger.error("DASHBOARD_FAILED reason=%s", exc)
        print(f"Dashboard generation failed: {exc}")
        return 1

    print("Dashboard written to artefacts/market_dashboard.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
