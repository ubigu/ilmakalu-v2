#!/bin/bash
set -e

PGPASSWORD=${POSTGRES_PASSWORD} psql -v ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname "$ILMAKALU_DB" \
    -h localhost \
    -f /dump/emissiontest_stripped.sql

PGPASSWORD=${POSTGRES_PASSWORD} psql -v ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname "$ILMAKALU_DB" \
    -h localhost \
    -f /dump/alter-schema-rights.sql