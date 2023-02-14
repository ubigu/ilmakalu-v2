#/bin/sh

set -e
# Initialize compute database for the first time

# obtain variables
. ./azure_variables.sh

## initialize cloud resources
## - database server
## - keyvault

## add credentials to keyvault

## create database (admin : postgres)
psql "$conn_string" <<-EOSQL
    DROP DATABASE IF EXISTS "$COMPUTE_DATABASE_NAME";
    CREATE DATABASE "$COMPUTE_DATABASE_NAME";
EOSQL

## create extension (admin : application)
psql "$conn_string_adm_ilmakalu" <<-EOSQL
    CREATE EXTENSION "postgis";
    GRANT ALL PRIVILEGES ON DATABASE "$COMPUTE_DATABASE_NAME" TO $COMPUTE_USER;
    ALTER DATABASE "$COMPUTE_DATABASE_NAME" OWNER TO $COMPUTE_USER;
EOSQL

## restore dump (user : application)
psql "$conn_string_ilmakalu" -f $COMPUTE_MASTER_DUMP_FILE
