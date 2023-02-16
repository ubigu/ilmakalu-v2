#!/bin/bash
set -e

PGPASSWORD=${ILMAKALU_USER_PW} psql -v ON_ERROR_STOP=1 --username "$ILMAKALU_USER" --dbname "$ILMAKALU_DB" -h localhost <<-EOSQL
    CREATE SCHEMA user_input;
    CREATE SCHEMA user_output;
EOSQL