#!/bin/sh

set -e

# obtain variables
. ./azure_variables.sh "$1"

# Create user for compute database
psql "$conn_string" <<-EOSQL
    CREATE USER "$DATA_USER" WITH PASSWORD '$DATA_PASSWORD';
    GRANT "$DATA_USER" TO "$ADMIN_USER";
EOSQL