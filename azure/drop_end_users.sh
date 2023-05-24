#/bin/sh

set -e

# obtain variables
. ./azure_variables.sh "$1"

# drop all end users, but don't touch end user group role
# Object owned by them are transferred to data user...
# ...hence DROP OWNED BY will only affect privileges owned by an end user
for end_user in $END_USERS
do
    psql "$conn_string_adm_ilmakalu_data" <<-EOSQL
    REASSIGN OWNED BY ${end_user} TO $DATA_USER;
    DROP OWNED BY ${end_user};
    DROP USER ${end_user};
EOSQL
done