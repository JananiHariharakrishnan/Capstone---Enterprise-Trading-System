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

    Daily return is based on consecutive closing prices:

        (current close / previous close) - 1

    Volatility is the standard deviation of daily returns.
    """

    data = df.sort_values("date").copy()

    data["daily_return"] = data["close"].pct_change()

    return data["daily_return"].std() * 100


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
    Calculate all three headline metrics for one security.
    """

    if df.empty:
        raise ValueError("Cannot calculate metrics for an empty DataFrame.")

    required_columns = {"symbol", "date", "close"}

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    return {
        "symbol": df["symbol"].iloc[0],
        "total_return": calculate_total_return(df),
        "volatility": calculate_volatility(df),
        "max_drawdown": calculate_max_drawdown(df),
    }


def compare_securities(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Calculate headline metrics for multiple securities.
    """

    results = []

    for symbol, df in data.items():
        if df.empty:
            raise ValueError(f"No data available for {symbol}.")

        metrics = calculate_metrics(df)
        metrics["symbol"] = symbol
        results.append(metrics)

    return pd.DataFrame(results)


def summarize_data(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Produce supporting dataset coverage statistics.
    """

    results = []

    for symbol, df in data.items():
        data_sorted = df.sort_values("date").copy()

        results.append(
            {
                "symbol": symbol,
                "observations": len(data_sorted),
                "start_date": data_sorted["date"].min(),
                "end_date": data_sorted["date"].max(),
                "min_close": data_sorted["close"].min(),
                "max_close": data_sorted["close"].max(),
            }
        )

    return pd.DataFrame(results)