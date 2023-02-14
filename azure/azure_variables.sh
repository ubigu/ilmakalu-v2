config_yaml="./ilmakalu_azure.yaml"

yq() {
  docker run --rm -i -v "${PWD}":/workdir mikefarah/yq "$@"
}

parse_config () {
    parsed_value=$(yq eval -e ".${1}" - < $config_yaml) > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        retval="$parsed_value"
    else
        retval=""
    fi
    echo "$retval"
}

# manually set
DBHOST_NAME=$(parse_config "postgres_flexible_server.server_name")
ADMIN_USER=$(parse_config "postgres_flexible_server.admin_user")
ADMIN_PASSWORD=$(parse_config "postgres_flexible_server.admin_password")
COMPUTE_DATABASE_NAME=$(parse_config "postgres_flexible_server.compute_database")
COMPUTE_USER=$(parse_config "postgres_flexible_server.compute_user")
COMPUTE_USER_PASSWORD=$(parse_config "postgres_flexible_server.compute_password")
COMPUTE_MASTER_DATABASE=$(parse_config "postgres_compute_master.database")
COMPUTE_MASTER_HOST=$(parse_config "postgres_compute_master.server_name")
COMPUTE_MASTER_USER=$(parse_config "postgres_compute_master.user")
COMPUTE_MASTER_PASSWORD=$(parse_config "postgres_compute_master.password")
COMPUTE_MASTER_DUMP_FILE=$(parse_config "postgres_compute_master.dump_output_file")

RG=$(parse_config "resource_group.name")
MY_IP=$(curl -s ifconfig.me)

if ! $(az account show > /dev/null); then
    az login
fi

SUBS=$(az account subscription list --query '[].subscriptionId' --output tsv)

# set subscription
az account set --subscription $SUBS

# save connection string
conn_string=$(az postgres flexible-server show-connection-string \
    --server-name $DBHOST_NAME \
    --admin-user $ADMIN_USER \
    --admin-password "$ADMIN_PASSWORD" \
    --query "connectionStrings.psql_cmd" \
    --output tsv)

# compute database, compute user
conn_string_ilmakalu=$(echo "postgresql://{login}:{password}@{server}.postgres.database.azure.com/postgres?sslmode=require" | \
    sed "s/{login}/$COMPUTE_USER/;s/{password}/$COMPUTE_USER_PASSWORD/;s/{server}/$DBHOST_NAME/;s/postgres?/${COMPUTE_DATABASE_NAME}?/")

# compute database, admin user
conn_string_adm_ilmakalu=$(echo $conn_string | sed 's/postgres?/${COMPUTE_DATABASE_NAME}?/')
