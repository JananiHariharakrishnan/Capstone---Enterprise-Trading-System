#!/usr/bin/env bash

#
# Sprint 3 acceptance harness - LOCAL POSTGRESQL VERSION
#
# This version does NOT use Docker.
#
# Usage:
#
#   bash scripts/check.sh
#
#   bash scripts/check.sh --keep
#
# PostgreSQL connection can be configured with:
#
#   PGHOST=localhost
#   PGPORT=5432
#   PGUSER=postgres
#   PGDATABASE=trading
#
# Example:
#
#   PGUSER=postgres PGDATABASE=trading bash scripts/check.sh
#

set -euo pipefail


# ============================================================================
# PATHS
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPRINT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${SPRINT_DIR}/.." && pwd)"

MIGRATIONS_DIR="${SPRINT_DIR}/migrations"
SEED_DIR="${SPRINT_DIR}/seed"
DESIGN_DIR="${SPRINT_DIR}/design"
PROBE_DIR="${SPRINT_DIR}/probes"
MANIFEST="${SPRINT_DIR}/manifest.env"
HISTORY_DESIGN="${SPRINT_DIR}/DESIGN.md"


# ============================================================================
# OPTIONS
# ============================================================================

KEEP_SCRATCH=0

while [ "$#" -gt 0 ]; do

    case "$1" in

        --keep)
            KEEP_SCRATCH=1
            shift
            ;;

        -h|--help)
            sed -n '2,25p' "${BASH_SOURCE[0]}" |
                sed 's/^#\{1,2\} \{0,1\}//'
            exit 0
            ;;

        *)
            printf 'Unknown option: %s\n' "$1" >&2
            exit 2
            ;;

    esac

done


# ============================================================================
# RESULT COUNTERS
# ============================================================================

PASSED=0
FAILED=0


section() {
    printf '\n%s\n' "$1"
}


pass() {
    printf '  PASS  %s\n' "$1"
    PASSED=$((PASSED + 1))
}


fail() {

    printf '  FAIL  %s\n' "$1"

    shift

    while [ "$#" -gt 0 ]; do
        printf '        %s\n' "$1"
        shift
    done

    FAILED=$((FAILED + 1))
}


abort() {

    printf '\nSTOPPED: %s\n' "$1" >&2

    shift

    while [ "$#" -gt 0 ]; do
        printf '  %s\n' "$1" >&2
        shift
    done

    printf '\nNothing else could be checked until that is fixed.\n' >&2

    exit 1
}


# ============================================================================
# POSTGRESQL CONFIGURATION
# ============================================================================

read_env() {

    key="$1"
    fallback="$2"
    value=""

    if [ -f "${REPO_ROOT}/.env" ]; then

        value="$(
            sed -n "s/^[[:space:]]*${key}=//p" \
                "${REPO_ROOT}/.env" |
            tail -n 1 |
            tr -d '\r'
        )"

        value="${value%\"}"
        value="${value#\"}"

        value="${value%\'}"
        value="${value#\'}"

    fi

    if [ -z "${value}" ]; then
        value="${fallback}"
    fi

    printf '%s' "${value}"
}


PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-$(read_env POSTGRES_USER postgres)}"
WORKING_DB="${PGDATABASE:-$(read_env POSTGRES_DB trading)}"

CHECK_DB="${CHECK_DATABASE:-${WORKING_DB}_check}"


printf 'Sprint 3 acceptance harness\n'
printf 'PostgreSQL: %s:%s\n' "${PGHOST}" "${PGPORT}"
printf 'User: %s\n' "${PGUSER}"
printf 'Working database: %s\n' "${WORKING_DB}"
printf 'Scratch database: %s\n' "${CHECK_DB}"


# ============================================================================
# LOCAL POSTGRESQL COMMANDS
# ============================================================================

psql_cmd() {

    psql \
        -h "${PGHOST}" \
        -p "${PGPORT}" \
        -U "${PGUSER}" \
        "$@"
}


