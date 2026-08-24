-- Probe: duplicate idempotency key must be rejected.
--
-- The first INSERT is valid.
-- The second INSERT uses a different order ID and different order details,
-- but deliberately repeats the same idempotency_key.
--
-- Expected result:
--   First INSERT  -> succeeds
--   Second INSERT -> SQLSTATE 23505 (unique violation)

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
SELECT
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    a.id,
    'INFY.NS',
    'BUY',
    'LIMIT',
    10,
    1500.00,
    'NEW',
    'probe-idempotency-001'
FROM accounts a
WHERE a.account_reference = 'ETP-2201';


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
SELECT
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    a.id,
    'INFY.NS',
    'BUY',
    'LIMIT',
    20,
    1510.00,
    'NEW',
    'probe-idempotency-001'
FROM accounts a
WHERE a.account_reference = 'ETP-2201';