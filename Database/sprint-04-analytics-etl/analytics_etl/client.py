import os
import requests
from dotenv import load_dotenv
from pathlib import Path


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

load_dotenv(ENV_PATH)


class ClientError(RuntimeError):
    """Raised when a Fauxnance request cannot be completed."""


def _get_base_url():
    base_url = os.getenv("FAUXNANCE_BASE_URL")
    if not base_url:
        raise RuntimeError("FAUXNANCE_BASE_URL missing")
    return base_url.rstrip("/")


def _get_api_key():
    api_key = os.getenv("FAUXNANCE_API_KEY")

    if not api_key:
        raise RuntimeError("FAUXNANCE_API_KEY missing")
    return api_key


def get_config():
    """Return the configured API URL and authenticated API key."""
    return _get_base_url(), _get_api_key()


def _get_json(url, headers=None, timeout=10):
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        raise ClientError(f"Fauxnance request failed: HTTP/network error for {url}") from exc
    except ValueError as exc:
        raise ClientError(f"Fauxnance returned invalid JSON for {url}") from exc


def health_check():
    """
    Health endpoint does not require API key.
    """

    return _get_json(f"{_get_base_url()}/health")


def usage_check():
    """
    Usage endpoint requires API key.
    """

    return _get_json(
        f"{_get_base_url()}/usage",
        headers={"X-Api-Key": _get_api_key()},
    )


def fetch_candles(symbol):

    return _get_json(
        f"{_get_base_url()}/candles/{symbol}",
        headers={"X-Api-Key": _get_api_key()},
        timeout=20,
    )