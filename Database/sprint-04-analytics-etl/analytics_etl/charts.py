from pathlib import Path

import pandas as pd
import plotly.graph_objects as go


COMPANY_NAMES = {
    "INFY.NS": "Infosys",
    "RELIANCE.NS": "Reliance Industries",
    "TATASTEEL.BO": "Tata Steel",
}


def company_name(symbol: str) -> str:
    return COMPANY_NAMES.get(symbol, symbol)


def create_performance_chart(
    metrics: pd.DataFrame,
    output_file: str = "artefacts/performance.html",
) -> None:
    """
    Create a chart comparing total returns.
    """

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    labels = [
        company_name(symbol)
        for symbol in metrics["symbol"]
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=labels,
            y=metrics["total_return"],
            text=[
                f"{value:.2f}%"
                for value in metrics["total_return"]
            ],
            textposition="auto",
        )
    )

    fig.update_layout(
        title="Total Return Comparison of Selected Indian Securities",
        xaxis_title="Company",
        yaxis_title="Total Return (%)",
    )

    fig.write_html(
        output_file,
        include_plotlyjs=True,
    )


def create_volatility_chart(
    metrics: pd.DataFrame,
    output_file: str = "artefacts/volatility.html",
) -> None:
    """
    Create a chart comparing daily-return volatility.
    """

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    labels = [
        company_name(symbol)
        for symbol in metrics["symbol"]
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=labels,
            y=metrics["volatility"],
            text=[
                f"{value:.2f}%"
                for value in metrics["volatility"]
            ],
            textposition="auto",
        )
    )

    fig.update_layout(
        title="Daily Return Volatility Comparison",
        xaxis_title="Company",
        yaxis_title="Volatility (%)",
    )

    fig.write_html(
        output_file,
        include_plotlyjs=True,
    )


def create_drawdown_chart(
    metrics: pd.DataFrame,
    output_file: str = "artefacts/drawdown.html",
) -> None:
    """
    Create a chart comparing maximum drawdown.
    """

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    labels = [
        company_name(symbol)
        for symbol in metrics["symbol"]
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=labels,
            y=metrics["max_drawdown"],
            text=[
                f"{value:.2f}%"
                for value in metrics["max_drawdown"]
            ],
            textposition="auto",
        )
    )

    fig.update_layout(
        title="Maximum Peak-to-Trough Drawdown Comparison",
        xaxis_title="Company",
        yaxis_title="Maximum Drawdown (%)",
    )

    fig.write_html(
        output_file,
        include_plotlyjs=True,
    )
