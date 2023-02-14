#!/bin/sh

set -e

. ./azure_variables.sh

# create Azure postgres flexible server
# read configuration from provided YAML file

usage () {
    echo "Usage: $0"
    exit 2
}

LOCATION=northeurope

# list resource groups
az group list --query "[].name" --output tsv

# exit if resource group already exists (to be safe and not try to create identical resource group)
if $( az group list --query "[].name" --output tsv | grep -q "^${RG}$" ); then
    echo "Group exists"
    exit
fi

# create resource group
az group create --location $LOCATION --name $RG

echo "Creating flexible server: $DBHOST_NAME"
az postgres flexible-server create \
    --location $LOCATION \
    --resource-group $RG \
    --name $DBHOST_NAME \
    --admin-user $ADMIN_USER \
    --admin-password $ADMIN_PASSWORD \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --public-access $MY_IP \
    --storage-size 32 \
    --version 13 \
    --high-availability Disabled

# Try to connect
echo "Connecting to flexible server"
az postgres flexible-server connect \
    --name $DBHOST_NAME \
    --admin-user $ADMIN_USER \
    --admin-password "$ADMIN_PASSWORD"

# show conncection string
echo "Connection string"
az postgres flexible-server show-connection-string \
    --server-name $DBHOST_NAME \
    --admin-user $ADMIN_USER \
    --admin-password "$ADMIN_PASSWORD" \
    --query "connectionStrings.psql_cmd"

# save connection string
conn_string=$(az postgres flexible-server show-connection-string \
    --server-name $DBHOST_NAME \
    --admin-user $ADMIN_USER \
    --admin-password "$ADMIN_PASSWORD" \
    --query "connectionStrings.psql_cmd" \
    --output tsv)

# show open access ip:s
az postgres flexible-server firewall-rule list \
    --resource-group $RG --name $DBHOST_NAME

# list databases
az postgres flexible-server db list \
    --resource-group $RG \
    --server-name $DBHOST_NAME

# enable postgis
az postgres flexible-server parameter set \
    --resource-group $RG \
    --server-name $DBHOST_NAME \
    --subscription $SUBS \
    --name azure.extensions \
    --value postgis

echo "When done, delete resources:"
echo "az group delete --yes --resource-group $RG"

echo "List resource groups:"
echo 'az group list --query "[].name" --output tsv'
