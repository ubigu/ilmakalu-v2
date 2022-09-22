#!/bin/sh

if [ $# -ne 1 ]; then
    echo "Give password for all users"
    exit 1
fi
infile="../datasets/dump_data/emissiontest_stripped.sql"
cat $infile | egrep 'OWNER|GRANT' | sed -n 's/^.*TO \([a-z]*\);/\1/p'| sort | uniq |\
    grep -v postgres | sed "s/^/CREATE USER /; s/$/ WITH PASSWORD '$1';/"
