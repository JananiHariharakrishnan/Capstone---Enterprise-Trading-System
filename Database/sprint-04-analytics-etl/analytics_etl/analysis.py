import pandas as pd


def calculate_total_return(df: pd.DataFrame) -> float:
    """
    Calculate total percentage return for a single security.

    Formula:
        ((last close / first close) - 1) * 100
    """

    data = df.sort_values("date").copy()

    first_close = data["close"].iloc[0]
    last_close = data["close"].iloc[-1]

    return ((last_close / first_close) - 1) * 100


def calculate_volatility(df: pd.DataFrame) -> float:
    """
    Calculate daily-return volatility as a percentage.

    Volatility is the standard deviation of daily percentage returns.
    """

    data = df.sort_values("date").copy()

    data["daily_return"] = data["close"].pct_change()

    volatility = data["daily_return"].std()

    return volatility * 100


def calculate_max_drawdown(df: pd.DataFrame) -> float:
    """
    Calculate the maximum peak-to-trough drawdown as a percentage.
    """

    data = df.sort_values("date").copy()

    running_peak = data["close"].cummax()

    drawdown = (data["close"] / running_peak) - 1

    return drawdown.min() * 100


def calculate_metrics(df: pd.DataFrame) -> dict:
    """
    Calculate all three metrics for one security.
    """

    return {
        "symbol": df["symbol"].iloc[0],
        "total_return": calculate_total_return(df),
        "volatility": calculate_volatility(df),
        "max_drawdown": calculate_max_drawdown(df),
    }


def compare_securities(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Calculate metrics for multiple securities.

    Parameters
    ----------
    data:
        Dictionary where the key is the security symbol and the value
        is its cleaned candle DataFrame.

    Example:
        {
            "INFY.NS": infy_df,
            "RELIANCE.NS": reliance_df,
            "TATASTEEL.BO": tata_steel_df
        }

    Returns
    -------
    pandas.DataFrame
        One row per security with return, volatility and drawdown.
    """

    results = []

    for symbol, df in data.items():
        metrics = calculate_metrics(df)
        metrics["symbol"] = symbol
        results.append(metrics)

    return pd.DataFrame(results)
