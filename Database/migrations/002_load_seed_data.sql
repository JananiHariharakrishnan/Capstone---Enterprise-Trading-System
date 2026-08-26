BEGIN;

-- =============================================================================
-- Enterprise Trading Platform
-- Migration 002: Seed reference data
-- PostgreSQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- INSTRUMENTS
-- -----------------------------------------------------------------------------

INSERT INTO instruments (
    symbol,
    name,
    asset_class,
    currency,
    tradable,
    current_price
) VALUES
    ('INFY.NS',      'Infosys Limited',                       'EQUITY',  'INR', TRUE,  1585.50),
    ('RELIANCE.NS',  'Reliance Industries Limited',           'EQUITY',  'INR', TRUE,  1425.00),
    ('TATASTEEL.BO', 'Tata Steel Limited',                   'EQUITY',  'INR', TRUE,   164.20),
    ('HDFCBANK.NS', 'HDFC Bank Limited',                     'EQUITY',  'INR', TRUE,  1672.00),
    ('AAPL',        'Apple Inc',                             'EQUITY',  'USD', TRUE,   232.50),
    ('SPY',         'SPDR S&P 500 ETF Trust',                'ETF',     'USD', TRUE,   548.00),
    ('FX:EURUSD',   'Euro against United States Dollar',     'FX',      'USD', TRUE,     1.17),
    ('X:BTC-USD',   'Bitcoin against United States Dollar',  'CRYPTO',  'USD', TRUE, 61000.00),
    ('SATYAM.BO',   'Satyam Computer Services Limited',     'EQUITY',  'INR', FALSE,   21.50);

-- -----------------------------------------------------------------------------
-- ACCOUNTS
-- account_reference is the stable business/customer reference.
-- -----------------------------------------------------------------------------

INSERT INTO accounts (
    account_reference,
    cash_balance,
    buying_power,
    status
) VALUES
    ('ETP-2201', 480000.00, 480000.00, 'ACTIVE'),
    ('ETP-2202', 1250000.00, 1250000.00, 'ACTIVE'),
    ('ETP-2203', 3200.00, 3200.00, 'ACTIVE'),
    ('ETP-2204', 95000.00, 95000.00, 'ACTIVE'),
    ('ETP-2205', 220000.00, 220000.00, 'SUSPENDED'),
    ('ETP-2206', 610000.00, 610000.00, 'CLOSED');

-- -----------------------------------------------------------------------------
-- USERS
-- account_id is resolved from account_reference.
-- -----------------------------------------------------------------------------

INSERT INTO users (
    account_id,
    first_name,
    last_name,
    email,
    phone_no,
    password_hash
)
SELECT
    a.id,
    v.first_name,
    v.last_name,
    v.email,
    v.phone_no,
    v.password_hash
FROM (
    VALUES
        ('ETP-2201', 'Ananya',  'Iyer',       'ananya.iyer@example.com',  '+91-9000000001', 'seed-password-hash-2201'),
        ('ETP-2202', 'Rohit',   'Deshpande', 'rohit.deshpande@example.com', '+91-9000000002', 'seed-password-hash-2202'),
        ('ETP-2203', 'Meera',   'Krishnan',  'meera.krishnan@example.com', '+91-9000000003', 'seed-password-hash-2203'),
        ('ETP-2204', 'Vikram',  'Nair',      'vikram.nair@example.com', '+91-9000000004', 'seed-password-hash-2204'),
        ('ETP-2205', 'Sana',    'Qureshi',   'sana.qureshi@example.com', '+91-9000000005', 'seed-password-hash-2205'),
        ('ETP-2206', 'Joseph',  'Mathew',    'joseph.mathew@example.com', '+91-9000000006', 'seed-password-hash-2206')
) AS v(
    account_reference,
    first_name,
    last_name,
    email,
    phone_no,
    password_hash
)
JOIN accounts a
    ON a.account_reference = v.account_reference;

-- -----------------------------------------------------------------------------
-- POSITIONS
-- -----------------------------------------------------------------------------

