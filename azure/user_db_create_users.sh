#!/bin/sh

set -e

# Create users for compute database

# obtain variables
. ./azure_variables.sh

# Create user for compute database
psql "$conn_string" <<-EOSQL
    CREATE USER "$DATA_USER" WITH PASSWORD '$DATA_PASSWORD';
    GRANT "$DATA_USER" TO "$ADMIN_USER";
EOSQL
