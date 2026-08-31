from .pipeline.extract import extract
from .pipeline.transform import transform
from .pipeline.load import load


def run():
    """Run extract, transform, and load in order."""
    raw = extract()
    transformed = transform(raw)
    loaded_rows = load(transformed)

    return {
        "symbols_extracted": len(raw),
        "rows_transformed": len(transformed),
        "rows_loaded": loaded_rows,
    }