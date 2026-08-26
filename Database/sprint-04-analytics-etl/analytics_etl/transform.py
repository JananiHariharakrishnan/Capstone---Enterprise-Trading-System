# analytics_etl/transform.py

from datetime import date
from typing import Any


REQUIRED_FIELDS = {
    "date",
    "open",
    "high",
    "low",
    "close",
}


def _to_float(value: Any) -> float:
    if value is None:
        raise ValueError("missing numeric value")

    return float(value)


def _transform_candle(
    symbol: str,
    candle: dict[str, Any],
) -> dict[str, Any] | None:

    # ------------------------------------------------------------------
    # Missing required fields
    # ------------------------------------------------------------------

    missing = REQUIRED_FIELDS - candle.keys()

    if missing:
        return None

    try:
        # --------------------------------------------------------------
        # Date
        # --------------------------------------------------------------

        candle_date = date.fromisoformat(
            str(candle["date"])
        )

        # --------------------------------------------------------------
        # Prices
        # --------------------------------------------------------------

        open_price = _to_float(candle["open"])
        high = _to_float(candle["high"])
        low = _to_float(candle["low"])
        close = _to_float(candle["close"])

        # --------------------------------------------------------------
        # Volume
        # --------------------------------------------------------------

        volume = candle.get("volume")

        if volume is not None:
            volume = int(volume)

    except (ValueError, TypeError):
        return None

    # ------------------------------------------------------------------
    # Positive price validation
    # ------------------------------------------------------------------

    if open_price <= 0:
        return None

    if high <= 0:
        return None

    if low <= 0:
        return None

    if close <= 0:
        return None

    # ------------------------------------------------------------------
    # OHLC consistency
    # ------------------------------------------------------------------

    # A candle cannot have high below low.
    if high < low:
        return None

    # Open must lie inside the day's trading range.
    if not low <= open_price <= high:
        return None

    # Close must lie inside the day's trading range.
    if not low <= close <= high:
        return None

    # ------------------------------------------------------------------
    # Volume validation
    # ------------------------------------------------------------------

    if volume is not None and volume < 0:
        return None

    # ------------------------------------------------------------------
    # Derived metrics
    # ------------------------------------------------------------------

    daily_change = close - open_price

    daily_change_pct = (
        (daily_change / open_price) * 100
    )

    return {
        "symbol": symbol,
        "date": candle_date.isoformat(),
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "synthetic": bool(
            candle.get("synthetic", False)
        ),
        "daily_change": daily_change,
        "daily_change_pct": daily_change_pct,
    }


def transform(data):
    """
    Pure transformation of raw Fauxnance responses.

    Input:
        Raw API responses.

    Output:
        List of cleaned candle records.

    This function:
        - does not access the environment
        - does not access the network
        - does not write files
        - does not write to a database
    """

    if not isinstance(data, dict):
        raise ValueError("data must be a dictionary")

    output = []

    for symbol, response in data.items():

        if not isinstance(response, dict):
            continue

        payload = response.get("data")

        if not isinstance(payload, dict):
            continue

        response_symbol = payload.get(
            "symbol",
            symbol,
        )

        candles = payload.get("candles")

        if not isinstance(candles, list):
            continue

        for candle in candles:

            if not isinstance(candle, dict):
                continue

            transformed = _transform_candle(
                response_symbol,
                candle,
            )

            if transformed is not None:
                output.append(transformed)

    return output