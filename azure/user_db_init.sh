#/bin/sh

set -e
# Initialize user database for the first time

# obtain variables
. ./azure_variables.sh "$1"

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
    GRANT ALL PRIVILEGES ON DATABASE "$DATA_DATABASE" TO $DATA_USER;
    ALTER DATABASE "$DATA_DATABASE" OWNER TO $DATA_USER;
EOSQL

# create data schemas
psql "$conn_string_ilmakalu_data" -f $USER_DATA_MASTER_DUMP_FILE

# create and (foreign) map schemas (user : data)
for schema in $COMPUTE_SCHEMAS;
do
    echo "CREATE SCHEMA IF NOT EXISTS ${schema};" | psql "$conn_string_ilmakalu_data" -
done

# psql "$conn_string_ilmakalu_data" <<-EOSQL
#     SET SCHEMA PATH '"$user"', functions, public;
# EOSQL