scalar() {

    psql_cmd \
        -X \
        -A \
        -t \
        -q \
        -v ON_ERROR_STOP=1 \
        -d "${CHECK_DB}" \
        -c "$1" \
        2>/dev/null |
        tr -d '\r' |
        head -n 1 ||
        true
}


drop_scratch() {

    printf \
        'DROP DATABASE IF EXISTS "%s" WITH (FORCE);\n' \
        "${CHECK_DB}" |
    psql_cmd \
        -X \
        -q \
        -v ON_ERROR_STOP=1 \
        -d postgres \
        >/dev/null 2>&1 ||
        true
}


create_scratch() {

    printf \
        'DROP DATABASE IF EXISTS "%s" WITH (FORCE);\nCREATE DATABASE "%s";\n' \
        "${CHECK_DB}" \
        "${CHECK_DB}" |
    psql_cmd \
        -X \
        -q \
        -v ON_ERROR_STOP=1 \
        -d postgres \
        >/dev/null 2>&1
}


# ============================================================================
# CSV HELPERS
# ============================================================================

csv_rows() {

    file="$1"

    [ -f "${file}" ] || {
        printf '0'
        return
    }

    lines="$(grep -c . "${file}" || true)"
    lines="${lines:-0}"

    if [ "${lines}" -gt 0 ]; then
        printf '%s' "$((lines - 1))"
    else
        printf '0'
    fi
}


# ============================================================================
# MANIFEST
# ============================================================================

section 'Manifest'


[ -f "${MANIFEST}" ] || abort \
    "No manifest.env in ${SPRINT_DIR}." \
    "Create ${MANIFEST} before running the harness."


SCHEMA_NAME=""
APPLY_COMMAND=""

ACCOUNTS_TABLE=""
ACCOUNTS_STATUS_COLUMN=""

ACCOUNTS_STATUS_ACTIVE=""
ACCOUNTS_STATUS_SUSPENDED=""
ACCOUNTS_STATUS_CLOSED=""

ORDERS_TABLE=""
ORDERS_IDEMPOTENCY_COLUMN=""


# shellcheck source=/dev/null
. "${MANIFEST}"


SCHEMA_NAME="${SCHEMA_NAME:-public}"


MANIFEST_KEYS="
SCHEMA_NAME
APPLY_COMMAND
ACCOUNTS_TABLE
ACCOUNTS_STATUS_COLUMN
ACCOUNTS_STATUS_ACTIVE
ACCOUNTS_STATUS_SUSPENDED
ACCOUNTS_STATUS_CLOSED
ORDERS_TABLE
ORDERS_IDEMPOTENCY_COLUMN
"


OUTSTANDING=""

for key in ${MANIFEST_KEYS}; do

    eval "value=\${${key}}"

    if [ -z "${value}" ] || [ "${value}" = "CHANGE_ME" ]; then
        OUTSTANDING="${OUTSTANDING} ${key}"
    fi

done


if [ -n "${OUTSTANDING}" ]; then

    abort \
        "manifest.env is not completely filled in." \
        "Missing or CHANGE_ME values:${OUTSTANDING}"

fi


valid_identifier() {

    case "$1" in

        '')
            return 1
            ;;

        *[!A-Za-z0-9_]*)
            return 1
            ;;

        [0-9]*)
            return 1
            ;;

    esac

    return 0
}


for key in \
    SCHEMA_NAME \
    ACCOUNTS_TABLE \
    ACCOUNTS_STATUS_COLUMN \
    ORDERS_TABLE \
    ORDERS_IDEMPOTENCY_COLUMN
do

    eval "value=\${${key}}"

    valid_identifier "${value}" ||
        abort \
            "${key} is not a valid plain identifier: ${value}" \
            "Use letters, digits and underscores only."

done


