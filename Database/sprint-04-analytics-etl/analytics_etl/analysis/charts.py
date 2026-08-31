from pathlib import Path
import logging

import duckdb
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..analysis import compare_securities


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
    "ICICIBANK.NS": {
        "name": "ICICI Bank",
        "color": "#F59E0B",
    },
}

COLORS = {
    "background": "#F0F4F9",
    "background_dark": "#E8ECF1",
    "card": "#FFFFFF",
    "card_hover": "#F9FAFB",
    "text": "#0F172A",
    "text_light": "#475569",
    "muted": "#64748B",
    "border": "#E2E8F0",
    "grid": "#F1F5F9",
    "grid_subtle": "#EBF2F9",
    "positive": "#10B981",
    "positive_light": "#D1FAE5",
    "negative": "#EF4444",
    "negative_light": "#FEE2E2",
    "warning": "#F59E0B",
    "warning_light": "#FEF3C7",
    "accent": "#3B82F6",
    "accent_dark": "#1E40AF",
    "accent_light": "#DBEAFE",
    "secondary": "#8B5CF6",
    "secondary_light": "#EDE9FE",
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
            WHERE synthetic = FALSE
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
        paper_bgcolor=COLORS["card"],
        plot_bgcolor=COLORS["grid"],
        font=dict(
            family="'Segoe UI', 'Roboto', 'Helvetica Neue', -apple-system, sans-serif",
            color=COLORS["text"],
            size=12,
        ),
        margin=dict(
            l=70,
            r=50,
            t=90,
            b=70,
        ),
        hoverlabel=dict(
            bgcolor=COLORS["text"],
            font_size=13,
            font_family="'Segoe UI', 'Roboto', sans-serif",
            font_color="white",
        ),
        showlegend=False,
        hovermode="closest",
    )

    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=COLORS["grid_subtle"],
        zeroline=False,
        showline=True,
        linewidth=2,
        linecolor=COLORS["border"],
        tickfont=dict(
            color=COLORS["muted"],
            size=11,
        ),
        title_font=dict(
            size=13,
            color=COLORS["text_light"],
        ),
    )

    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=COLORS["grid_subtle"],
        zeroline=False,
        showline=True,
        linewidth=2,
        linecolor=COLORS["border"],
        tickfont=dict(
            color=COLORS["muted"],
            size=11,
        ),
        title_font=dict(
            size=13,
            color=COLORS["text_light"],
        ),
    )


def _kpi_card(
    title: str,
    value: str,
    subtitle: str,
    accent: str,
) -> str:
    """Create one HTML KPI card with modern styling."""
    
    # Determine if value is negative for styling
    is_negative = str(value).startswith('-')
    card_bg = COLORS["card"]
    
    return f"""
    <div style="
        background: linear-gradient(135deg, {card_bg} 0%, #FAFBFC 100%);
        border: 2px solid {COLORS['border']};
        border-radius: 14px;
        padding: 24px 28px;
        min-width: 200px;
        flex: 1;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06), 0 1px 3px rgba(0, 0, 0, 0.08);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    " class="kpi-card">
        <div style="
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, {accent}, transparent);
            opacity: 0.8;
        "></div>
        
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 14px;
        ">
            <div style="
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 1.3px;
                color: {COLORS['muted']};
                text-transform: uppercase;
            ">
                {title}
            </div>
            <div style="
                width: 36px;
                height: 36px;
                border-radius: 8px;
                background: linear-gradient(135deg, {accent}20, {accent}10);
                border: 1px solid {accent}30;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
            ">
                {'📊' if 'RETURN' in title else '📈' if 'VOLATILITY' in title else '📉' if 'DRAWDOWN' in title else '💹'}
            </div>
        </div>

        <div style="
            font-size: 32px;
            font-weight: 800;
            color: {accent};
            margin-bottom: 8px;
            letter-spacing: -0.8px;
        ">
            {value}
        </div>

        <div style="
            font-size: 12px;
            color: {COLORS['muted']};
            line-height: 1.5;
        ">
            {subtitle}
        </div>
    </div>
    <style>
        .kpi-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12), 0 4px 8px rgba(0, 0, 0, 0.1);
            border-color: {accent}40;
        }}
    </style>
    """


