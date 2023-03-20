#!/bin/sh

. ./azure_variables.sh

if [ "$1" = "" ]; then
    echo "Usage: $0 <name>"
    echo "Currently used rules:"
    az postgres flexible-server firewall-rule list --resource-group $RG --name $DBHOST_NAME --output tsv --query "[].name"
    echo "Current IP: $MY_IP"
    exit 1
fi

az postgres flexible-server firewall-rule create --resource-group $RG --name $DBHOST_NAME --rule-name "$1" --start-ip-address $MY_IP
