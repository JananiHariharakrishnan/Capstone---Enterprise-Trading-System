# DESIGN.md

# Executed Trade Retention, Extraction and Growth Design

## 1. Purpose

The trading database stores orders as the record of what the customer requested and
stores executions as the record of what actually traded.

An order describes the requested trade:

- account
- instrument
- side
- quantity
- price
- order type
- order status
- idempotency key
- order creation time

An executed trade needs to retain information beyond the order because an order
represents an instruction while an execution represents an actual fill.

The design therefore retains executions separately from orders.

The database is the source of truth for executed trades. The Sprint 7 analytical
extract reads this data incrementally and transfers it to the analytical store.

---

## 2. Retention Grain

The retention grain is **one row per execution/fill**.

An execution represents a quantity of an order that actually traded at a particular
price and time.

The execution record contains at least:

- execution identifier
- order identifier
- executed quantity
- execution price
- execution timestamp

The order remains the parent business record.

The relationship is:

    account
       |
       +--- orders
              |
              +--- executions

An order can therefore have zero, one, or multiple executions.

For the current Sprint 6 model, the order state is terminal when it reaches a final
state such as `FILLED`, `REJECTED`, or `CANCELLED`. There is no half-filled order
state.

The execution table is still kept separately because the execution is the durable
record of what was actually traded rather than simply what was requested.

For the current simplified trading model, a `FILLED` order has an execution record
representing the filled quantity and price.

The order remains useful for customer-facing order history, while executions provide
the more precise trade-level record required for statements and future analytical
processing.

---

## 3. Why Execution Data Is Retained Separately

The order and execution have different meanings.

An order answers:

    "What did the customer ask the system to do?"

An execution answers:

    "What actually traded?"

Keeping the execution separately avoids making the order row responsible for every
piece of execution information.

This also leaves room for the system to support multiple executions for one order
later without changing the meaning of the order table.

For example:

    Order O1001
        requested quantity = 1,000

    Execution E1
        quantity = 400
        price = 100.20

    Execution E2
        quantity = 600
        price = 100.40

The order is the parent record and the executions are the trade-level records.

The foreign key from executions to orders ensures that an execution cannot exist
without a corresponding order.

---

## 4. Population

Execution rows are populated by the **order execution/trading component**.

The component responsible for processing a successful trade creates the execution
record as part of the same transactional workflow that records the resulting order
state.

The application must not create execution rows merely because an order was received.

The intended flow is:

    1. Receive order.
    2. Persist the order.
    3. Process the order.
    4. If the order executes, create an execution record.
    5. Move the order to its terminal state.
    6. Commit the transaction.

This means the database does not infer executions later from order history.

The execution record is populated at the point where the trading component knows that
the trade actually occurred.

The application owns the business decision to create an execution. The database owns
the structural integrity of the relationship through foreign keys and constraints.

---

## 5. What Is Retained Beyond the Order

The execution retains information that describes the actual trade event.

The important additional information is:

| Information | Why retained |
|---|---|
| Execution ID | Uniquely identifies the actual trade event |
| Order ID | Connects the trade back to the originating order |
| Executed quantity | Records what actually traded |
| Execution price | Records the actual trade price |
| Executed timestamp | Records when the trade occurred |

The order's requested quantity and requested price must not be treated as a substitute
for execution data.

This distinction becomes particularly important if the execution model is expanded
to support multiple fills in a later sprint.

---

# 6. Sprint 7 Incremental Extraction

Sprint 7 requires extracting orders created since a given timestamp rather than
scanning the entire order history.

The extract uses the order creation timestamp as its incremental boundary.

Conceptually:

    SELECT ...
    FROM orders
    WHERE created_on >= :last_successful_extract_timestamp
    ORDER BY created_on ASC;

The extract therefore reads only the portion of the order history that falls within
the requested extraction window.

The extraction process should persist a high-water mark representing the last
successfully processed timestamp.

For example:

    Previous high-water mark:
        2026-08-22 00:00:00

    Current extract:
        orders created on or after 2026-08-22 00:00:00

After the analytical-store load succeeds, the process advances the high-water mark.

The high-water mark must only be advanced after the corresponding extract has been
successfully persisted.

This prevents an unsuccessful analytical load from causing data to be skipped on
the next run.

---

## 7. Incremental Extraction and Duplicate Handling

The extraction boundary should be deterministic.

A timestamp alone can produce ambiguity when multiple orders have the same timestamp.
For that reason, the implementation should use a timestamp plus a stable unique
identifier as the eventual extraction cursor if the volume and ingestion pattern
require it.

The conceptual ordering is:

    ORDER BY created_on ASC, id ASC

The cursor can then represent:

    (created_on, id)

The next extraction retrieves records after that exact position.

This avoids depending on generated identity ordering alone and prevents records with
identical timestamps from being accidentally skipped.

The analytical load should also be designed to tolerate replay of a small boundary
window. Re-reading the last successfully processed records is preferable to silently
losing records.

The analytical destination should therefore use a deterministic business identifier
such as the order ID to make the load idempotent.

---

# 8. Indexing for Incremental Extraction

