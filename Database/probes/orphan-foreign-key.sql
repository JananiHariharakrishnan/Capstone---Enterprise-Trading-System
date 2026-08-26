-- Probe: an order must not reference an account that does not exist.
--
-- The account_id below is deliberately chosen to be absent from the seeded
-- accounts table.
--
-- Expected result:
--   SQLSTATE 23503 (foreign key violation)

INSERT INTO orders (
    id,
    account_id,
    symbol,
    side,
    order_type,
    qty,
    price,
    status,
    idempotency_key
)
VALUES (
    'cccccccc-cccc-cccc-cccc-cccccccccccc',
    999999999,
    'INFY.NS',
    'BUY',
    'LIMIT',
    10,
    1500.00,
    'NEW',
    'probe-orphan-account-001'
);