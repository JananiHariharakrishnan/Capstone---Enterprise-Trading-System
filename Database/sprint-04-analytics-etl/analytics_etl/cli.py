from analytics_etl.extract import extract
from analytics_etl.transform import transform
from analytics_etl.load import load


def main():
    print("=== ETL START ===")

    print("1. Extracting...")
    raw_data = extract()
    print(f"   Extracted {len(raw_data)} symbols")

    print("2. Transforming...")
    transformed_data = transform(raw_data)
    print(f"   Transformed {len(transformed_data)} symbols")

    print("3. Loading...")
    load(transformed_data)

    print("=== ETL COMPLETE ===")


if __name__ == "__main__":
    main()