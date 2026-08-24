# Normalisation Notes

## 1. Objective

The purpose of this design is to translate the Enterprise Trading Platform ER model into a relational schema that satisfies **Third Normal Form (3NF)**.

Third Normal Form is mandatory for this design. The normalisation process was therefore performed to:

- Eliminate repeating groups and non-atomic attributes.
- Remove partial dependencies.
- Remove transitive dependencies.
- Preserve the relationships represented in the ER model.
- Maintain referential integrity between related entities.
- Avoid unnecessary duplication of business data.
- Clearly document any operational current-state data that could otherwise be derived from historical records.

The final relational design consists of:

- `instruments`
- `accounts`
- `users`
- `orders`
- `executions`
- `positions`
- `balance_history`
- `watchlist`

---

# 2. ER Model to Relational Model

The first step was to map each major ER entity to a relation.

| ER Entity | Relational Table | Primary Key |
|---|---|---|
| Instrument | `instruments` | `symbol` |
| Account | `accounts` | `id` |
| User | `users` | `account_id` |
| Order | `orders` | `id` |
| Execution | `executions` | `id` |
| Position | `positions` | `(account_id, symbol)` |
| Balance History | `balance_history` | `id` |
| Watchlist | `watchlist` | `(account_id, symbol)` |

The `instruments` relation stores instrument-level attributes including symbol, name, asset class, currency, tradability and current price. `symbol` is the primary key and is referenced by other relations.

The `accounts` relation represents trading accounts. In addition to the internal surrogate key `id`, the updated design introduces `account_reference` as a stable business/customer account reference. `account_reference` is declared `UNIQUE`, making it a candidate key while `id` remains the primary key used by foreign keys.

The `users` relation represents the holder associated with a trading account. `account_id` is both its primary key and a foreign key to `accounts.id`, enforcing the 1:1 relationship.

---

# 3. Mapping Relationships

## 3.1 Account – User

The ER model represents one user/holder record per trading account.

This is mapped as:

```text
accounts(id)
        |
        | 1 : 1
        |
users(account_id)
```

`users.account_id` is both:

- Primary Key of `users`
- Foreign Key referencing `accounts.id`

This prevents multiple user records from being associated with the same account.

---

## 3.2 Account – Order

An account can place multiple orders, while each order belongs to one account.

This 1:N relationship is represented as:

```text
accounts(id)
        |
        | 1 : N
        |
orders(account_id)
```

`orders.account_id` is therefore a foreign key referencing `accounts.id`.

---

## 3.3 Instrument – Order

An instrument can appear in multiple orders, while each order refers to one instrument.

```text
instruments(symbol)
        |
        | 1 : N
        |
orders(symbol)
```

`orders.symbol` references `instruments.symbol`.

---

## 3.4 Order – Execution

An order may have multiple executions/fills.

```text
orders(id)
    |
    | 1 : N
    |
executions(order_id)
```

`executions.order_id` references `orders.id`.

Each execution independently stores its actual quantity, execution price and execution time. This prevents multiple execution values from being stored as repeating attributes within an order.

---

## 3.5 Account – Instrument through Position

An account can hold multiple instruments and an instrument can be held by multiple accounts. Therefore, the underlying relationship is many-to-many.

The relationship is resolved through:

```text
positions(
    account_id,
    symbol,
    qty,
    avg_cost
)
```

The composite primary key is:

```text
(account_id, symbol)
```

This represents one net position for a particular account and instrument combination.

---

## 3.6 Account – Instrument through Watchlist

An account can watch multiple instruments, and an instrument can appear in multiple accounts' watchlists.

This many-to-many relationship is resolved through:

```text
watchlist(
    account_id,
    symbol,
    added_on
)
```

The composite primary key `(account_id, symbol)` prevents duplicate account/instrument entries.

---

## 3.7 Account – Balance History

An account can have many balance history records.

```text
accounts(id)
        |
        | 1 : N
        |
balance_history(account_id)
```

`balance_history.account_id` references `accounts.id`.

A balance history entry can optionally reference an order through `related_order_id`. The attribute is nullable because deposits and withdrawals do not necessarily originate from an order.

---

# 4. First Normal Form (1NF)

The first stage was to ensure that every relation satisfies **First Normal Form**.

