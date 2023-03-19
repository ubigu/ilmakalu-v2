#/bin/sh

set -e

# obtain variables
. ./azure_variables.sh "$1"

# create end user role and make admin role a member of it
psql "$conn_string_adm_ilmakalu_data" <<-EOSQL
    CREATE GROUP "end_users" WITH NOLOGIN; 
    GRANT "end_users" TO ${DATA_USER};
    GRANT "end_users" TO ${ADMIN_USER};
EOSQL

# Give the group required privileges in compute schemas
for schema in aluejaot built delineations energy functions grid_globals traffic
do
    psql "$conn_string_adm_ilmakalu_data" <<-EOSQL
    GRANT USAGE ON SCHEMA $schema TO "end_users";
    GRANT SELECT ON ALL TABLES IN SCHEMA $schema TO "end_users";
    ALTER DEFAULT PRIVILEGES IN SCHEMA $schema GRANT SELECT ON TABLES TO "end_users";
EOSQL
done

# Give the group required privileges in user schemas
for schema in user_input user_output
do
    psql "$conn_string_adm_ilmakalu_data" <<-EOSQL
    GRANT ALL ON SCHEMA $schema TO "end_users";
    GRANT SELECT ON ALL TABLES IN SCHEMA $schema TO "end_users";
EOSQL
done

# remove non-relevant, dump given, event trigger about changing new schema ownership
# there is probably something off in previous dump handling, event trigger is listed in pgadmin, but it is not listed in pg_event_trigger system table
# for now this event trigger is left as is
#psql "$conn_string_adm_ilmakalu_data" <<-EOSQL
#    DROP EVENT TRIGGER IF EXISTS trigger_create_set_schema_owner CASCADE;
#EOSQL

# create event trigger for ownership transfer
psql "$conn_string_adm_ilmakalu_data" -f ./sql_files/table_owner_transfer_trigger.sql
