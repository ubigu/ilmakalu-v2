#!/bin/sh

# Prepare GIS materials

set -e

# Parse configuration YAML
# Built using:
# yq --version
# yq (https://github.com/mikefarah/yq/) version 4.16.2

python_interpreter="./venv/bin/python"

config_yaml="config/config.yaml"

grid_file="grid_1km/grid_250m.shp"
municipality_file="./external/TietoaKuntajaosta_2022_10k.zip"
urban_centers_file="./external/keskustatkaupanalueet.zip"
urban_zones_file="./external/YKRVyohykkeet2021.zip"
urban_rural_file="./external/YKRKaupunkiMaaseutuLuokitus2018.zip"
corine_file="./external/U2018_CLC2018_V2020_20u1.gpkg"

municipality_grid_sql_file="sql/municipality_grid.sql"
urban_zones_process_sql_file="sql/urban_zones_and_land_use.sql"

parse_config () {
    parsed_value=$(yq eval -e ".${1}" - < $config_yaml) > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        retval="$parsed_value"
    else
        retval=""
    fi
    echo "$retval"
}

# dynamic configuration
# refer to configuration YAML

deployment="local_dev"

db_name=$(parse_config "database.${deployment}.database")
db_host=$(parse_config "database.${deployment}.host")
db_port=$(parse_config "database.${deployment}.port")
db_user=$(parse_config "database.${deployment}.user")
db_password=$(parse_config "database.${deployment}.pass")

db_addr="dbname=${db_name} host=${db_host} port=${db_port} user=${db_user} password=${db_password}"

# Grid
echo "Processing grid"
if ! [ -f "$grid_file" ]; then
    sh generate_250m_grid.sh
else
    echo "Grid file '$grid_file' exists, not generating."
fi

echo "Upload grid to database"
ogr2ogr -nln data.fi_grid_250m -f "PostgreSQL" PG:"$db_addr" "$grid_file"

# Municipality
echo "Upload municipality data"
ogr2ogr -overwrite -nln data.fi_municipality_2022_10k -nlt MULTIPOLYGON -f "PostgreSQL" PG:"$db_addr" \
    "/vsizip/$municipality_file" Kunta

# Urban and commercial centers
echo "Upload urban and commercial centers"
ogr2ogr -overwrite -nln data.fi_centers -f "PostgreSQL" PG:"$db_addr" \
    "/vsizip/$urban_centers_file" KeskustaAlueet

echo "Compute urban center centroids"
psql -v ON_ERROR_STOP=1 "$db_addr" -f sql/urban_center_centroid.sql

# Urban zones
echo "Upload urban zones"
ogr2ogr -overwrite -nln data.fi_urban_zones -f "PostgreSQL" PG:"$db_addr" \
    "/vsizip/$urban_zones_file" YKRVyohykkeet2021

# Urban-rural
echo "Upload urban-rural classification"
ogr2ogr -overwrite -lco precision=NO -nln data.fi_urban_rural -f "PostgreSQL" PG:"$db_addr" \
    "/vsizip/$urban_rural_file" YKRKaupunkiMaaseutuLuokitus2018

# corine
echo "Upload corine land cover"
ogr2ogr -overwrite -nln data.corine_land_cover_2018_eu -f "PostgreSQL" PG:"$db_addr" \
  "$corine_file" U2018_CLC2018_V2020_20u1

# municipality grid
echo "Process municipality grid"
psql -v ON_ERROR_STOP=1 "$db_addr" -f "$municipality_grid_sql_file"

# YKR data
echo "Obtain YKR population and employment data"
$python_interpreter ykr_process.py

# process uploaded data
echo "Process urban zones data"
psql -v ON_ERROR_STOP=1 "$db_addr" -f "$urban_zones_process_sql_file"
