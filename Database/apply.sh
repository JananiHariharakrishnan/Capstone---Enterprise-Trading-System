#!/usr/bin/env bash

set -euo pipefail

# Find the sprint folder
SPRINT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MIGRATIONS_DIR="${SPRINT_DIR}/migrations"
ENV_FILE="${SPRINT_DIR}/.env"

# ------------------------------------------------------------
# Save TARGET_DATABASE if it was already provided
# ------------------------------------------------------------

TARGET_DATABASE_FROM_ENV="${TARGET_DATABASE:-}"

# ------------------------------------------------------------
# Load repository .env
# ------------------------------------------------------------

if [[ -f "${ENV_FILE}" ]]; then
    set -a
    source "${ENV_FILE}"
    set +a
fi

# ------------------------------------------------------------
# Determine target database
#
# TARGET_DATABASE takes priority.
# Otherwise use POSTGRES_DB from .env.
# ------------------------------------------------------------

TARGET_DATABASE="${TARGET_DATABASE_FROM_ENV:-${POSTGRES_DB:-}}"

if [[ -z "${TARGET_DATABASE}" ]]; then
    echo "ERROR: TARGET_DATABASE is not set and POSTGRES_DB was not found in .env." >&2
    exit 1
fi

# ------------------------------------------------------------
# PostgreSQL connection configuration
# ------------------------------------------------------------

export PGHOST="${PGHOST:-${POSTGRES_HOST:-localhost}}"
export PGPORT="${PGPORT:-${POSTGRES_PORT:-5432}}"
export PGUSER="${PGUSER:-${POSTGRES_USER:-postgres}}"

if [[ -z "${PGPASSWORD:-}" && -n "${POSTGRES_PASSWORD:-}" ]]; then
    export PGPASSWORD="${POSTGRES_PASSWORD}"
fi

# ------------------------------------------------------------
# Check migrations directory
# ------------------------------------------------------------

if [[ ! -d "${MIGRATIONS_DIR}" ]]; then
    echo "ERROR: migrations/ directory not found." >&2
    exit 1
fi

# ------------------------------------------------------------
# Apply all SQL files in filename order
#
# This includes both migrations and seed SQL files.
# ------------------------------------------------------------

echo "Applying migrations and seed data to database: ${TARGET_DATABASE}"

mapfile -d '' MIGRATIONS < <(
    find "${MIGRATIONS_DIR}" \
        -maxdepth 1 \
        -type f \
        -name '*.sql' \
        -print0 |
    LC_ALL=C sort -z
)

if [[ "${#MIGRATIONS[@]}" -eq 0 ]]; then
    echo "ERROR: No SQL files found in migrations/ directory." >&2
    exit 1
fi

for migration in "${MIGRATIONS[@]}"; do

    echo "Applying: $(basename "${migration}")"

    psql \
        -h "${PGHOST}" \
        -p "${PGPORT}" \
        -U "${PGUSER}" \
        -d "${TARGET_DATABASE}" \
        -v ON_ERROR_STOP=1 \
        --single-transaction \
        -f "${migration}"

done

echo "Database migration and seeding completed successfully."