The design satisfies 1NF because:

- Each column contains a single atomic value.
- There are no repeating groups.
- Each row represents one entity or relationship instance.
- Every relation has a defined primary key.
- Multiple executions are stored as separate rows.
- Multiple watchlist entries are stored as separate rows.
- Account information is not repeated inside orders or executions.

For example, instead of storing multiple executions inside an order:

```text
Order
--------------------------------
order_id
execution_1
execution_2
execution_3
```

the design uses:

```text
executions
--------------------------------
id
order_id
quantity
price
executed_at
```

This allows an arbitrary number of executions while keeping each execution record atomic.

Similarly, watchlist records are represented as individual rows.

---

# 5. Second Normal Form (2NF)

The next step was to eliminate **partial dependencies**.

Relations with single-column primary keys do not have partial dependency issues because their non-key attributes depend on the complete single-column key.

The composite-key relations requiring specific verification are:

- `positions`
- `watchlist`

---

## 5.1 Positions

The relation is:

```text
positions(
    account_id,
    symbol,
    qty,
    avg_cost
)
```

Primary Key:

```text
(account_id, symbol)
```

Functional dependency:

```text
(account_id, symbol) → qty, avg_cost
```

Both `qty` and `avg_cost` describe the position of a specific instrument within a specific account.

Neither attribute depends solely on `account_id` or solely on `symbol`.

Therefore, there is no partial dependency.

```text
positions ∈ 2NF
```

This is enforced by the composite primary key in the schema.

---

## 5.2 Watchlist

The relation is:

```text
watchlist(
    account_id,
    symbol,
    added_on
)
```

Primary Key:

```text
(account_id, symbol)
```

Functional dependency:

```text
(account_id, symbol) → added_on
```

The timestamp describes when that particular account added that particular instrument.

It does not depend only on the account or only on the instrument.

Therefore, there is no partial dependency.

```text
watchlist ∈ 2NF
```

---

# 6. Third Normal Form (3NF)

The final normalisation step was to verify that there are **no transitive dependencies**.

The general requirement is:

```text
Primary Key → Non-Key Attributes
```

and no non-key attribute should determine another non-key attribute.

---

## 6.1 Instruments

Functional dependency:

```text
symbol → name, asset_class, currency,
         tradable, current_price
```

All attributes describe the instrument identified by `symbol`.

There is no non-key attribute that determines another non-key attribute.

Therefore:

```text
instruments ∈ 3NF
```

---

## 6.2 Accounts

The updated `accounts` relation is:

```text
accounts(
    id,
    account_reference,
    cash_balance,
    buying_power,
    status,
    version,
    last_updated
)
```

Primary Key:

```text
id
```

Candidate Key:

```text
account_reference
```

because `account_reference` has a unique constraint.

The functional dependencies are:

```text
id → account_reference, cash_balance, buying_power,
     status, version, last_updated
```

and because `account_reference` uniquely identifies an account:

```text
account_reference → id, cash_balance, buying_power,
                    status, version, last_updated
```

`account_reference` is therefore an alternate/candidate key rather than a non-key attribute that introduces a transitive dependency.

There is no dependency such as:

```text
id → account_reference → some_non_key_attribute
```

where `account_reference` is a non-key determinant.

Therefore:

```text
accounts ∈ 3NF
```

The addition of `account_reference` does **not** violate 3NF because it is uniquely constrained and functions as a candidate key.

---

## 6.3 Users

Functional dependency:

```text
account_id → first_name, last_name,
             email, phone_no, password_hash
```

All non-key attributes describe the user associated with the account.

`email` is unique, but no additional attributes depend on email within this relation.

Therefore:

```text
users ∈ 3NF
```

The 1:1 relationship is enforced through `account_id` being both PK and FK.

---

## 6.4 Orders

Functional dependency:

```text
id → account_id, symbol, side,
     order_type, qty, price, status,
     idempotency_key, created_on
```

All attributes describe the order identified by `id`.

Account attributes remain in `accounts`, and instrument attributes remain in `instruments`.

Therefore, order-specific information is not unnecessarily duplicated.

```text
orders ∈ 3NF
```

The `idempotency_key` is also uniquely constrained to provide a database-level duplicate-order guarantee.

---

## 6.5 Executions

