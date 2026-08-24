from analytics_etl.extract import extract
from analytics_etl.transform import transform
from analytics_etl.load import load
def main():
    raw_data = extract()
    clean_data = transform(raw_data)
    load(clean_data)