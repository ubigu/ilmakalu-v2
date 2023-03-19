#/bin/sh

set -e

# obtain variables
. ./azure_variables.sh "$1"

# create users one by one, assign them to end user group and alter their search path
for end_user in $END_USERS
do
    end_user_pw=$(openssl rand -base64 12)
    psql "$conn_string_adm_ilmakalu_data" <<-EOSQL
    CREATE USER ${end_user} WITH PASSWORD '${end_user_pw}';
    GRANT "end_users" TO ${end_user};
EOSQL
    echo "Created user ${end_user} with password '${end_user_pw}'"
done