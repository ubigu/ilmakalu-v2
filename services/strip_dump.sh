#!/bin/sh

# strip garbage from dump

infile="../datasets/dump_data/emissiontest.sql"
outfile="../datasets/dump_data/emissiontest_stripped.sql"
#cat $infile | grep -v cloudsql > $outfile
cp $infile $outfile
