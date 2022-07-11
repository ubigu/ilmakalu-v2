#!/bin/sh
# initialize datasets for one specific municipality

# Kudos: https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0

if [ "$sourced" -eq "1" ];then
    echo "Use sh or bash or shell executable to run script, source will not work."
    return 0
fi

# initialize python
python="$(dirname -- $0)/../venv/bin/python"

# run grid cell travel time calculation
$python "$(dirname -- $0)/compute_grid.py"

# run XX calculation
# <your script here>