Functional dependency:

```text
id → order_id, quantity, price, executed_at
```

Each execution is identified by `id`.

Order information is not duplicated in the execution relation. Instead, the relationship is represented through `order_id`.

Therefore:

```text
executions ∈ 3NF
```

---

## 6.6 Positions

Functional dependency:

```text
(account_id, symbol) → qty, avg_cost
```

Both non-key attributes depend on the entire composite key.

No non-key attribute determines another non-key attribute.

Therefore:

```text
positions ∈ 3NF
```

---

## 6.7 Balance History

Functional dependency:

```text
id → account_id, type, amount, related_order_id
```

All attributes describe a single balance history event.

The account and order are represented using foreign keys rather than duplicated descriptive data.

Therefore:

```text
balance_history ∈ 3NF
```

The nullable `related_order_id` is intentional because not every balance movement originates from an order.

---

## 6.8 Watchlist

Functional dependency:

```text
(account_id, symbol) → added_on
```

`added_on` depends on the complete composite key.

There are no transitive dependencies.

Therefore:

```text
watchlist ∈ 3NF
```

---

# 7. Final 3NF Relational Design

The resulting normalised relational design is:

```text
INSTRUMENTS(
    symbol PK,
    name,
    asset_class,
    currency,
    tradable,
    current_price
)

ACCOUNTS(
    id PK,
    account_reference UNIQUE,
    cash_balance,
    buying_power,
    status,
    version,
    last_updated
)

USERS(
    account_id PK/FK → accounts.id,
    first_name,
    last_name,
    email UNIQUE,
    phone_no,
    password_hash
)

ORDERS(
    id PK,
    account_id FK → accounts.id,
    symbol FK → instruments.symbol,
    side,
    order_type,
    qty,
    price,
    status,
    idempotency_key UNIQUE,
    created_on
)

EXECUTIONS(
    id PK,
    order_id FK → orders.id,
    quantity,
    price,
    executed_at
)

POSITIONS(
    account_id PK/FK → accounts.id,
    symbol PK/FK → instruments.symbol,
    qty,
    avg_cost
)

BALANCE_HISTORY(
    id PK,
    account_id FK → accounts.id,
    type,
    amount,
    related_order_id FK → orders.id NULL
)

WATCHLIST(
    account_id PK/FK → accounts.id,
    symbol PK/FK → instruments.symbol,
    added_on
)
```

The updated implementation explicitly enforces the relevant primary keys, foreign keys, unique constraints and check constraints. 
---

# 8. Deliberate Denormalisation Review

Third Normal Form is mandatory for this design, so no arbitrary denormalisation has been introduced.

However, the schema contains several **operational current-state attributes** that could potentially be reconstructed from historical information:

- `accounts.cash_balance`
- `accounts.buying_power`
- `positions.qty`
- `positions.avg_cost`

## 8.1 Account Balances

`balance_history` records individual cash movements, while `accounts.cash_balance` stores the current available cash.

The historical balance could theoretically be reconstructed by aggregating balance movements. However, storing the current balance directly allows the trading system to perform account and order checks without recalculating the entire balance history.

Therefore:

```text
balance_history = historical/audit information
accounts.cash_balance = current operational state
```

The schema explicitly describes `cash_balance` as the current available cash and `buying_power` as the amount currently available for new orders.

These fields should be treated as **maintained current state**, with consistency enforced by the application's transaction logic.

---

## 8.2 Position State

Historical executions contain individual fills, while `positions` stores the current net quantity and average cost for each account/instrument pair.

Reconstructing a current portfolio position from all executions every time a portfolio query is performed would be unnecessarily expensive.

Therefore:

```text
executions = historical trade/fill events
positions = current portfolio state
```

This is an intentional operational design decision rather than arbitrary duplication. 
---

## 8.3 Denormalisation Decision

No additional descriptive data has been duplicated between entities.

In particular:

- Instrument name and asset class are not copied into `orders`.
- Account/customer details are not copied into `orders`.
- Order details are not copied into `executions`.
- Instrument details are not copied into `positions`.
- Account details are not copied into `balance_history`.

Relationships are represented using foreign keys.

Therefore, the design remains **3NF-compliant**, while explicitly documenting the operational current-state values that are maintained for performance and transactional purposes.

