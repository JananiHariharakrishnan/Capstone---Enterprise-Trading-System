# Index Justifications

## Purpose

The trading platform uses indexes to improve the performance of frequently
executed queries.

Indexes are not free. Each index requires additional storage and must be
maintained whenever rows are inserted, deleted, or relevant indexed columns
are updated. Therefore, indexes are added only where there is a clear query
pattern that benefits from them.

Primary-key and unique-constraint indexes are not counted here as deliberate
performance indexes because PostgreSQL creates those automatically to enforce
constraints.

---

## 1. Orders by Account and Status

### Index

```sql
CREATE INDEX idx_orders_account_status
ON orders(account_id, status);
```

### Query Supported

```sql
SELECT
    order_id,
    ticker,
    side,
    type,
    quantity,
    filled_quantity,
    price,
    status,
    created_at
FROM orders
WHERE account_id = ?
  AND status = ?
ORDER BY created_at DESC;
```

### Why This Index Is Needed

A common trading-platform operation is retrieving orders belonging to a
particular account and filtering them by lifecycle status.

Examples include:

- Pending orders for an account
- Filled orders for an account
- Cancelled orders for an account
- Rejected orders for an account

The composite index starts with `account_id`, which narrows the search to one
account. The second column, `status`, further restricts the matching rows.

### Without the Index

As the orders table grows, PostgreSQL may perform a sequential scan and inspect
many unrelated orders before finding the requested account and status.

### With the Index

PostgreSQL can use an index scan or bitmap index scan to locate the relevant
rows more efficiently.

### Write Cost

Every new order adds an entry to this index. Updates to `account_id` or
`status` also require index maintenance.

This cost is justified because retrieving orders by account and status is a
core operational query.

---

## 2. Orders by Instrument

### Index

```sql
CREATE INDEX idx_orders_ticker
ON orders(ticker);
```

### Query Supported

```sql
SELECT
    order_id,
    account_id,
    side,
    quantity,
    price,
    status,
    created_at
FROM orders
WHERE ticker = ?
ORDER BY created_at DESC;
```

### Why This Index Is Needed

Trading operations and reporting may need to retrieve all orders associated
with a particular instrument.

For example:

```text
All AAPL orders
All MSFT orders
All NVDA orders
```

The `ticker` index allows PostgreSQL to locate orders for the requested
instrument without scanning unrelated orders.

### Without the Index

PostgreSQL may perform a sequential scan over the complete orders table and
compare the ticker of every row.

### With the Index

PostgreSQL can locate rows matching the ticker through the index.

### Write Cost

Each new order creates another index entry. Updates to the ticker also require
index maintenance.

The additional cost is justified by instrument-level trading and reporting
queries.

---

## 3. Cash History by Account and Time

### Index

```sql
CREATE INDEX idx_cash_history_account_time
ON cash_history(account_id, created_at DESC);
```

### Query Supported

```sql
SELECT
    cash_history_id,
    order_id,
    entry_type,
    amount,
    balance_after,
    created_at
FROM cash_history
WHERE account_id = ?
ORDER BY created_at DESC
LIMIT 50;
```

### Why This Index Is Needed

Cash history is normally retrieved for a particular account, with the newest
transactions shown first.

The index begins with `account_id` and then stores the timestamp in descending
order.

This matches the filtering and ordering pattern of the query.

### Without the Index

PostgreSQL may need to scan many cash-history rows belonging to other accounts
and then sort the matching rows by timestamp.

### With the Index

PostgreSQL can find records belonging to the requested account and access them
in descending timestamp order.

This is particularly useful for queries using `LIMIT`, because PostgreSQL can
stop after obtaining the required number of recent records.

### Write Cost

`cash_history` is append-heavy, so every cash event creates an additional
index entry.

The additional write and storage cost is justified because recent cash
activity is frequently needed for account statements, auditing and
reconciliation.

---

## 4. Position History by Account and Time

### Index

```sql
CREATE INDEX idx_positions_history_account_time
ON positions_history(
    account_id,
    snapshot_timestamp DESC
);
```

### Query Supported

```sql
SELECT
    ticker,
    quantity,
    market_price,
    snapshot_timestamp
FROM positions_history
WHERE account_id = ?
ORDER BY snapshot_timestamp DESC
LIMIT 1;
```

### Why This Index Is Needed

The platform stores historical position snapshots.

A common operation is retrieving the latest snapshot for a particular account.

The index first groups entries by `account_id` and then orders them by
`snapshot_timestamp DESC`.

### Without the Index

PostgreSQL may scan historical snapshots and sort matching records to determine
the newest snapshot.

As position history grows, this becomes increasingly expensive.

### With the Index

PostgreSQL can locate the requested account and access the most recent records
directly.

The `LIMIT 1` query particularly benefits because the database can stop after
finding the first matching index entry.

### Write Cost

Every position snapshot adds another index entry.

Because position history is expected to grow continuously, this introduces
additional storage and insertion cost.

The cost is justified by the importance of efficiently retrieving recent
portfolio state.

---

## 5. Position History by Instrument and Time

### Index

```sql
CREATE INDEX idx_positions_history_ticker_time
ON positions_history(
    ticker,
    snapshot_timestamp DESC
);
```

### Query Supported

```sql
SELECT
    account_id,
    quantity,
    market_price,
    snapshot_timestamp
FROM positions_history
WHERE ticker = ?
ORDER BY snapshot_timestamp DESC;
```

### Why This Index Is Needed

Historical position information may also be analysed by instrument.

For example, the platform may need to retrieve recent historical positions
associated with a particular ticker.

The index groups records by ticker and keeps them ordered by snapshot time.

