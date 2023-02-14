#!/bin/sh

set -e

# Create users for compute database

# obtain variables
. ./azure_variables.sh

# Create user for compute database
psql "$conn_string" <<-EOSQL
    CREATE USER "$COMPUTE_USER" WITH PASSWORD '$COMPUTE_USER_PASSWORD';
    GRANT "$COMPUTE_USER" TO "$ADMIN_USER";
EOSQL
