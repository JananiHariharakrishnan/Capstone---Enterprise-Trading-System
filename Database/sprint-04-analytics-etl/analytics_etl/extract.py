import json
from pathlib import Path

from analytics_etl.client import fetch_candles


CACHE_DIR = Path(".cache")


SYMBOLS = [
    "INFY.NS",
    "RELIANCE.NS",
    "TATASTEEL.BO"
]


def cache_file(symbol):

    CACHE_DIR.mkdir(exist_ok=True)

    return CACHE_DIR / f"{symbol}.json"



def load_cache(symbol):

    file = cache_file(symbol)

    if file.exists():

        with open(file, "r") as f:
            return json.load(f)

    return None



def save_cache(symbol, data):

    file = cache_file(symbol)

    with open(file, "w") as f:
        json.dump(
            data,
            f,
            indent=2
        )



def extract():

    responses = {}

    for symbol in SYMBOLS:

        cached = load_cache(symbol)

        if cached:

            print(
                f"{symbol}: using cache"
            )

            responses[symbol] = cached
            continue


        print(
            f"{symbol}: fetching API"
        )

        raw = fetch_candles(symbol)

        save_cache(
            symbol,
            raw
        )

        responses[symbol] = raw


    return responses