The current account-oriented order index supports dashboard and history queries:

    (account_id, created_on DESC)

The Sprint 7 extract has a different access pattern because it searches across all
accounts by creation time.

For that reason, a production implementation should add an index on:

    orders(created_on)

This allows the database to locate the incremental extraction range without scanning
the complete orders table.

The index is intentionally separate from the account-oriented index because the two
queries have different leading predicates.

The expected access patterns are therefore:

    Account dashboard:
        account_id + created_on

    Analytical extract:
        created_on

This is a deliberate trade-off: an additional index increases write cost slightly,
but avoids increasingly expensive full-history scans as order volume grows.

---

# 9. Growth to 100x Current Volume

The initial schema is intentionally designed for the current sprint rather than
premature distributed infrastructure.

At 100 times the current volume, the largest growth concern is expected to be the
orders and executions history.

The design remains viable because the main operational queries use selective access
patterns:

- account history uses account ID and creation time;
- portfolio reads use the account-position key;
- account lookup uses the unique account reference;
- incremental extraction uses creation time;
- executions are reached through their order relationship.

The database should not repeatedly calculate dashboard data by scanning all historical
orders.

The analytical extract should also never become:

    SELECT * FROM orders

without a time boundary.

Instead, each run reads only the new extraction range.

At 100x volume, indexes become increasingly important and should be monitored using
query plans and database statistics.

If the orders/executions tables become large enough that index maintenance,
vacuuming, backup duration, or query latency becomes operationally significant,
partitioning can then be introduced through a later migration.

---

# 10. Partitioning Position

Partitioning is **not required at the current scale**.

The current design deliberately avoids partitioning because it adds operational
complexity:

- more complicated migrations
- partition management
- more complicated backup and restore considerations
- additional monitoring
- partition pruning requirements
- more complicated retention operations

The primary growth dimension is time, so if partitioning becomes necessary, the
natural future partition key would be the order/execution creation or execution
timestamp.

Time-based partitioning would allow old data to be managed as complete partitions
rather than individual rows.

However, introducing partitions before there is evidence that the existing indexed
tables cannot handle the workload would add complexity without a demonstrated
benefit.

The decision is therefore:

    Do not partition yet.

Revisit partitioning when measured production characteristics show that table size,
maintenance time, backup/restore requirements, or query performance justify it.

---

# 11. Archival and Retention Position

The system should distinguish between **operational retention** and **analytical
retention**.

The operational database should retain the trading records required for customer
support, order history, statements, reconciliation, and audit requirements.

Executed trade information should not be deleted merely because an order is old.

The Sprint 7 analytical store provides a separate destination for historical and
analytical workloads.

This prevents long-running analytical queries from unnecessarily competing with
the transactional database.

At the current stage, automatic deletion or archival from the operational database
is not required.

The retention period should ultimately be determined by the applicable business,
audit, and regulatory requirements rather than by database size alone.

Once an approved retention period exists, archival can be implemented as a controlled
process.

A future archival strategy could:

    1. Identify records older than the approved operational retention period.
    2. Verify that they have been successfully transferred to the durable archive.
    3. Record the archival batch and high-water mark.
    4. Remove eligible operational records only after successful verification.
    5. Preserve the data in the archive for the required retention period.

Until those requirements are defined, deleting historical trading records would be
premature.

---

# 12. Cost and Operational Trade-offs

Every additional retained column and index has a cost.

Execution retention increases:

- storage usage;
- backup size;
- replication traffic;
- index maintenance;
- vacuum/maintenance work.

The benefit is that the system retains an authoritative record of the actual trade
rather than reconstructing executions from order state later.

The incremental extraction index also has a write cost because every new order must
update the index.

That cost is accepted because the alternative is a progressively more expensive
full-history scan for every analytical extract.

The design therefore favors:

    small predictable write overhead
        +
    bounded incremental reads

over:

    slightly cheaper writes
        +
    increasingly expensive historical scans.

At 100x volume, operational complexity is expected to increase mainly around
maintenance, backups, monitoring, and extraction throughput rather than around the
business data model itself.

The design intentionally delays partitioning and automated archival until measured
workload or approved retention requirements justify them.

---

# 13. Final Design Decision

The design retains executed trades at **one row per execution**.

Executions are populated by the **trading/order execution component** when a trade
actually occurs.

The transactional database remains the source of truth for order and execution
records.

Sprint 7 extracts data incrementally using a timestamp-based high-water mark rather
than scanning the entire order history.

The order creation timestamp should have a dedicated index for this cross-account
incremental workload.

At 100x volume, the design continues to rely on indexed access and incremental
extraction. Partitioning is deliberately deferred until measured scale requires it.

Archival and deletion are also deferred until business and regulatory retention
requirements are explicitly defined.

This keeps the current design simple enough to operate while leaving clear upgrade
paths for:

- composite incremental cursors;
- time-based partitioning;
- archival;
- longer-term analytical retention;
- larger execution volumes.

The key principle is to pay modest, predictable costs during writes and extraction
rather than allowing historical growth to turn routine operational queries and
nightly extracts into full-table scans.