for key in \
    ACCOUNTS_STATUS_ACTIVE \
    ACCOUNTS_STATUS_SUSPENDED \
    ACCOUNTS_STATUS_CLOSED
do

    eval "value=\${${key}}"

    case "${value}" in

        *[\'\\]*)
            abort \
                "${key} contains a quote or backslash: ${value}"
            ;;

    esac

done


pass "manifest.env declares every name the harness needs"


# ============================================================================
# LOCAL POSTGRESQL AVAILABILITY
# ============================================================================

section 'PostgreSQL'


command -v psql >/dev/null 2>&1 || abort \
    "psql is not installed or is not on PATH." \
    "Install PostgreSQL client tools."


command -v pg_isready >/dev/null 2>&1 || abort \
    "pg_isready is not installed or is not on PATH."


if ! pg_isready \
        -h "${PGHOST}" \
        -p "${PGPORT}" \
        -U "${PGUSER}" \
        >/dev/null 2>&1
then

    abort \
        "Cannot connect to local PostgreSQL." \
        "Start PostgreSQL and try again." \
        "Test with:" \
        "  pg_isready -h ${PGHOST} -p ${PGPORT} -U ${PGUSER}"

fi


pass "local PostgreSQL is accepting connections"


# ============================================================================
# DELIVERABLES ON DISK
# ============================================================================

section 'Deliverables on disk'


list_sql() {

    dir="$1"

    [ -d "${dir}" ] || return 0

    find "${dir}" \
        -maxdepth 1 \
        -type f \
        -name '*.sql' \
        -print |
        LC_ALL=C sort
}


MIGRATIONS=()

while IFS= read -r file; do

    [ -n "${file}" ] || continue

    MIGRATIONS[${#MIGRATIONS[@]}]="${file}"

done < <(list_sql "${MIGRATIONS_DIR}")


if [ "${#MIGRATIONS[@]}" -eq 0 ]; then

    abort \
        "No migration files in migrations/." \
        "Create migrations/001_create_trading_schema.sql."

fi


pass "migrations/ holds ${#MIGRATIONS[@]} SQL file(s)"


BADLY_NAMED=""

for file in "${MIGRATIONS[@]}"; do

    name="$(basename "${file}")"

    case "${name}" in

        [0-9][0-9][0-9]_*.sql)
            ;;

        *)
            BADLY_NAMED="${BADLY_NAMED} ${name}"
            ;;

    esac

done


if [ -n "${BADLY_NAMED}" ]; then

    fail \
        "Migration files that do not follow NNN_description.sql:${BADLY_NAMED}"

else

    pass "every migration is named NNN_description.sql"

fi


# ============================================================================
# SEED FILES
# ============================================================================

MISSING_SEED=""

SEED_FILES="
customer-accounts.csv
instrument-reference.csv
order-history.csv
current-holdings.csv
"


for name in ${SEED_FILES}; do

    [ -s "${SEED_DIR}/${name}" ] ||
        MISSING_SEED="${MISSING_SEED} ${name}"

done


if [ -n "${MISSING_SEED}" ]; then

    abort \
        "Provided seed files missing or empty:${MISSING_SEED}" \
        "Restore the four files in seed/."

fi


pass "seed/ holds the four provided data files"


# ============================================================================
# DESIGN FILES
# ============================================================================

DIAGRAM=""

for candidate in "${DESIGN_DIR}"/er-diagram.*; do

    if [ -f "${candidate}" ]; then
        DIAGRAM="${candidate}"
        break
    fi

done


if [ -n "${DIAGRAM}" ]; then

    pass \
        "ER diagram committed at design/$(basename "${DIAGRAM}")"

else

    fail \
        "No ER diagram in design/." \
        "Create design/er-diagram.md."

fi


if [ -s "${DESIGN_DIR}/indexes.md" ]; then

    pass "index justifications committed at design/indexes.md"

else

    fail \
        "No design/indexes.md, or the file is empty."

fi


if [ -s "${HISTORY_DESIGN}" ]; then

    pass "historical trade data design committed at DESIGN.md"

else

    fail \
        "No DESIGN.md, or the file is empty."

fi


# ============================================================================
# PROBES
# ============================================================================

probe_is_written() {

    [ -f "$1" ] || return 1

    body="$(
        sed -e 's/--.*$//' "$1" |
        tr -d '[:space:]'
    )"

    [ -n "${body}" ]
}