def _insight_card(
    number: str,
    title: str,
    text: str,
) -> str:
    """Create one analytical insight card with modern styling."""

    return f"""
    <div style="
        background: linear-gradient(135deg, {COLORS['card']} 0%, #FAFBFC 100%);
        border: 2px solid {COLORS['border']};
        border-radius: 12px;
        padding: 22px 24px;
        flex: 1;
        min-width: 280px;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
        transition: all 0.3s ease;
        position: relative;
    " class="insight-card">
        <div style="
            background: linear-gradient(135deg, {COLORS['accent']}, {COLORS['secondary']});
            color: white;
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: 900;
            margin-bottom: 12px;
        ">
            {number}
        </div>

        <div style="
            font-size: 14px;
            font-weight: 700;
            color: {COLORS['text']};
            margin-bottom: 10px;
            letter-spacing: -0.3px;
        ">
            {title}
        </div>

        <div style="
            font-size: 13px;
            line-height: 1.65;
            color: {COLORS['text_light']};
        ">
            {text}
        </div>
    </div>
    <style>
        .insight-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.1);
            border-color: {COLORS['accent']}40;
        }}
    </style>
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
                    size=28,
                    color=row["color"],
                    line=dict(
                        color="white",
                        width=3,
                    ),
                    opacity=0.85,
                ),
                textfont=dict(
                    size=12,
                    color=row["color"],
                    family="'Segoe UI', sans-serif",
                ),
                hovertemplate=(
                    f"<b>{row['company']}</b><br>"
                    "Return: %{y:.2f}%<br>"
                    "Volatility: %{x:.2f}%<br>"
                    "<extra></extra>"
                ),
            )
        )

    scatter.update_layout(
        title=dict(
            text="<b>Risk / Return Landscape</b>",
            font=dict(size=18, color=COLORS["text"], family="'Segoe UI', sans-serif"),
            x=0.05,
            xanchor="left",
            y=0.95,
            yanchor="top",
        ),
        xaxis_title="<b>Daily Volatility (%)</b>",
        yaxis_title="<b>Total Return (%)</b>",
        showlegend=False,
        height=500,
        hovermode="closest",
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
            marker_line_width=0,
            text=[
                f"{value:+.2f}%"
                for value in return_data["total_return"]
            ],
            textposition="outside",
            textfont=dict(
                size=12,
                color=COLORS["text"],
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Total Return: %{x:.2f}%"
                "<extra></extra>"
            ),
        )
    )

    return_chart.update_layout(
        title=dict(
            text="<b>Return Ranking</b>",
            font=dict(size=16, color=COLORS["text"]),
            x=0.05,
            xanchor="left",
        ),
        xaxis_title="<b>Total Return (%)</b>",
        height=400,
        showlegend=False,
        margin=dict(l=120, r=80, t=70, b=70),
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
                size=18,
                color=[
                    company_color(symbol)
                    for symbol in volatility_data["symbol"]
                ],
                line=dict(
                    width=2,
                    color="white",
                ),
            ),
            text=[
                f"{value:.2f}%"
                for value in volatility_data["volatility"]
            ],
            textposition="middle right",
            textfont=dict(
                size=12,
                color=COLORS["text"],
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Daily Volatility: %{x:.2f}%"
                "<extra></extra>"
            ),
        )
    )

    volatility_chart.update_layout(
        title=dict(
            text="<b>Volatility Profile</b>",
            font=dict(size=16, color=COLORS["text"]),
            x=0.05,
            xanchor="left",
        ),
        xaxis_title="<b>Daily Volatility (%)</b>",
        height=400,
        showlegend=False,
        margin=dict(l=120, r=80, t=70, b=70),
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
            marker_line_width=0,
            opacity=0.9,
            text=[
                f"{value:.2f}%"
                for value in drawdown_data["max_drawdown"]
            ],
            textposition="outside",
            textfont=dict(
                size=12,
                color=COLORS["text"],
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Maximum Drawdown: %{x:.2f}%"
                "<extra></extra>"
            ),
        )
    )

    drawdown_chart.update_layout(
        title=dict(
            text="<b>Maximum Drawdown</b>",
            font=dict(size=16, color=COLORS["text"]),
            x=0.05,
            xanchor="left",
        ),
        xaxis_title="<b>Peak-to-Trough Decline (%)</b>",
        height=400,
        showlegend=False,
        margin=dict(l=120, r=80, t=70, b=70),
    )

    _base_layout(drawdown_chart)

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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Enterprise-grade analytics dashboard for Indian securities market analysis">
    
    <title>Indian Securities Analytics Dashboard</title>

    <style>

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        html, body {{
            height: 100%;
        }}

        body {{
            background: linear-gradient(135deg, {COLORS['background']} 0%, {COLORS['background_dark']} 100%);
            color: {COLORS['text']};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
            font-size: 14px;
            line-height: 1.6;
            letter-spacing: -0.2px;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}

        .container {{
            max-width: 1520px;
            margin: 0 auto;
            padding: 48px 32px 80px;
        }}

        /* ============ HEADER ============ */

        .header {{
            margin-bottom: 48px;
        }}

        .header-content {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 40px;
            margin-bottom: 32px;
        }}

        .header-left {{
            flex: 1;
        }}

        .eyebrow {{
            color: {COLORS['accent']};
            font-size: 11px;
            font-weight: 900;
            letter-spacing: 2.5px;
            margin-bottom: 12px;
            text-transform: uppercase;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .eyebrow::before {{
            content: "";
            width: 20px;
            height: 2px;
            background: linear-gradient(90deg, {COLORS['accent']}, transparent);
        }}

        h1 {{
            margin: 0;
            font-size: 44px;
            font-weight: 900;
            letter-spacing: -1.5px;
            background: linear-gradient(135deg, {COLORS['text']} 0%, {COLORS['text_light']} 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 12px;
        }}

        .subtitle {{
            color: {COLORS['muted']};
            font-size: 16px;
            font-weight: 500;
            letter-spacing: -0.3px;
        }}

        .timestamp {{
            display: inline-block;
            background: {COLORS['accent_light']};
            color: {COLORS['accent_dark']};
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-top: 20px;
        }}

        /* ============ KPI SECTION ============ */

        .kpis {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            margin-bottom: 36px;
        }}

        /* ============ CHART SECTIONS ============ */

        .section {{
            background: {COLORS['card']};
            border: 1px solid {COLORS['border']};
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.08), 0 2px 6px rgba(0, 0, 0, 0.06);
            transition: all 0.3s ease;
            margin-bottom: 28px;
        }}

        .section:hover {{
            box-shadow: 0 8px 32px rgba(15, 23, 42, 0.12), 0 4px 12px rgba(0, 0, 0, 0.08);
            border-color: {COLORS['accent']}20;
        }}

        .section-header {{
            padding: 24px 32px;
            border-bottom: 1px solid {COLORS['border']};
            background: linear-gradient(135deg, #FAFBFC 0%, {COLORS['card']} 100%);
        }}

        .section-title {{
            font-size: 16px;
            font-weight: 800;
            color: {COLORS['text']};
            letter-spacing: -0.3px;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .section-title::before {{
            content: "";
            width: 4px;
            height: 20px;
            background: linear-gradient(180deg, {COLORS['accent']}, {COLORS['secondary']});
            border-radius: 2px;
        }}

        .section-content {{
            padding: 8px;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 28px;
            margin-bottom: 28px;
        }}

        @media (max-width: 1200px) {{
            .grid {{
                grid-template-columns: 1fr;
            }}
        }}

        /* ============ INSIGHTS SECTION ============ */

        .insights-section {{
            padding: 32px;
            background: linear-gradient(135deg, #FAFBFC 0%, {COLORS['card']} 100%);
        }}

        .insights {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 24px;
        }}

        /* ============ TABLE SECTION ============ */

        .metrics-table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .metrics-table thead {{
            background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
            border-bottom: 2px solid {COLORS['border']};
        }}

        .metrics-table th {{
            padding: 16px 20px;
            text-align: left;
            font-size: 12px;
            font-weight: 800;
            color: {COLORS['muted']};
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}

        .metrics-table tbody tr {{
            border-bottom: 1px solid {COLORS['grid']};
            transition: background-color 0.2s ease;
        }}

        .metrics-table tbody tr:hover {{
            background-color: {COLORS['grid']};
        }}

        .metrics-table td {{
            padding: 14px 20px;
            font-size: 13px;
            color: {COLORS['text_light']};
        }}

        .company-badge {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            background: {COLORS['card']};
            border-radius: 6px;
            font-weight: 600;
            color: {COLORS['text']};
        }}

        .metric-value {{
            font-weight: 700;
            font-family: 'Courier New', monospace;
            color: {COLORS['text']};
        }}

        .metric-positive {{
            color: {COLORS['positive']};
        }}

        .metric-negative {{
            color: {COLORS['negative']};
        }}

        /* ============ FOOTER ============ */

        .footer {{
            text-align: center;
            color: {COLORS['muted']};
            font-size: 12px;
            margin-top: 48px;
            padding-top: 32px;
            border-top: 1px solid {COLORS['border']};
            letter-spacing: 0.3px;
        }}

        .footer strong {{
            color: {COLORS['text_light']};
            font-weight: 700;
        }}

        /* ============ BADGE STYLES ============ */

        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.3px;
            text-transform: uppercase;
        }}

        .badge-positive {{
            background: {COLORS['positive_light']};
            color: {COLORS['positive']};
        }}

        .badge-negative {{
            background: {COLORS['negative_light']};
            color: {COLORS['negative']};
        }}

        .badge-warning {{
            background: {COLORS['warning_light']};
            color: {COLORS['warning']};
        }}

        /* ============ RESPONSIVE ============ */

        @media (max-width: 1024px) {{
            .container {{
                padding: 40px 24px 60px;
            }}

            h1 {{
                font-size: 36px;
            }}

            .kpis {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 24px 16px 40px;
            }}

            .header-content {{
                flex-direction: column;
                gap: 24px;
            }}

            h1 {{
                font-size: 28px;
            }}

            .subtitle {{
                font-size: 14px;
            }}

            .kpis {{
                grid-template-columns: 1fr;
            }}

            .grid {{
                grid-template-columns: 1fr;
                gap: 20px;
            }}

            .insights {{
                grid-template-columns: 1fr;
            }}
        }}

        /* ============ ANIMATIONS ============ */

        @keyframes fadeIn {{
            from {{
                opacity: 0;
                transform: translateY(10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .section {{
            animation: fadeIn 0.6s ease-out forwards;
        }}

        .section:nth-child(1) {{ animation-delay: 0.1s; }}
        .section:nth-child(2) {{ animation-delay: 0.2s; }}
        .section:nth-child(3) {{ animation-delay: 0.3s; }}
        .section:nth-child(4) {{ animation-delay: 0.4s; }}

    </style>
</head>

<body>

<div class="container">

    <!-- HEADER -->
    <div class="header">
        <div class="header-content">
            <div class="header-left">
                <div class="eyebrow">📊 Market Analytics</div>
                <h1>Indian Securities</h1>
                <p class="subtitle">Comprehensive performance and risk analysis across four major securities</p>
                <div class="timestamp">Generated from live market data</div>
            </div>
        </div>
    </div>

    <!-- KPI CARDS -->
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
            "Across all securities",
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

    <!-- RISK/RETURN SCATTER -->
    <div class="section">
        <div class="section-header">
            <h2 class="section-title">Risk / Return Landscape</h2>
        </div>
        <div class="section-content">
            {scatter_html}
        </div>
    </div>

    <!-- TWO COLUMN GRID -->
    <div class="grid">
        <div class="section">
            <div class="section-header">
                <h2 class="section-title">Return Ranking</h2>
            </div>
            <div class="section-content">
                {return_html}
            </div>
        </div>

        <div class="section">
            <div class="section-header">
                <h2 class="section-title">Volatility Profile</h2>
            </div>
            <div class="section-content">
                {volatility_html}
            </div>
        </div>
    </div>

    <!-- DRAWDOWN SECTION -->
    <div class="section">
        <div class="section-header">
            <h2 class="section-title">Maximum Drawdown</h2>
        </div>
        <div class="section-content">
            {drawdown_html}
        </div>
    </div>

    <!-- DETAILED METRICS TABLE -->
    <div class="section">
        <div class="section-header">
            <h2 class="section-title">Detailed Metrics</h2>
        </div>
        <div style="padding: 24px 32px;">
            <table class="metrics-table">
                <thead>
                    <tr>
                        <th>Security</th>
                        <th>Total Return</th>
                        <th>Daily Volatility</th>
                        <th>Max Drawdown</th>
                        <th>Return/Risk Ratio</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Add table rows
    for _, row in metrics.iterrows():
        rr_ratio = row["total_return"] / max(row["volatility"], 0.01)
        rr_class = "metric-positive" if rr_ratio > 0 else "metric-negative"
        return_class = "metric-positive" if row["total_return"] >= 0 else "metric-negative"
        
        dashboard += f"""
                    <tr>
                        <td>
                            <div class="company-badge" style="border-left: 4px solid {row['color']};">
                                {row['company']}
                            </div>
                        </td>
                        <td>
                            <span class="metric-value {return_class}">
                                {row['total_return']:+.2f}%
                            </span>
                        </td>
                        <td>
                            <span class="metric-value">{row['volatility']:.2f}%</span>
                        </td>
                        <td>
                            <span class="metric-value metric-negative">{row['max_drawdown']:.2f}%</span>
                        </td>
                        <td>
                            <span class="metric-value {rr_class}">{rr_ratio:.2f}x</span>
                        </td>
                    </tr>
