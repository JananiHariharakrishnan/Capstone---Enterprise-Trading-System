import logging

from analytics_etl.pipeline import run


logger = logging.getLogger(__name__)


def main() -> int:
    print("=== ETL START ===")
    try:
        result = run()
    except Exception as exc:
        logger.error("ETL_FAILED reason=%s", exc)
        print(f"ETL failed: {exc}")
        return 1

    print(f"Extracted symbols: {result['symbols_extracted']}")
    print(f"Transformed rows: {result['rows_transformed']}")
    print(f"Loaded rows: {result['rows_loaded']}")
    print("=== ETL COMPLETE ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


if __name__ == "__main__":
    main()