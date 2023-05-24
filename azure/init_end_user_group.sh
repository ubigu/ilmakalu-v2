#/bin/sh

set -e

# obtain variables
. ./azure_variables.sh "$1"

# create group role and grant application roles membership to it
psql "$conn_string_adm_ilmakalu_data" <<-EOSQL
    CREATE GROUP "end_users" WITH NOLOGIN;
    GRANT "end_users" TO $DATA_USER;
    GRANT "end_users" TO $ADMIN_USER;
    GRANT "end_users" TO $COMPUTE_USER;
EOSQL

# Give the group required privileges in compute schemas
for schema in $COMPUTE_SCHEMAS
do
    psql "$conn_string_adm_ilmakalu_data" <<-EOSQL
    GRANT USAGE ON SCHEMA $schema TO "end_users";
    GRANT SELECT ON ALL TABLES IN SCHEMA $schema TO "end_users";
    ALTER DEFAULT PRIVILEGES FOR USER $ADMIN_USER IN SCHEMA $schema GRANT SELECT ON TABLES TO "end_users";
    ALTER DEFAULT PRIVILEGES FOR USER $DATA_USER IN SCHEMA $schema GRANT SELECT ON TABLES TO "end_users";
EOSQL
done

# Give the group required privileges in user schemas
for schema in user_input user_output
do
    psql "$conn_string_adm_ilmakalu_data" <<-EOSQL
    GRANT ALL ON SCHEMA $schema TO "end_users";
    GRANT SELECT ON ALL TABLES IN SCHEMA $schema TO "end_users";
    ALTER DEFAULT PRIVILEGES FOR USER $ADMIN_USER IN SCHEMA $schema GRANT SELECT ON TABLES TO "end_users";
    ALTER DEFAULT PRIVILEGES FOR USER $DATA_USER IN SCHEMA $schema GRANT SELECT ON TABLES TO "end_users";
EOSQL
done