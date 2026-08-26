import os
import requests
from dotenv import load_dotenv
from pathlib import Path


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

load_dotenv(ENV_PATH)

def get_config():
    base_url = os.getenv("FAUXNANCE_BASE_URL")
    api_key = os.getenv("FAUXNANCE_API_KEY")

    if not base_url:
        raise RuntimeError("FAUXNANCE_BASE_URL missing")

    if not api_key:
        raise RuntimeError("FAUXNANCE_API_KEY missing")

    return base_url, api_key


def health_check():
    """
    Health endpoint does not require API key.
    """

    base_url, _ = get_config()

    response = requests.get(
        f"{base_url}/health",
        timeout=10
    )

    response.raise_for_status()

    return response.json()


def usage_check():
    """
    Usage endpoint requires API key.
    """

    base_url, api_key = get_config()

    response = requests.get(
        f"{base_url}/usage",
        headers={
            "X-Api-Key": api_key
        },
        timeout=10
    )

    response.raise_for_status()

    return response.json()


def fetch_candles(symbol):

    base_url, api_key = get_config()

    response = requests.get(
        f"{base_url}/candles/{symbol}",
        headers={
            "X-Api-Key": api_key
        },
        timeout=20
    )

    response.raise_for_status()

    return response.json()