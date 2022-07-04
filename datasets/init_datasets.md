# Intro

This document describes how datasets are initialized

# Used schemas

## data

Storage for universal data. Generic source data, either self geneated or downloaded from public sources.
```sql
CREATE SCHEMA data;
```

# 250m national grid

## Computing

Grid is computed from 1km grid.

Grid generation is performed in `generate_250m_grid.sh`

## Inserting result to database

Data source: `grid_1km/grid_250m.shp`

Load data:
```sh
ogr2ogr -nln data.fi_grid_250m \
    -f "PostgreSQL" PG:"dbname='databasename' host='addr' port='5432' user='x' password='y'" \
    grid_1km/grid_250m.shp
```

# Municipality data

Source: https://tiedostopalvelu.maanmittauslaitos.fi/tp/kartta

Load data:
```sh
ogr2ogr -nln data.fi_municipality_2022_10k -nlt MULTIPOLYGON \
    -f "PostgreSQL" PG:"dbname='databasename' host='addr' port='5432' user='x' password='y'" \
    /vsizip//path/to/file/TietoaKuntajaosta_2022_10k.zip Kunta 
```

# Centers and shopping centers

Data source: https://wwwd3.ymparisto.fi/d3/gis_data/spesific/keskustatkaupanalueet.zip

Load data:
```sh
ogr2ogr -nln data.fi_centers \
    -f "PostgreSQL" PG:"dbname='databasename' host='addr' port='5432' user='x' password='y'" \
    /vsizip//path/to/file/keskustatkaupanalueet.zip KeskustaAlueet
```

Compute centroid to separate table:
```sql
CREATE TABLE data.fi_center_p AS
SELECT
    ogc_fid AS fi_center_ref,
    ST_Centroid(wkb_geometry) AS geom
FROM data.fi_centers;
```

# Urban zones

Data source: https://wwwd3.ymparisto.fi/d3/gis_data/spesific/YKRVyohykkeet2021.zip

Load data:
```sh
ogr2ogr -nln data.fi_urban_zones \
    -f "PostgreSQL" PG:"dbname='databasename' host='addr' port='5432' user='x' password='y'" \
    /vsizip//path/to/file/YKRVyohykkeet2021.zip YKRVyohykkeet2021
```

# Urban-Rural classification

Data source: https://wwwd3.ymparisto.fi/d3/gis_data/spesific/YKRKaupunkiMaaseutuLuokitus2018.zip

Load data:
```sh
ogr2ogr -lco precision=NO -nln data.fi_urban_rural \
    -f "PostgreSQL" PG:"dbname='databasename' host='addr' port='5432' user='x' password='y'" \
    /vsizip//path/to/file/YKRKaupunkiMaaseutuLuokitus2018.zip YKRKaupunkiMaaseutuLuokitus2018
```
