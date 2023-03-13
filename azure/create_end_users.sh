#/bin/sh

set -e

# obtain variables
. ./azure_variables.sh "$1"

# create end user role and make admin role a member of it
psql "$conn_string" <<-EOSQL
    CREATE GROUP "end_users" WITH NOLOGIN;
    GRANT "end_users" TO ${DATA_USER};
    GRANT "end_users" TO ${ADMIN_USER};
EOSQL

# create (or replace) function and event trigger for ownership transfer
psql "$conn_string" -f ./sql_files/table_owner_transfer_trigger.sql

# Give the group required privileges in compute schemas
for schema in aluejaot built delineations energy functions grid_globals traffic
do
    psql "$conn_string" <<-EOSQL
    GRANT USAGE ON SCHEMA $schema TO "end_users";
    GRANT SELECT ON ALL TABLES IN SCHEMA $schema TO "end_users";
    ALTER DEFAULT PRIVILEGES IN SCHEMA $schema GRANT SELECT ON TABLES TO "end_users";
EOSQL
done

# Give the group required privileges in user schemas
for schema in user_input user_output
do
    psql "$conn_string" <<-EOSQL
    GRANT ALL ON SCHEMA $schema TO "end_users";
    GRANT SELECT ON ALL TABLES IN SCHEMA $schema TO "end_users";
    ALTER DEFAULT PRIVILEGES IN SCHEMA $schema GRANT SELECT ON TABLES TO "end_users";
EOSQL
done

# create users one by one and assign them to end user group
for end_user in $END_USERS
do
    end_user_pw=$(openssl rand -base64 12)
    psql "$conn_string" <<-EOSQL
    CREATE USER ${end_user} WITH PASSWORD '${end_user_pw}';
    GRANT "end_users" TO ${end_user};
EOSQL
    echo "Created user ${end_user} with password '${end_user_pw}'"
done