for probe in \
    duplicate-idempotency-key \
    orphan-foreign-key
do

    if probe_is_written "${PROBE_DIR}/${probe}.sql"; then

        pass "probes/${probe}.sql has SQL in it"

    else

        fail \
            "probes/${probe}.sql contains no executable SQL."

    fi

done


# ============================================================================
# CREATE SCRATCH DATABASE
# ============================================================================

section "Applying your schema to ${CHECK_DB}"


create_scratch ||
    abort \
        "Could not create scratch database ${CHECK_DB}." \
        "Make sure ${PGUSER} has CREATEDB permission."


APPLY_LOG="$(mktemp)"

trap 'rm -f "${APPLY_LOG}"' EXIT


# ============================================================================
# APPLY MIGRATIONS
# ============================================================================

if (
    cd "${SPRINT_DIR}"

    TARGET_DATABASE="${CHECK_DB}" \
    PGHOST="${PGHOST}" \
    PGPORT="${PGPORT}" \
    PGUSER="${PGUSER}" \
    bash -c "${APPLY_COMMAND}"

) >"${APPLY_LOG}" 2>&1
then

    pass \
        "your apply command takes an empty database to migrated schema"

else

    printf '\n'

    sed 's/^/  | /' "${APPLY_LOG}"

    abort \
        "The apply command failed against an empty database." \
        "Command:" \
        "${APPLY_COMMAND}"

fi


# ============================================================================
# VERIFY SCHEMA WAS CREATED
# ============================================================================

TABLE_COUNT="$(
    scalar "
        SELECT count(*)
        FROM pg_tables
        WHERE schemaname = '${SCHEMA_NAME}'
    "
)"


if [ "${TABLE_COUNT:-0}" -eq 0 ]; then

    abort \
        "Your apply command created no tables." \
        "Check migrations/001_create_trading_schema.sql."

fi


pass \
    "${TABLE_COUNT} table(s) exist in schema ${SCHEMA_NAME}"


# ============================================================================
# RELATION HELPERS
# ============================================================================

resolve_relation() {

    scalar "
        SELECT c.relname
        FROM pg_class c
        WHERE c.oid =
            to_regclass('${SCHEMA_NAME}.$1')
    "
}


ACCOUNTS_REL="$(resolve_relation "${ACCOUNTS_TABLE}")"
ORDERS_REL="$(resolve_relation "${ORDERS_TABLE}")"


if [ -z "${ACCOUNTS_REL}" ] ||
   [ -z "${ORDERS_REL}" ]
then

    MISSING=""

    [ -n "${ACCOUNTS_REL}" ] ||
        MISSING="${MISSING} ${SCHEMA_NAME}.${ACCOUNTS_TABLE}"

    [ -n "${ORDERS_REL}" ] ||
        MISSING="${MISSING} ${SCHEMA_NAME}.${ORDERS_TABLE}"


    EXISTING="$(
        scalar "
            SELECT string_agg(
                tablename,
                ', '
                ORDER BY tablename
            )
            FROM pg_tables
            WHERE schemaname = '${SCHEMA_NAME}'
        "
    )"


    abort \
        "Tables named in manifest.env do not exist:${MISSING}" \
        "Existing tables: ${EXISTING:-none}"

fi


pass "the tables named in manifest.env exist"


# ============================================================================
# COLUMN CHECKS
# ============================================================================