"""
    
    dashboard += f"""
                </tbody>
            </table>
        </div>
    </div>

    <!-- INSIGHTS SECTION -->
    <div class="section">
        <div class="section-header">
            <h2 class="section-title">KEY INSIGHTS</h2>
        </div>
        <div class="insights-section">
            <div class="insights">
                {_insight_card(
                    "01",
                    "Strongest performance",
                    (
                        f"<b>{company_name(best_return['symbol'])}</b> leads with "
                        f"the highest total return of <b>{best_return['total_return']:+.2f}%</b>, "
                        f"demonstrating superior price appreciation over the analysis period."
                    ),
                )}
                
                {_insight_card(
                    "02",
                    "Volatility Analysis",
                    (
                        f"<b>{company_name(highest_volatility['symbol'])}</b> exhibits "
                        f"the highest daily volatility at <b>{highest_volatility['volatility']:.2f}%</b>, "
                        f"indicating greater price fluctuation and market sensitivity."
                    ),
                )}
                
                {_insight_card(
                    "03",
                    "Drawdown Comparison",
                    (
                        f"<b>{company_name(largest_drawdown['symbol'])}</b> recorded "
                        f"the largest peak-to-trough decline at <b>{largest_drawdown['max_drawdown']:.2f}%</b>, "
                        f"representing the most significant downside exposure."
                    ),
                )}
            </div>
        </div>
    </div>

    <!-- FOOTER -->
    <div class="footer">
        <strong>Indian Securities Analytics Dashboard</strong><br>
        Performance, volatility, and risk metrics · Analysis based on historical market data<br>
        <span style="display: block; margin-top: 12px; font-size: 11px;">
            This analysis is provided for informational purposes only and does not constitute investment advice.
        </span>
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
