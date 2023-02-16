#/bin/sh

set -e
# Initialize user database for the first time

# obtain variables
. ./azure_variables.sh

if ! [ -f "$USER_DATA_MASTER_DUMP_FILE" ]; then
    echo "No dump file '$USER_DATA_MASTER_DUMP_FILE', cannot proceed."
    exit 1
fi

## create database (admin : postgres)
psql "$conn_string" <<-EOSQL
    DROP DATABASE IF EXISTS "$DATA_DATABASE";
    CREATE DATABASE "$DATA_DATABASE";
EOSQL

## create extension (admin : data)
#cat <<-EOSQL
psql "$conn_string_adm_ilmakalu_data" <<-EOSQL
    CREATE EXTENSION "postgis";
    CREATE EXTENSION "dblink";
    CREATE EXTENSION "postgres_fdw";
    GRANT ALL PRIVILEGES ON DATABASE "$DATA_DATABASE" TO $DATA_USER;
    ALTER DATABASE "$DATA_DATABASE" OWNER TO $DATA_USER;
    CREATE SERVER $ILMAKALU_COMPUTE_SERVICE_NAME FOREIGN DATA WRAPPER postgres_fdw OPTIONS (dbname '$COMPUTE_DATABASE_NAME', host 'localhost');
    CREATE USER MAPPING FOR "$DATA_USER" SERVER $ILMAKALU_COMPUTE_SERVICE_NAME OPTIONS (user '$COMPUTE_USER', password '$COMPUTE_USER_PASSWORD');
    GRANT USAGE ON FOREIGN SERVER $ILMAKALU_COMPUTE_SERVICE_NAME TO $DATA_USER;
EOSQL

# create schemas
psql "$conn_string_ilmakalu_data" -f $USER_DATA_MASTER_DUMP_FILE
