'''
Temprory code until the extract , load and transform file is done
'''

import pandas as pd

from analytics_etl.analysis import compare_securities
from analytics_etl.charts import (
    create_performance_chart,
    create_volatility_chart,
    create_drawdown_chart,
)


def create_sample_data(symbol):
    return pd.DataFrame(
        {
            "symbol": [symbol] * 6,
            "date": pd.to_datetime(
                [
                    "2026-07-01",
                    "2026-07-02",
                    "2026-07-03",
                    "2026-07-06",
                    "2026-07-07",
                    "2026-07-08",
                ]
            ),
            "close": [
                100,
                103,
                101,
                106,
                104,
                108,
            ],
        }
    )


def main():
    # Temporary sample data.
    # This will later be replaced by the real ETL output.

    infy_df = create_sample_data("INFY.NS")
    reliance_df = create_sample_data("RELIANCE.NS")
    tata_df = create_sample_data("TATASTEEL.BO")

    data = {
        "INFY.NS": infy_df,
        "RELIANCE.NS": reliance_df,
        "TATASTEEL.BO": tata_df,
    }

    # Calculate the three metrics.
    metrics = compare_securities(data)

    print("\nAnalysis results:")
    print(metrics.to_string(index=False))

    # Create charts.
    create_performance_chart(
        metrics,
        "artefacts/performance.html",
    )

    create_volatility_chart(
        metrics,
        "artefacts/volatility.html",
    )

    create_drawdown_chart(
        metrics,
        "artefacts/drawdown.html",
    )

    print("\nCharts created in artefacts/")


if __name__ == "__main__":
    main()

'''
Permanent code
from analytics_etl.analysis import compare_securities
from analytics_etl.charts import (
    create_performance_chart,
    create_volatility_chart,
    create_drawdown_chart,
)

# These will eventually come from your ETL pipeline.
infy_df = ...
reliance_df = ...
tata_df = ...

data = {
    "INFY.NS": infy_df,
    "RELIANCE.NS": reliance_df,
    "TATASTEEL.BO": tata_df,
}

metrics = compare_securities(data)

print(metrics.to_string(index=False))

create_performance_chart(
    metrics,
    "artefacts/performance.html",
)

create_volatility_chart(
    metrics,
    "artefacts/volatility.html",
)

create_drawdown_chart(
    metrics,
    "artefacts/drawdown.html",
)

'''

