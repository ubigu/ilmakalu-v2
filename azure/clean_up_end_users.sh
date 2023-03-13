#/bin/sh

set -e

# obtain variables
. ./azure_variables.sh "$1"

# remove user group
psql "$conn_string" <<-EOSQL
    DROP OWNED BY "end_users";
    DROP USER "end_users";
EOSQL

# clean up end users and resources they own
for end_user in $END_USERS
do
    psql "$conn_string" <<-EOSQL
    DROP USER $end_user;
EOSQL
done

# remove event trigger
psql "$conn_string" <<-EOSQL
    DROP FUNCTION IF EXISTS trigger_create_set_table_owner CASCADE; 
    DROP EVENT TRIGGER IF EXISTS trigger_create_set_table_owner CASCADE;
EOSQL
