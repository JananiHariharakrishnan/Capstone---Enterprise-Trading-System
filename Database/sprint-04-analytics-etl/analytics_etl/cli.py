from analytics_etl.extract import extract
from analytics_etl.transform import transform
from analytics_etl.load import load
import json

def main():
    raw_data = extract()
    print(
        json.dumps(
            raw_data,
            indent=2
        )
    )
    clean_data = transform(raw_data)
    load(clean_data)
    
if __name__ == "__main__":
    main()