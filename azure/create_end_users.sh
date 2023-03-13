#/bin/sh

set -e

# obtain variables
. ./azure_variables.sh "$1"

# create end user role and make admin role a member of it
psql "$conn_string" <<-EOSQL
    CREATE GROUP "table_owner" WITH NOLOGIN;
    CREATE GROUP "table_user" WITH NOLOGIN;
    CREATE GROUP "table_ownership_transfer" WITH NOLOGIN;
    GRANT "table_owner" TO ${DATA_USER};
    GRANT "table_owner" TO ${ADMIN_USER};
    GRANT "table_owner" TO "table_ownership_transfer" WITH ADMIN OPTION;
    GRANT "table_user" TO ${DATA_USER};
EOSQL

# create (or replace) function and event trigger for ownership transfer
psql "$conn_string" -f ./sql_files/create_trigger.sql

# grant execute on the function for usage group role
psql "$conn_string" <<-EOSQL 
    GRANT EXECUTE ON FUNCTION trigger_create_set_table_owner TO table_user;
EOSQL

# Give the group required privileges in compute schemas
for schema in aluejaot built delineations energy functions grid_globals traffic
do
    psql "$conn_string" <<-EOSQL
    GRANT USAGE ON SCHEMA $schema TO "table_user";
    GRANT SELECT ON ALL TABLES IN SCHEMA $schema TO "table_user";
    ALTER DEFAULT PRIVILEGES IN SCHEMA $schema GRANT SELECT ON TABLES TO "table_user";
EOSQL
done

# Give the group required privileges in user schemas
for schema in user_input user_output
do
    psql "$conn_string" <<-EOSQL
    GRANT ALL ON SCHEMA $schema TO "table_user";
    GRANT ALL ON SCHEMA $schema TO "table_ownership_transfer";
    GRANT ALL ON SCHEMA $schema TO "table_owner";
    GRANT SELECT ON ALL TABLES IN SCHEMA $schema TO "table_user";
    ALTER DEFAULT PRIVILEGES IN SCHEMA $schema GRANT SELECT ON TABLES TO "table_user";
EOSQL
done

# create users one by one and assign them to end user group
for end_user in $END_USERS
do
    end_user_pw=$(openssl rand -base64 12)
    psql "$conn_string" <<-EOSQL
    CREATE USER ${end_user} WITH PASSWORD '${end_user_pw}';
    GRANT "table_user" TO ${end_user};
EOSQL
    echo "Created user ${end_user} with password '${end_user_pw}'"
done