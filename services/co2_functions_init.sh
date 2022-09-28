#!/bin/bash

# init CO2 -functions to local database
# Note: ugly hack, since we would like to have this in docker-compose in a long run

file=co2_functions.txt

DBUSER=docker
DBPASS=docker
DBPORT=5435
DB=ilmakalu

while read -r line;
do
    echo "# Line is: $line"
    echo "PGPASSWORD=${DBPASS} psql -U $DBUSER -h localhost -p $DBPORT $DB -f $line"
done < $file