column_exists() {

    scalar "
        SELECT 1
        FROM pg_attribute a
        WHERE a.attrelid =
            to_regclass('${SCHEMA_NAME}.$1')
        AND a.attname = '$2'
        AND a.attnum > 0
        AND NOT a.attisdropped
    "
}


for pair in \
    "${ACCOUNTS_TABLE}:${ACCOUNTS_STATUS_COLUMN}" \
    "${ORDERS_TABLE}:${ORDERS_IDEMPOTENCY_COLUMN}"
do

    table="${pair%%:*}"
    column="${pair##*:}"


    if [ "$(column_exists "${table}" "${column}")" = "1" ]; then

        pass "${table}.${column} exists"

    else

        columns="$(
            scalar "
                SELECT string_agg(
                    a.attname,
                    ', '
                    ORDER BY a.attnum
                )
                FROM pg_attribute a
                WHERE a.attrelid =
                    to_regclass('${SCHEMA_NAME}.${table}')
                AND a.attnum > 0
                AND NOT a.attisdropped
            "
        )"


        fail \
            "${table} has no column named ${column}." \
            "Columns: ${columns:-none}"

    fi

done


# ============================================================================
# IDEMPOTENCY UNIQUE CONSTRAINT
# ============================================================================

UNIQUE_ON_KEY="$(
    scalar "
        SELECT string_agg(
            ci.relname,
            ', '
        )
        FROM pg_index i
        JOIN pg_class ci
            ON ci.oid = i.indexrelid
        WHERE i.indrelid =
            to_regclass(
                '${SCHEMA_NAME}.${ORDERS_TABLE}'
            )
        AND i.indisunique
        AND EXISTS (
            SELECT 1
            FROM pg_attribute a
            WHERE a.attrelid = i.indrelid
            AND a.attnum = ANY(
                string_to_array(
                    i.indkey::text,
                    ' '
                )::smallint[]
            )
            AND a.attname =
                '${ORDERS_IDEMPOTENCY_COLUMN}'
        )
    "
)"


if [ -n "${UNIQUE_ON_KEY}" ]; then

    pass \
        "a unique constraint/index covers ${ORDERS_TABLE}.${ORDERS_IDEMPOTENCY_COLUMN} (${UNIQUE_ON_KEY})"

else

    fail \
        "Nothing enforces uniqueness on ${ORDERS_TABLE}.${ORDERS_IDEMPOTENCY_COLUMN}." \
        "Add UNIQUE (account_id, idempotency_key)."

fi


# ============================================================================
# FOREIGN KEYS
# ============================================================================

FK_COUNT="$(
    scalar "
        SELECT count(*)
        FROM pg_constraint c
        JOIN pg_namespace n
            ON n.oid = c.connamespace
        WHERE c.contype = 'f'
        AND n.nspname = '${SCHEMA_NAME}'
    "
)"

FK_COUNT="${FK_COUNT:-0}"


if [ "${FK_COUNT}" -ge 2 ]; then

    pass \
        "${FK_COUNT} foreign key constraint(s) declared"

else

    fail \
        "Only ${FK_COUNT} foreign key constraint(s) declared." \
        "Orders must reference accounts and instruments."

fi


# ============================================================================
# CHECK CONSTRAINTS
# ============================================================================

CHECK_COUNT="$(
    scalar "
        SELECT count(*)
        FROM pg_constraint c
        JOIN pg_namespace n
            ON n.oid = c.connamespace
        WHERE c.contype = 'c'
        AND n.nspname = '${SCHEMA_NAME}'
    "
)"

CHECK_COUNT="${CHECK_COUNT:-0}"


if [ "${CHECK_COUNT}" -ge 3 ]; then

    pass \
        "${CHECK_COUNT} check constraint(s) declared"

else

    fail \
        "Only ${CHECK_COUNT} check constraint(s) declared." \
        "Expected at least three."

fi


# ============================================================================
# ACCOUNT STATUS CHECK
# ============================================================================

