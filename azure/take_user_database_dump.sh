#!/bin/sh

. ./azure_variables.sh

pg_dump \
    --no-acl \
    -O \
    -n user_input \
    -n user_output \
    -n aluejaot \
    -T spatial_ref_sys \
    "user=${USER_DATA_MASTER_USER} password=${USER_DATA_MASTER_PASSWORD} host=${USER_DATA_MASTER_HOST} dbname=${USER_DATA_MASTER_DB}" \
    | awk '/^CREATE FUNCTION/,/^\$\$;$/ {next} {print}' - \
    > $USER_DATA_MASTER_DUMP_FILE