erDiagram

    %% =========================================================
    %% ACCOUNTS
    %% =========================================================

    ACCOUNTS {
        BIGINT id PK
        VARCHAR account_reference UK
        NUMERIC cash_balance
        NUMERIC buying_power
        VARCHAR status
        INT version
        TIMESTAMP last_updated
    }

    %% =========================================================
    %% USERS
    %% =========================================================

    USERS {
        BIGINT account_id PK, FK
        VARCHAR first_name
        VARCHAR last_name
        VARCHAR email UK
        VARCHAR phone_no
        VARCHAR password_hash
    }

    %% =========================================================
    %% INSTRUMENTS
    %% =========================================================

    INSTRUMENTS {
        VARCHAR symbol PK
        VARCHAR name
        VARCHAR asset_class
        CHAR currency
        BOOLEAN tradable
        NUMERIC current_price
    }

    %% =========================================================
    %% ORDERS
    %% =========================================================

    ORDERS {
        UUID id PK
        BIGINT account_id FK
        VARCHAR symbol FK
        VARCHAR side
        VARCHAR order_type
        INT qty
        NUMERIC price
        VARCHAR status
        VARCHAR idempotency_key UK
        TIMESTAMP created_on
    }

    %% =========================================================
    %% EXECUTIONS
    %% =========================================================

    EXECUTIONS {
        BIGINT id PK
        UUID order_id FK
        INT quantity
        NUMERIC price
        TIMESTAMP executed_at
    }

    %% =========================================================
    %% POSITIONS
    %% =========================================================

    POSITIONS {
        BIGINT account_id PK, FK
        VARCHAR symbol PK, FK
        INT qty
        NUMERIC avg_cost
    }

    %% =========================================================
    %% BALANCE HISTORY
    %% =========================================================

    BALANCE_HISTORY {
        BIGINT id PK
        BIGINT account_id FK
        VARCHAR type
        NUMERIC amount
        UUID related_order_id FK
    }

    %% =========================================================
    %% WATCHLIST
    %% =========================================================

    WATCHLIST {
        BIGINT account_id PK, FK
        VARCHAR symbol PK, FK
        TIMESTAMP added_on
    }


    %% =========================================================
    %% RELATIONSHIPS
    %% =========================================================

    ACCOUNTS ||--|| USERS : "has"

    ACCOUNTS ||--o{ ORDERS : "places"
    INSTRUMENTS ||--o{ ORDERS : "for"

    ORDERS ||--o{ EXECUTIONS : "has"

    ACCOUNTS ||--o{ POSITIONS : "owns"
    INSTRUMENTS ||--o{ POSITIONS : "represents"

    ACCOUNTS ||--o{ BALANCE_HISTORY : "has"
    ORDERS o|--o{ BALANCE_HISTORY : "related to"

    ACCOUNTS ||--o{ WATCHLIST : "maintains"
    INSTRUMENTS ||--o{ WATCHLIST : "included in"