STATUS_CHECK="$(
    scalar "
        SELECT count(*)
        FROM pg_constraint c
        WHERE c.contype = 'c'
        AND c.conrelid =
            to_regclass(
                '${SCHEMA_NAME}.${ACCOUNTS_TABLE}'
            )
        AND pg_get_constraintdef(c.oid)
            ~* '\\m${ACCOUNTS_STATUS_COLUMN}\\M'
    "
)"


if [ "${STATUS_CHECK:-0}" -ge 1 ]; then

    pass \
        "a check constraint restricts ${ACCOUNTS_TABLE}.${ACCOUNTS_STATUS_COLUMN}"

else

    fail \
        "No check constraint covers ${ACCOUNTS_TABLE}.${ACCOUNTS_STATUS_COLUMN}." \
        "The harness requires ACTIVE, SUSPENDED and CLOSED to be constrained."

fi


# ============================================================================
# INDEXES
# ============================================================================

INDEX_LIST="$(
    scalar "
        SELECT string_agg(
            ci.relname,
            ', '
            ORDER BY ci.relname
        )
        FROM pg_index i
        JOIN pg_class ci
            ON ci.oid = i.indexrelid
        JOIN pg_class t
            ON t.oid = i.indrelid
        JOIN pg_namespace n
            ON n.oid = t.relnamespace
        WHERE n.nspname = '${SCHEMA_NAME}'
        AND NOT i.indisprimary
        AND NOT EXISTS (
            SELECT 1
            FROM pg_constraint k
            WHERE k.conindid = i.indexrelid
        )
    "
)"


INDEX_COUNT=0


if [ -n "${INDEX_LIST}" ]; then

    INDEX_COUNT="$(
        printf '%s' "${INDEX_LIST}" |
        tr ',' '\n' |
        grep -c . ||
        true
    )"

fi


if [ "${INDEX_COUNT}" -ge 3 ]; then

    pass \
        "${INDEX_COUNT} deliberate index(es): ${INDEX_LIST}"

else

    fail \
        "Only ${INDEX_COUNT} deliberate index(es)." \
        "At least three are required." \
        "Found: ${INDEX_LIST:-none}"

fi


# ============================================================================
# SEED DATA
# ============================================================================

section 'Seed data'


MISSING_STATES=""


for state in \
    "${ACCOUNTS_STATUS_ACTIVE}" \
    "${ACCOUNTS_STATUS_SUSPENDED}" \
    "${ACCOUNTS_STATUS_CLOSED}"
do

    count="$(
        scalar "
            SELECT count(*)
            FROM \"${SCHEMA_NAME}\".\"${ACCOUNTS_REL}\"
            WHERE \"${ACCOUNTS_STATUS_COLUMN}\"::text =
                '${state}'
        "
    )"


    if [ "${count:-0}" -ge 1 ]; then

        pass \
            "${count} loaded account(s) in state ${state}"

    else

        MISSING_STATES="${MISSING_STATES} ${state}"

    fi

done


if [ -n "${MISSING_STATES}" ]; then

    present="$(
        scalar "
            SELECT string_agg(
                DISTINCT
                \"${ACCOUNTS_STATUS_COLUMN}\"::text,
                ', '
            )
            FROM \"${SCHEMA_NAME}\".\"${ACCOUNTS_REL}\"
        "
    )"


    fail \
        "No account in state(s):${MISSING_STATES}" \
        "States present: ${present:-none}"

fi


EXPECTED_ACCOUNTS="$(
    csv_rows \
        "${SEED_DIR}/customer-accounts.csv"
)"


ACCOUNT_COUNT="$(
    scalar "
        SELECT count(*)
        FROM \"${SCHEMA_NAME}\".\"${ACCOUNTS_REL}\"
    "
)"


ACCOUNT_COUNT="${ACCOUNT_COUNT:-0}"


