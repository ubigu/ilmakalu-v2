#!/bin/sh
# initialize datasets for one specific municipality

set -e

if [ $# -ne 1 ]; then
    echo "Usage: $0 <municipality_id>"
    exit 1
fi

echo "Running data generation for municipality: $1"
