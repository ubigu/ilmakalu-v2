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
