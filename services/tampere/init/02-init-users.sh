#!/bin/bash
set -e

PGPASSWORD=${POSTGRES_PASSWORD} psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -h localhost <<-EOSQL
    SELECT '${EMISSIONTEST_USER_PW}' AS koe;
    CREATE USER emissiontest WITH PASSWORD '${EMISSIONTEST_USER_PW}';
    CREATE USER internal WITH PASSWORD '${INTERNAL_USER_PW}';
    CREATE USER schemacreator WITH PASSWORD '${SCHEMACREATOR_USER_PW}';
    CREATE USER tablecreator WITH PASSWORD '${TABLECREATOR_USER_PW}';
    CREATE USER cloudsqladmin WITH PASSWORD '${CLOUDSQLADMIN_USER_PW}';
    CREATE USER cloudsqlsuperuser WITH SUPERUSER PASSWORD '${CLOUDSQLSUPERUSER_USER_PW}';
    GRANT schemacreator TO ilmakalu;
    CREATE GROUP organisationname;
    GRANT organisationname TO ilmakalu;
    GRANT tablecreator TO ilmakalu;
EOSQL