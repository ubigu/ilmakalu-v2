#!/bin/sh

set -e

# Drop users from compute database

# obtain variables
. ./azure_variables.sh

# Drop user for compute database
psql "$conn_string" <<-EOSQL
    DROP USER IF EXISTS "$COMPUTE_USER";
EOSQL
