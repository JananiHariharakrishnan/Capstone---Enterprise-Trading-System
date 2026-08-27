import json
import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


logger = logging.getLogger(__name__)

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache"
DEFAULT_SYMBOLS = ("INFY.NS", "RELIANCE.NS", "TATASTEEL.BO")
MAX_RETRIES = 3
BACKOFF_SECONDS = 1

load_dotenv(ENV_FILE)

BASE_URL = os.getenv("FAUXNANCE_BASE_URL")
if not BASE_URL:
    raise RuntimeError(f"FAUXNANCE_BASE_URL is not set in {ENV_FILE}")
BASE_URL = BASE_URL.rstrip("/")


class RateLimitError(RuntimeError):
    """Raised when the API daily quota has been reached."""


class SymbolRequestError(RuntimeError):
    """Raised when the API rejects one symbol request."""


def _get_api_key() -> str:
    api_key = os.getenv("FAUXNANCE_API_KEY")
    if not api_key:
        raise RuntimeError(f"FAUXNANCE_API_KEY is not set in {ENV_FILE}")
    return api_key


def _cache_path(symbol: str, start_date: str, end_date: str) -> Path:
    safe_symbol = symbol.replace(":", "_").replace("/", "_")
    return CACHE_DIR / f"{safe_symbol}_{start_date}_{end_date}.json"


def _request(
    symbol: str,
    start_date: str,
    end_date: str,
    api_key: str,
) -> dict:
    """Fetch one raw candle response, retrying temporary failures."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                f"{BASE_URL}/candles/{symbol}",
                params={"start": start_date, "end": end_date},
                headers={"X-Api-Key": api_key},
                timeout=10,
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt == MAX_RETRIES - 1:
                logger.error("NETWORK_ERROR symbol=%s attempts=%s", symbol, MAX_RETRIES)
                raise

            delay = BACKOFF_SECONDS * (2**attempt)
            logger.warning("NETWORK_ERROR symbol=%s retry=%s delay=%s", symbol, attempt + 1, delay)
            time.sleep(delay)
            continue

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            logger.error(
                "RATE_LIMITED symbol=%s retry_after=%s",
                symbol,
                retry_after,
            )
            raise RateLimitError(
                f"API rate limit reached for {symbol}. Retry-After={retry_after}"
            )

        if 400 <= response.status_code < 500:
            logger.error(
                "SYMBOL_REQUEST_ERROR symbol=%s status=%s message=%s",
                symbol,
                response.status_code,
                response.text,
            )
            raise SymbolRequestError(
                f"{symbol}: HTTP {response.status_code}: {response.text}"
            )

        if response.status_code >= 500:
            if attempt == MAX_RETRIES - 1:
                response.raise_for_status()

            delay = BACKOFF_SECONDS * (2**attempt)
            logger.warning("SERVER_ERROR symbol=%s retry=%s delay=%s", symbol, attempt + 1, delay)
            time.sleep(delay)
            continue

        response.raise_for_status()
        return response.json()

    raise RuntimeError(f"Request failed for {symbol}")


def extract(
    symbols=None,
    start_date="2025-08-26",
    end_date="2026-08-26",
):
    """Return raw candle responses, using the cache whenever possible."""
    symbols = DEFAULT_SYMBOLS if symbols is None else symbols
    results = {}
    api_key = None
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    for symbol in symbols:
        cache_file = _cache_path(symbol, start_date, end_date)

        if cache_file.exists():
            print(f"CACHE HIT: {symbol}")
            logger.info("CACHE_HIT symbol=%s", symbol)
            with cache_file.open("r", encoding="utf-8") as file:
                results[symbol] = json.load(file)
            continue

        if api_key is None:
            api_key = _get_api_key()

        print(f"API FETCH: {symbol}")
        logger.info("FETCH symbol=%s start=%s end=%s", symbol, start_date, end_date)
        try:
            raw_response = _request(symbol, start_date, end_date, api_key)
        except RateLimitError:
            raise
        except SymbolRequestError as exc:
            logger.error("SYMBOL_FAILED symbol=%s reason=%s", symbol, exc)
            continue

        with cache_file.open("w", encoding="utf-8") as file:
            json.dump(raw_response, file, indent=2)
        results[symbol] = raw_response

    return results