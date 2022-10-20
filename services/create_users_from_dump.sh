#!/bin/sh

if [ $# -ne 2 ]; then
    echo "Usage: $0 <password> <ilmakalu_user>"
        exit 1
fi
infile="../datasets/dump_data/emissiontest_stripped.sql"
cat $infile | egrep 'OWNER|GRANT' | sed -n 's/^.*TO \([a-z]*\);/\1/p'| sort | uniq |\
    grep -v postgres |\
    grep -v "cloudsqlsuperuser" |\
    sed "s/^/CREATE USER /; s/$/ WITH PASSWORD '$1';/"

echo "CREATE USER cloudsqladmin WITH PASSWORD '$1';"
echo "CREATE USER cloudsqlsuperuser WITH SUPERUSER PASSWORD '$1';"
echo "GRANT schemacreator TO $2;"
# TODO: change organisation name default string
echo "CREATE GROUP organisationname;"
echo "GRANT organisationname TO $2;"
echo "GRANT tablecreator TO $2;"