if [ "$1" = "local" ]; then
    run_mode="local"
    config_yaml="./ilmakalu_local.yaml"
else
    run_mode="azure"
    config_yaml="./ilmakalu_azure.yaml"
fi

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

# dump home
COMPUTE_MASTER_DATABASE=$(parse_config "postgres_compute_master.database")
COMPUTE_MASTER_HOST=$(parse_config "postgres_compute_master.server_name")
COMPUTE_MASTER_USER=$(parse_config "postgres_compute_master.user")
COMPUTE_MASTER_PASSWORD=$(parse_config "postgres_compute_master.password")
COMPUTE_MASTER_DUMP_FILE=$(parse_config "postgres_compute_master.dump_output_file")

# userdata database
DATA_DATABASE=$(parse_config "postgres_flexible_server.data_database")
DATA_USER=$(parse_config "postgres_flexible_server.data_user")
DATA_PASSWORD=$(parse_config "postgres_flexible_server.data_password")

# dblink service
ILMAKALU_COMPUTE_SERVICE_NAME=$(parse_config "postgres_compute_service.name")

# user data (Ubigu sources)
USER_DATA_MASTER_HOST=$(parse_config "user_data_source.server_name")
USER_DATA_MASTER_DB=$(parse_config "user_data_source.database")
USER_DATA_MASTER_USER=$(parse_config "user_data_source.user")
USER_DATA_MASTER_PASSWORD=$(parse_config "user_data_source.password")
USER_DATA_MASTER_DUMP_FILE=$(parse_config "user_data_source.dump_output_file")

COMPUTE_SCHEMAS=$(parse_config "user_data.schemas[]")

RG=$(parse_config "resource_group.name")
MY_IP=$(curl -s ifconfig.me)

if [ "$run_mode" = "azure" ]; then
    echo "Azure"
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

    # skeleton for connection string
    conn_str_skel=$(az postgres \
        flexible-server show-connection-string \
        -d $COMPUTE_DATABASE_NAME --query "connectionStrings.psql_cmd" \
        --out tsv)

    # compute database, compute user
    conn_string_ilmakalu=$(echo $conn_str_skel | \
        sed "s/{login}/$COMPUTE_USER/;s/{password}/$COMPUTE_USER_PASSWORD/;s/{server}/$DBHOST_NAME/;s/postgres?/${COMPUTE_DATABASE_NAME}?/")

    # data database, data user
    conn_string_ilmakalu_data=$(echo $conn_str_skel | \
        sed "s/{login}/$DATA_USER/;s/{password}/$DATA_PASSWORD/;s/{server}/$DBHOST_NAME/;s/postgres?/${DATA_DATABASE}?/")

    # compute database, admin user
    conn_string_adm_ilmakalu=$(echo $conn_string | sed "s/postgres?/${COMPUTE_DATABASE_NAME}?/")

    # data database, admin user
    conn_string_adm_ilmakalu_data=$(echo $conn_string | sed "s/postgres?/${DATA_DATABASE}?/")
else
    echo "Local"
    PORT=65432
    conn_string="postgresql://$ADMIN_USER:$ADMIN_PASSWORD@$DBHOST_NAME:${PORT}/postgres?sslmode=require"
    conn_string_adm_ilmakalu_data="postgresql://$ADMIN_USER:$ADMIN_PASSWORD@$DBHOST_NAME:${PORT}/${DATA_DATABASE}?sslmode=require"
    conn_string_ilmakalu_data="postgresql://$DATA_USER:$DATA_PASSWORD@$DBHOST_NAME:${PORT}/${DATA_DATABASE}?sslmode=require"
fi