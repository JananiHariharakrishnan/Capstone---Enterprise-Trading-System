import logging

import pandas as pd


logger = logging.getLogger(__name__)


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


def transform(raw_data: dict) -> pd.DataFrame:
    """Convert raw API responses into a validated candle DataFrame."""
    if not isinstance(raw_data, dict):
        raise ValueError("raw_data must be a dictionary")

    rows = []
    for symbol, response in raw_data.items():
        if not isinstance(response, dict):
            logger.warning("INVALID_PAYLOAD symbol=%s reason=response_not_object", symbol)
            continue

        data = response.get("data", {})
        if not isinstance(data, dict) or not isinstance(data.get("candles"), list):
            logger.warning("INVALID_PAYLOAD symbol=%s reason=missing_candles", symbol)
            continue

        response_symbol = data.get("symbol", symbol)
        for candle in data["candles"]:
            if isinstance(candle, dict):
                rows.append({"symbol": response_symbol, **candle})

    if not rows:
        return pd.DataFrame(columns=COLUMNS)

    frame = pd.DataFrame(rows)
    required = ["symbol", "date", "open", "high", "low", "close"]

    for column in ["open", "high", "low", "close", "volume"]:
        if column not in frame:
            frame[column] = pd.NA
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["date"] = pd.to_datetime(
        frame["date"], format="%Y-%m-%d", errors="coerce"
    )
    missing_required = frame[required].isna().any(axis=1)
    if missing_required.any():
        logger.warning(
            "INVALID_CANDLES dropped=%s reason=missing_or_invalid_required_field",
            int(missing_required.sum()),
        )
    frame = frame[~missing_required]

    valid_prices = (
        (frame[["open", "high", "low", "close"]] > 0).all(axis=1)
        & (frame["high"] >= frame["low"])
        & frame["open"].between(frame["low"], frame["high"])
        & frame["close"].between(frame["low"], frame["high"])
    )
    valid_volume = frame["volume"].isna() | (frame["volume"] >= 0)
    invalid_rows = ~(valid_prices & valid_volume)
    if invalid_rows.any():
        logger.warning("INVALID_CANDLES dropped=%s", int(invalid_rows.sum()))
    frame = frame[~invalid_rows]

    frame = frame.drop_duplicates(subset=["symbol", "date"], keep="last")
    if "synthetic" not in frame:
        frame["synthetic"] = False
    else:
        frame["synthetic"] = frame["synthetic"].fillna(False).astype(bool)
    frame["daily_change"] = frame["close"] - frame["open"]
    frame["daily_change_pct"] = frame["daily_change"] / frame["open"] * 100
    frame["date"] = frame["date"].dt.date

    return frame[COLUMNS].sort_values(["symbol", "date"]).reset_index(drop=True)
