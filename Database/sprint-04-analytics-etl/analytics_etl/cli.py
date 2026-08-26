from analytics_etl.pipeline import run


def main():
    print("=== ETL START ===")
    result = run()
    print(f"Extracted symbols: {result['symbols_extracted']}")
    print(f"Transformed rows: {result['rows_transformed']}")
    print(f"Loaded rows: {result['rows_loaded']}")
    print("=== ETL COMPLETE ===")


if __name__ == "__main__":
    main()