### Without the Index

PostgreSQL may scan the entire position-history table and sort the matching
records.

### With the Index

PostgreSQL can directly locate snapshots for the requested ticker in
timestamp order.

### Write Cost

Each new position snapshot requires another index entry in addition to the
account/time index.

Because this table is append-heavy, this index should be retained only while
instrument-level historical queries justify its maintenance cost.

---

## 6. Executions by Order

### Index

```sql
CREATE INDEX idx_executions_order
ON executions(order_id);
```

### Query Supported

```sql
SELECT
    execution_id,
    broker_execution_id,
    quantity,
    execution_price,
    executed_at
FROM executions
WHERE order_id = ?
ORDER BY executed_at;
```

### Why This Index Is Needed

A single order can produce multiple executions.

For example:

```text
Order: 100 shares

Execution 1: 30 shares
Execution 2: 40 shares
Execution 3: 30 shares
```

The application therefore needs an efficient way to retrieve every execution
belonging to an order.

### Without the Index

PostgreSQL may scan the complete executions table to locate executions
belonging to the requested order.

### With the Index

PostgreSQL can directly locate execution records through `order_id`.

### Write Cost

Each broker execution creates another index entry.

The cost is justified because order-to-execution lookup is fundamental for
trade history, auditing and reconciliation.

---

## 7. Holdings by Account

### Index

```sql
CREATE INDEX idx_holdings_account
ON holdings(account_id);
```

### Query Supported

```sql
SELECT
    ticker,
    quantity,
    average_buy_price
FROM holdings
WHERE account_id = ?;
```

### Why This Index Is Needed

One of the most common portfolio queries is retrieving all current holdings
for an account.

The index allows PostgreSQL to locate the holdings belonging to the requested
account efficiently.

### Without the Index

PostgreSQL may scan holdings belonging to every account.

### With the Index

PostgreSQL can locate the relevant holdings using `account_id`.

### Write Cost

Holding creation and account changes require index maintenance.

The cost is justified because portfolio retrieval by account is a core
application operation.

---

## 8. Holdings by Instrument

### Index

```sql
CREATE INDEX idx_holdings_ticker
ON holdings(ticker);
```

### Query Supported

```sql
SELECT
    account_id,
    quantity,
    average_buy_price
FROM holdings
WHERE ticker = ?;
```

### Why This Index Is Needed

The platform may need to identify accounts currently holding a particular
instrument.

This is useful for instrument exposure analysis and operational reporting.

### Without the Index

PostgreSQL may scan the entire holdings table.

### With the Index

PostgreSQL can directly locate holdings for the requested ticker.

### Write Cost

Every new holding requires an additional index entry.

The index should be retained while instrument-level exposure queries justify
the additional write and storage cost.

---

## 9. Recommendations by Instrument and Time

### Index

```sql
CREATE INDEX idx_recommendations_ticker_time
ON recommendations(
    ticker,
    generated_at DESC
);
```

### Query Supported

```sql
SELECT
    action,
    confidence,
    target_price,
    source,
    generated_at,
    expires_at
FROM recommendations
WHERE ticker = ?
ORDER BY generated_at DESC
LIMIT 1;
```

### Why This Index Is Needed

The application may frequently request the latest recommendation for a
particular instrument.

The index first filters by ticker and then stores recommendations in descending
generation-time order.

### Without the Index

PostgreSQL may scan and sort recommendation records to determine the latest
recommendation.

### With the Index

PostgreSQL can locate the newest recommendation for the ticker directly.

The `LIMIT 1` query makes this index particularly useful.

### Write Cost

Each generated recommendation creates another index entry.

The additional cost is justified when latest-recommendation retrieval is a
frequent operation.

---

## Indexes Created by Constraints

Some indexes exist because PostgreSQL creates them automatically to enforce
primary keys and unique constraints.

Examples include:

```text
accounts(account_id)
accounts(account_number)

orders(order_id)
orders(account_id, idempotency_key)

holdings(holding_id)
holdings(account_id, ticker)

executions(execution_id)
executions(broker_execution_id)
```

These are not counted as deliberate performance indexes in this document.

In particular:

```sql
UNIQUE (account_id, idempotency_key)
```

exists primarily to guarantee idempotency rather than merely improve query
performance.

---

## Index Design Summary

| Index | Main Access Pattern |
|---|---|
| `idx_orders_account_status` | Orders for an account filtered by status |
| `idx_orders_ticker` | Orders for a particular instrument |
| `idx_cash_history_account_time` | Recent cash history for an account |
| `idx_positions_history_account_time` | Latest position history for an account |
| `idx_positions_history_ticker_time` | Position history for an instrument |
| `idx_executions_order` | Executions belonging to an order |
| `idx_holdings_account` | Current portfolio holdings for an account |
| `idx_holdings_ticker` | Accounts holding an instrument |
| `idx_recommendations_ticker_time` | Latest recommendation for an instrument |

---

## Trade-Off Summary

Indexes improve query performance by reducing the amount of data PostgreSQL
needs to scan and, for some queries, by avoiding explicit sorting.

The trade-offs are:

- Additional disk storage
- Additional work during inserts
- Additional work during deletes
- Additional work when indexed columns are updated
- Additional maintenance requirements

For this reason, indexes should be justified by actual access patterns rather
than being added to every column.

The indexes in this design target account order retrieval, instrument order
retrieval, portfolio access, execution lookup, cash history, position history
and recommendation retrieval.

As production data grows, PostgreSQL query plans should be reviewed using
`EXPLAIN` and `EXPLAIN ANALYZE`. Indexes that are not being used or whose
maintenance cost exceeds their benefit should be reconsidered.