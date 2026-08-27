
## Symbols and scope

The analysis uses four Indian securities:

| Symbol | Company | Reason for selection |
|---|---|---|
| INFY.NS | Infosys | Major NSE-listed Indian IT services company, providing exposure to the technology sector. |
| RELIANCE.NS | Reliance Industries | Major NSE-listed Indian conglomerate with exposure across energy, retail and telecommunications. |
| TATASTEEL.BO | Tata Steel | Major BSE-listed Indian steel producer, providing exposure to the metals and industrial sector. |
| ICICIBANK.NS | ICICI Bank | Major NSE-listed Indian private-sector bank, providing exposure to the financial services and banking sector. |

The universe is intentionally limited to four securities so that the analysis
can produce focused and defensible claims across different sectors within the
available time.

---

### Claims

The analysis compares Infosys (`INFY.NS`), Reliance Industries (`RELIANCE.NS`),
Tata Steel (`TATASTEEL.BO`), and ICICI Bank (`ICICIBANK.NS`) using
performance, volatility, and drawdown metrics.

| # | Claim | Evidence / Metric | Chart Artefact |
|---|---|---|---|
| 1 | **Performance:** Infosys delivered the highest total return among the analysed securities, with a total return of **2.14%**. The average return across all analysed securities was **0.08%**. | Total return = `((final close / initial close) - 1) × 100` | `artefacts/market_dashboard.html#performance` |
| 2 | **Volatility:** The analysed securities recorded an average daily-return volatility of **1.22%**. | Standard deviation of close-to-close daily returns | `artefacts/market_dashboard.html#volatility` |
| 3 | **Drawdown:** Infosys experienced the largest maximum peak-to-trough drawdown among the analysed securities, with a maximum drawdown of **-6.36%**. | Maximum drawdown = `((close / running peak) - 1) × 100` | `artefacts/market_dashboard.html#drawdown` |

## Scope and interpretation

The claims are based on non-synthetic market observations stored in DuckDB.
The analysis compares the four securities over their common available
analysis period.

The results describe observed historical performance during the analysis
period and do not imply future investment performance.