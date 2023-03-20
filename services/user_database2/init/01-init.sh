#!/bin/bash
set -e

PGPASSWORD=${POSTGRES_PASSWORD} psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$ILMAKALU_DB" -h localhost <<-EOSQL
    CREATE EXTENSION postgis;
    CREATE EXTENSION dblink;
EOSQL