INSERT INTO positions (
    account_id,
    symbol,
    qty,
    avg_cost
)
SELECT
    a.id,
    v.symbol,
    v.qty,
    v.avg_cost
FROM (
    VALUES
        ('ETP-2201', 'SATYAM.BO',    100,  21.50),
        ('ETP-2201', 'INFY.NS',      300, 1585.50),
        ('ETP-2201', 'TATASTEEL.BO', 500,  164.20),
        ('ETP-2202', 'RELIANCE.NS',  250, 1425.00),
        ('ETP-2202', 'AAPL',          60,  232.50),
        ('ETP-2203', 'TATASTEEL.BO',  15,  163.00),
        ('ETP-2204', 'HDFCBANK.NS',   30, 1672.00)
) AS v(account_reference, symbol, qty, avg_cost)
JOIN accounts a
    ON a.account_reference = v.account_reference;

-- -----------------------------------------------------------------------------
-- ORDERS
-- UUIDs are deterministic seed values.
-- idempotency_key is unique by database constraint.
-- -----------------------------------------------------------------------------

INSERT INTO orders (
    id,
    account_id,
    symbol,
    side,
    order_type,
    qty,
    price,
    status,
    idempotency_key,
    created_on
)
SELECT
    v.order_id::UUID,
    a.id,
    v.symbol,
    v.side,
    v.order_type,
    v.qty,
    v.price,
    v.status,
    v.idempotency_key,
    v.created_on::TIMESTAMP
FROM (
    VALUES
        ('1f0c8c10-7a41-4c01-9001-000000000001', 'ETP-2201', 'SATYAM.BO',    'BUY',  'LIMIT', 100,  21.50,    'FILLED',    'seed-2201-001', '2026-05-14 10:31:06'),
        ('1f0c8c10-7a41-4c01-9001-000000000002', 'ETP-2201', 'INFY.NS',      'BUY',  'LIMIT', 200, 1580.50,   'FILLED',    'seed-2201-002', '2026-06-08 09:47:12'),
        ('1f0c8c10-7a41-4c01-9001-000000000003', 'ETP-2201', 'INFY.NS',      'BUY',  'LIMIT', 100, 1595.50,   'FILLED',    'seed-2201-003', '2026-06-19 11:03:45'),
        ('1f0c8c10-7a41-4c01-9001-000000000004', 'ETP-2201', 'TATASTEEL.BO', 'BUY',  'LIMIT', 500,  164.20,   'FILLED',    'seed-2201-004', '2026-06-25 10:15:08'),
        ('1f0c8c10-7a41-4c01-9001-000000000005', 'ETP-2201', 'HDFCBANK.NS',  'BUY',  'LIMIT', 40,  1650.00,   'REJECTED',  'seed-2201-005', '2026-07-02 14:22:31'),
        ('1f0c8c10-7a41-4c01-9001-000000000006', 'ETP-2201', 'TATASTEEL.BO', 'SELL', 'LIMIT', 100,  172.00,   'CANCELLED', 'seed-2201-006', '2026-07-14 15:40:57'),
        ('1f0c8c10-7a41-4c01-9001-000000000007', 'ETP-2201', 'RELIANCE.NS',  'BUY',  'LIMIT', 50,  1410.00,   'NEW',       'seed-2201-007', '2026-08-03 09:05:19'),

        ('1f0c8c10-7a41-4c01-9001-000000000008', 'ETP-2202', 'RELIANCE.NS',  'BUY',  'LIMIT', 400, 1425.00,   'FILLED',    'seed-2202-001', '2026-06-11 09:31:04'),
        ('1f0c8c10-7a41-4c01-9001-000000000009', 'ETP-2202', 'AAPL',          'BUY',  'LIMIT', 60,  232.50,   'FILLED',    'seed-2202-002', '2026-06-30 13:52:26'),
        ('1f0c8c10-7a41-4c01-9001-000000000010', 'ETP-2202', 'RELIANCE.NS',  'SELL', 'LIMIT', 150, 1468.00,   'FILLED',    'seed-2202-003', '2026-07-09 10:28:33'),
        ('1f0c8c10-7a41-4c01-9001-000000000011', 'ETP-2202', 'X:BTC-USD',    'BUY',  'LIMIT', 1,  61000.00,   'REJECTED',  'seed-2202-004', '2026-07-21 16:11:02'),
        ('1f0c8c10-7a41-4c01-9001-000000000012', 'ETP-2202', 'SPY',           'BUY',  'LIMIT', 25,  548.00,    'NEW',       'seed-2202-005', '2026-08-04 08:12:47'),

        ('1f0c8c10-7a41-4c01-9001-000000000013', 'ETP-2203', 'TATASTEEL.BO', 'BUY',  'LIMIT', 15,  163.00,    'FILLED',    'seed-2203-001', '2026-06-17 12:05:41'),
        ('1f0c8c10-7a41-4c01-9001-000000000014', 'ETP-2203', 'INFY.NS',      'BUY',  'LIMIT', 10, 1585.00,    'REJECTED',  'seed-2203-002', '2026-07-06 09:58:15'),
        ('1f0c8c10-7a41-4c01-9001-000000000015', 'ETP-2203', 'TATASTEEL.BO', 'BUY',  'LIMIT', 20,  160.00,    'NEW',       'seed-2203-003', '2026-08-05 10:44:29'),

        ('1f0c8c10-7a41-4c01-9001-000000000016', 'ETP-2204', 'HDFCBANK.NS',  'BUY',  'LIMIT', 30, 1672.00,    'FILLED',    'seed-2204-001', '2026-06-23 11:19:53'),
        ('1f0c8c10-7a41-4c01-9001-000000000017', 'ETP-2204', 'SPY',           'BUY',  'LIMIT', 10,  552.00,    'CANCELLED', 'seed-2204-002', '2026-07-28 14:03:38'),
        ('1f0c8c10-7a41-4c01-9001-000000000018', 'ETP-2204', 'AAPL',          'BUY',  'LIMIT', 20,  230.00,    'NEW',       'seed-2204-003', '2026-08-06 09:22:10')
) AS v(
    order_id,
    account_reference,
    symbol,
    side,
    order_type,
    qty,
    price,
    status,
    idempotency_key,
    created_on
)
JOIN accounts a
    ON a.account_reference = v.account_reference;

