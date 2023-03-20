#!/bin/sh

. ./azure_variables.sh

pg_dump \
    --no-acl \
    -O \
    -N user_input \
    -N user_output \
    -T spatial_ref_sys \
    "user=${COMPUTE_MASTER_USER} password=${COMPUTE_MASTER_PASSWORD} host=${COMPUTE_MASTER_HOST} dbname=${COMPUTE_MASTER_DATABASE}" \
    | awk '/^CREATE EVENT TRIGGER/,/^$/ {next} {print}' - \
    | sed 's/public.\(co2_\)/functions.\1/ig' \
    | grep -v '^COMMENT ON EXTENSION' > $COMPUTE_MASTER_DUMP_FILE