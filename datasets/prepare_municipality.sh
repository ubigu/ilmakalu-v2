#!/bin/sh
# initialize datasets for one specific municipality

# Kudos: https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0

if [ "$sourced" -eq "1" ];then
    echo "Use sh or bash or shell executable to run script, source will not work."
    return 0
fi

if [ $# -ne 1 ]; then
    echo "Usage: $0 <municipality_id>"
    exit 1
fi

if [ $(echo "$1" | grep -E '^[0-9]{3}$') ]; then
    echo "Processing municipality: '$1'"
else
    echo "Municipality three digit string not recognized"
    exit 2
fi

python="$(dirname -- $0)/../venv/bin/python"
echo "Running data generation for municipality: $1"
echo "$python"
$python --version

# run grid cell travel time calculation

# run XX calculation
# <your script here>