-- -----------------------------------------------------------------------------
-- EXECUTIONS
-- Only FILLED orders receive executions.
-- -----------------------------------------------------------------------------

INSERT INTO executions (
    order_id,
    quantity,
    price,
    executed_at
)
SELECT
    o.id,
    v.quantity,
    v.price,
    v.executed_at::TIMESTAMP
FROM (
    VALUES
        ('1f0c8c10-7a41-4c01-9001-000000000001', 100,  21.50,  '2026-05-14 10:31:20'),
        ('1f0c8c10-7a41-4c01-9001-000000000002', 200, 1580.50, '2026-06-08 09:47:30'),
        ('1f0c8c10-7a41-4c01-9001-000000000003', 100, 1595.50, '2026-06-19 11:04:01'),
        ('1f0c8c10-7a41-4c01-9001-000000000004', 500,  164.20, '2026-06-25 10:15:22'),
        ('1f0c8c10-7a41-4c01-9001-000000000008', 400, 1425.00, '2026-06-11 09:31:25'),
        ('1f0c8c10-7a41-4c01-9001-000000000009', 60,   232.50, '2026-06-30 13:52:45'),
        ('1f0c8c10-7a41-4c01-9001-000000000010', 150, 1468.00, '2026-07-09 10:28:50'),
        ('1f0c8c10-7a41-4c01-9001-000000000013', 15,   163.00, '2026-06-17 12:06:02'),
        ('1f0c8c10-7a41-4c01-9001-000000000016', 30,  1672.00, '2026-06-23 11:20:10')
) AS v(order_id, quantity, price, executed_at)
JOIN orders o
    ON o.id = v.order_id::UUID;

COMMIT;