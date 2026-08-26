from .extract import extract
from .transform import transform
from .load import load


def run():
    raw = extract()

    transformed = transform(raw)

    load(transformed)