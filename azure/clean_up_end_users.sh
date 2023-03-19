#/bin/sh

set -e

# obtain variables
. ./azure_variables.sh "$1"

# clean up end users
for end_user in $END_USERS
do
    psql "$conn_string_adm_ilmakalu_data" <<-EOSQL
    DROP USER $end_user;
EOSQL
done