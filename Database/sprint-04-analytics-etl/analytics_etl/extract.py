import json
import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

# extract.py is:
#
# Database/
#   sprint-04-analytics-etl/
#       analytics_etl/
#           extract.py
#
# Therefore parents[2] = Database/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.getenv("FAUXNANCE_BASE_URL")

if not BASE_URL:
    raise RuntimeError(
        f"FAUXNANCE_BASE_URL is not set. "
        f"Expected it in {ENV_FILE}"
    )

BASE_URL = BASE_URL.rstrip("/")

CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache"

MAX_RETRIES = 3
BACKOFF_SECONDS = 1


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class RateLimitError(RuntimeError):
    """Raised when Fauxnance returns HTTP 429."""

    pass


class SymbolRequestError(RuntimeError):
    """Raised when a symbol receives a non-retryable 4xx response."""

    pass


# ---------------------------------------------------------------------------
# API key
# ---------------------------------------------------------------------------

def _get_api_key() -> str:
    key = os.getenv("FAUXNANCE_API_KEY")

    if not key:
        raise RuntimeError(
            f"FAUXNANCE_API_KEY is not set. "
            f"Expected it in {ENV_FILE}"
        )

    return key


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _cache_path(
    symbol: str,
    start_date: str,
    end_date: str,
) -> Path:

    safe_symbol = symbol.replace(":", "_").replace("/", "_")

    return CACHE_DIR / (
        f"{safe_symbol}_{start_date}_{end_date}.json"
    )


# ---------------------------------------------------------------------------
# HTTP request
# ---------------------------------------------------------------------------

def _request(
    symbol: str,
    start_date: str,
    end_date: str,
    api_key: str,
) -> dict:

    url = f"{BASE_URL}/candles/{symbol}"

    params = {
        "start": start_date,
        "end": end_date,
    }

    # -----------------------------------------------------------------------
    # IMPORTANT:
    # Real Fauxnance API uses x-api-key.
    #
    # Do NOT log this dictionary because it contains the secret.
    # -----------------------------------------------------------------------

    headers = {
        "x-api-key": api_key,
    }

    for attempt in range(MAX_RETRIES):

        try:

            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=10,
            )

        # -------------------------------------------------------------------
        # Timeout
        # -------------------------------------------------------------------

        except requests.exceptions.Timeout:

            if attempt == MAX_RETRIES - 1:

                logger.error(
                    "NETWORK_TIMEOUT symbol=%s attempts=%s",
                    symbol,
                    MAX_RETRIES,
                )

                raise

            delay = BACKOFF_SECONDS * (2 ** attempt)

            logger.warning(
                "NETWORK_TIMEOUT symbol=%s retry=%s delay=%s",
                symbol,
                attempt + 1,
                delay,
            )

            time.sleep(delay)

            continue

        # -------------------------------------------------------------------
        # Connection error
        # -------------------------------------------------------------------

        except requests.exceptions.ConnectionError:

            if attempt == MAX_RETRIES - 1:

                logger.error(
                    "CONNECTION_ERROR symbol=%s attempts=%s",
                    symbol,
                    MAX_RETRIES,
                )

                raise

            delay = BACKOFF_SECONDS * (2 ** attempt)

            logger.warning(
                "CONNECTION_ERROR symbol=%s retry=%s delay=%s",
                symbol,
                attempt + 1,
                delay,
            )

            time.sleep(delay)

            continue

        # -------------------------------------------------------------------
        # 429 - rate limit
        # -------------------------------------------------------------------

        if response.status_code == 429:

            retry_after = response.headers.get("Retry-After")

            logger.error(
                "RATE_LIMITED symbol=%s retry_after=%s",
                symbol,
                retry_after,
            )

            raise RateLimitError(
                f"Fauxnance rate limit reached for {symbol}. "
                f"Retry-After={retry_after}"
            )

        # -------------------------------------------------------------------
        # Other 4xx
        # -------------------------------------------------------------------

        if 400 <= response.status_code < 500:

            message = response.text

            logger.error(
                "REQUEST_ERROR symbol=%s status=%s message=%s",
                symbol,
                response.status_code,
                message,
            )

            raise SymbolRequestError(
                f"{symbol}: HTTP {response.status_code}: {message}"
            )

        # -------------------------------------------------------------------
        # 5xx - retry with exponential backoff
        # -------------------------------------------------------------------

        if response.status_code >= 500:

            if attempt == MAX_RETRIES - 1:

                logger.error(
                    "SERVER_ERROR symbol=%s status=%s attempts=%s",
                    symbol,
                    response.status_code,
                    MAX_RETRIES,
                )

                response.raise_for_status()

            delay = BACKOFF_SECONDS * (2 ** attempt)

            logger.warning(
                "SERVER_ERROR symbol=%s retry=%s delay=%s",
                symbol,
                attempt + 1,
                delay,
            )

            time.sleep(delay)

            continue

        # -------------------------------------------------------------------
        # 200
        # -------------------------------------------------------------------

        response.raise_for_status()

        return response.json()

    raise RuntimeError(
        f"Request failed for {symbol}"
    )


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------

def extract(
    symbols=None,
    start_date="2025-08-26",
    end_date="2026-08-26",
):
    """
    Fetch raw Fauxnance API responses.

    Extract is responsible for:
        - API key
        - network access
        - retry handling
        - rate-limit handling
        - caching raw responses

    It does NOT transform the payload.
    """

    if symbols is None:

        symbols = [
            "INFY.NS",
            "RELIANCE.NS",
            "TATASTEEL.BO",
        ]

    api_key = _get_api_key()

    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    results = {}

    for symbol in symbols:

        cache_file = _cache_path(
            symbol,
            start_date,
            end_date,
        )

        # -------------------------------------------------------------------
        # Cache hit
        # -------------------------------------------------------------------

        if cache_file.exists():

            logger.info(
                "CACHE_HIT symbol=%s",
                symbol,
            )

            with cache_file.open(
                "r",
                encoding="utf-8",
            ) as fh:

                results[symbol] = json.load(fh)

            continue

        # -------------------------------------------------------------------
        # Fetch
        # -------------------------------------------------------------------

        logger.info(
            "FETCH symbol=%s start=%s end=%s",
            symbol,
            start_date,
            end_date,
        )

        try:

            raw = _request(
                symbol,
                start_date,
                end_date,
                api_key,
            )

        # 429 stops the entire batch
        except RateLimitError:

            raise

        # Other 4xx skips only this symbol
        except SymbolRequestError as exc:

            logger.error(
                "SYMBOL_FAILED symbol=%s reason=%s",
                symbol,
                exc,
            )

            continue

        # -------------------------------------------------------------------
        # Save RAW response
        # -------------------------------------------------------------------

        with cache_file.open(
            "w",
            encoding="utf-8",
        ) as fh:

            json.dump(
                raw,
                fh,
                indent=2,
            )

        results[symbol] = raw

    return results