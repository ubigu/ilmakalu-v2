#/bin/sh

set -e

# obtain variables
. ./azure_variables.sh "$1"

# create users one by one and assign them to the end user group
for end_user in $END_USERS
do
    end_user_pw=$(openssl rand -base64 12)
    psql "$conn_string_adm_ilmakalu_data" <<-EOSQL
    CREATE USER ${end_user} WITH PASSWORD '${end_user_pw}';
    GRANT "end_users" TO ${end_user};
    GRANT ${end_user} TO $ADMIN_USER;
    GRANT ${end_user} TO $DATA_USER;
    ALTER DEFAULT PRIVILEGES FOR USER ${end_user} IN SCHEMA "user_input" GRANT SELECT ON TABLES TO "end_users";
    ALTER DEFAULT PRIVILEGES FOR USER ${end_user} IN SCHEMA "user_output" GRANT SELECT ON TABLES TO "end_users";
    ALTER ROLE ${end_user} SET search_path = public, functions;
EOSQL
    echo "Created user ${end_user} with password '${end_user_pw}'"
done
