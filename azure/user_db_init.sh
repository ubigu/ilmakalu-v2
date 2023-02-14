#/bin/sh

set -e
# Initialize user database for the first time

# obtain variables
. ./azure_variables.sh

## initialize cloud resources
## - database server
## - keyvault

## add credentials to keyvault

## create database (admin : postgres)
psql "$conn_string" <<-EOSQL
    DROP DATABASE IF EXISTS "$DATA_DATABASE";
    CREATE DATABASE "$DATA_DATABASE";
EOSQL

## create extension (admin : data)
psql "$conn_string_adm_ilmakalu_data" <<-EOSQL
    CREATE EXTENSION "postgis";
    GRANT ALL PRIVILEGES ON DATABASE "$DATA_DATABASE" TO $DATA_USER;
    ALTER DATABASE "$DATA_DATABASE" OWNER TO $DATA_USER;
EOSQL