if [ "${ACCOUNT_COUNT}" -ge "${EXPECTED_ACCOUNTS}" ]; then

    pass \
        "${ACCOUNT_COUNT} account(s) loaded, expected at least ${EXPECTED_ACCOUNTS}"

else

    fail \
        "Only ${ACCOUNT_COUNT} account(s) loaded." \
        "Expected at least ${EXPECTED_ACCOUNTS}."

fi


EXPECTED_ORDERS="$(
    csv_rows \
        "${SEED_DIR}/order-history.csv"
)"


ORDER_COUNT="$(
    scalar "
        SELECT count(*)
        FROM \"${SCHEMA_NAME}\".\"${ORDERS_REL}\"
    "
)"


ORDER_COUNT="${ORDER_COUNT:-0}"


if [ "${ORDER_COUNT}" -ge "${EXPECTED_ORDERS}" ]; then

    pass \
        "${ORDER_COUNT} order(s) loaded, expected at least ${EXPECTED_ORDERS}"

else

    fail \
        "Only ${ORDER_COUNT} order(s) loaded." \
        "Expected at least ${EXPECTED_ORDERS}."

fi


# ============================================================================
# PROBE EXECUTION
# ============================================================================

section 'Constraints under load'


run_probe() {

    probe_file="$1"
    expected="$2"
    label="$3"


    if ! probe_is_written "${probe_file}"; then

        printf \
            '  SKIP  %s: probe contains no SQL.\n' \
            "${label}"

        return

    fi


    output="$(
        {
            printf '\\set VERBOSITY verbose\n'
            printf 'BEGIN;\n'
            cat "${probe_file}"
            printf '\nROLLBACK;\n'
        } |
        psql_cmd \
            -X \
            -q \
            -v ON_ERROR_STOP=1 \
            -d "${CHECK_DB}" \
            2>&1
    )" && status=0 || status=$?


    if [ "${status}" -eq 0 ]; then

        fail \
            "${label}: database accepted the statement." \
            "Expected SQLSTATE ${expected}."

        return

    fi


    actual="$(
        printf '%s\n' "${output}" |
        sed -n \
            's/.*ERROR:[[:space:]]*\([0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z]\):.*/\1/p' |
        head -n 1
    )"


    if [ "${actual}" = "${expected}" ]; then

        pass \
            "${label}: rejected with SQLSTATE ${expected}"

    else

        fail \
            "${label}: expected SQLSTATE ${expected}, got ${actual:-no SQLSTATE}." \
            "Postgres said:" \
            "$(printf '%s\n' "${output}" |
                grep -m 1 'ERROR:' ||
                printf '%s' 'no ERROR line')"

    fi
}


run_probe \
    "${PROBE_DIR}/duplicate-idempotency-key.sql" \
    23505 \
    "Duplicate idempotency key"


run_probe \
    "${PROBE_DIR}/orphan-foreign-key.sql" \
    23503 \
    "Orphan foreign key"


# ============================================================================
# RESULT
# ============================================================================

printf '\n%s\n' \
    '----------------------------------------------------------------'


printf '%s passed, %s failed\n' \
    "${PASSED}" \
    "${FAILED}"


if [ "${FAILED}" -eq 0 ]; then

    if [ "${KEEP_SCRATCH}" -eq 1 ]; then

        printf \
            'Scratch database %s kept.\n' \
            "${CHECK_DB}"

    else

        drop_scratch

        printf \
            'Scratch database %s dropped.\n' \
            "${CHECK_DB}"

    fi


    printf '\n'
    printf '%s\n' \
        'The Sprint 3 acceptance harness is satisfied.'


    exit 0

fi


printf '\n'
printf \
    'Scratch database %s left in place for inspection.\n' \
    "${CHECK_DB}"


printf \
    'Connect with:\n  psql -h %s -p %s -U %s -d %s\n' \
    "${PGHOST}" \
    "${PGPORT}" \
    "${PGUSER}" \
    "${CHECK_DB}"


exit 1