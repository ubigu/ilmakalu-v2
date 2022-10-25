# Intro

This document describes how datasets are initialized

# Used schemas

TODO: _schema decisions might need redesign_

## data

Layers computed during initialization.

## prepared_data

Intermediate results, obtained when generating actual data layers.

Contents in this schema can be later on utilized in creating municipality targeted
specific data layers.

# 250m national grid skeleton

## Computing

Grid is computed from national 1km grid by upsampling.

Grid generation is performed in `generate_250m_grid.sh`

Processing will take several minutes, and should be performed using suitable
Python virtual environment.

Processing steps in generating script:
* national 1km grid is obtained from WFS
* rasterize 1km grid
* sample up by 4, obtaining 250m raster
* generate artificial id:s for 250m raster (avoid merging of cells in polygonizing)
* polygonize raster
* compute and add `xyind` -attribute, save to shapefile
* verify result (compute unique areas from cells, manual verification)

## Inserting result to database

Data source: `grid_1km/grid_250m.shp`

Load data:
```sh
ogr2ogr -nln data.fi_grid_250m \
    -f "PostgreSQL" PG:"dbname='databasename' host='addr' port='5432' user='x' password='y'" \
    grid_1km/grid_250m.shp
```

# Municipality region data

Source: https://tiedostopalvelu.maanmittauslaitos.fi/tp/kartta

Processing instructions assume Geopackage format. Other format selection might
require changing source layer name in import.

Load data:
```sh
ogr2ogr -nln data.fi_municipality_2022_10k -nlt MULTIPOLYGON \
    -f "PostgreSQL" PG:"dbname='databasename' host='addr' port='5432' user='x' password='y'" \
    /vsizip//path/to/file/TietoaKuntajaosta_2022_10k.zip Kunta 
```

## Source data schema:
* Projection: EPSG:3067
* Geometry: Multipolygon
* Feature Count: 309

```
FID Column = id
Geometry Column = geom
gml_id: Integer64 (0.0)
natcode: String (20.0)
namefin: String (60.0)
nameswe: String (60.0)
landarea: Real(Float32) (0.0)
freshwarea: Real(Float32) (0.0)
seawarea: Real(Float32) (0.0)
totalarea: Real(Float32) (0.0)
```
# Urban centers and commercial centers

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

## Source data schema
* Projection: EPSG:3067
* Geometry: Polygon
* Feature Count: 304

```
Keskustyyp: String (50.0)
Kaupunkise: String (50.0)
KeskusNimi: String (60.0)
SHAPE_Leng: Real (19.11)
SHAPE_Area: Real (19.11)
```

# Urban zones

Data source: https://wwwd3.ymparisto.fi/d3/gis_data/spesific/YKRVyohykkeet2021.zip

Load data:
```sh
ogr2ogr -nln data.fi_urban_zones \
    -f "PostgreSQL" PG:"dbname='databasename' host='addr' port='5432' user='x' password='y'" \
    /vsizip//path/to/file/YKRVyohykkeet2021.zip YKRVyohykkeet2021
```

## Source data schema
* Projection: 3067
* Geometry: Polygon
* Feature Count: 5201

```
vyoh: Integer (5.0)
Ydinalue: Integer (5.0)
vyohselite: String (80.0)
MuutosPvm: Date (10.0)
Shape_Leng: Real (19.11)
Shape_Area: Real (19.11)
```

# Urban-Rural classification

Data source: https://wwwd3.ymparisto.fi/d3/gis_data/spesific/YKRKaupunkiMaaseutuLuokitus2018.zip

Load data:
```sh
ogr2ogr -lco precision=NO -nln data.fi_urban_rural \
    -f "PostgreSQL" PG:"dbname='databasename' host='addr' port='5432' user='x' password='y'" \
    /vsizip//path/to/file/YKRKaupunkiMaaseutuLuokitus2018.zip YKRKaupunkiMaaseutuLuokitus2018
```

## Source data schema

* Projection: 3067
* Geometry: Polygon
* Feature Count: 318

```
Luokka: String (3.0)
Nimi: String (40.0)
Shape_Leng: Real (19.11)
Shape_Area: Real (19.11)
```
# CORINE land cover

Data source: https://land.copernicus.eu/pan-european/corine-land-cover/clc2018?tab=download

Load data:
```sh
ogr2ogr -nln data.corine_land_cover_2018_eu \
  -f "PostgreSQL" PG:"dbname='databasename' host='addr' port='5432' user='x' password='y'" \
  U2018_CLC2018_V2020_20u1.gpkg U2018_CLC2018_V2020_20u1
```

## Source data schema

* Projection: 3035
* Geometry: Multi Polygon
* Feature Count: 2375406

```
FID Column = OBJECTID
Geometry Column = Shape
Code_18: String (3.0)
Remark: String (20.0)
Area_Ha: Real (0.0)
ID: String (18.0)
```

# Combined 250m grid

Grid has to be prepared for calculation use. To perform this, following steps
should be taken.

## Create and populate table

Run `sql/municipality_grid.sql` in order to create and populate grid. Grid cells are
labeled with national municipality code, if grid and municipality areas intersect.

Grid cell geometry occurs multiple times in target table, if same grid cell
intersects with multiple municipalities.

## Add zone data

This step is performed later

## Add distance to city centers

This step is performed later

# YKR data

Population of YKR data is done in script: `ykr_process.py`

Required data is saved to directory `ykr`.

Input files used:
* T01_vae_e.mdb
* T03_tpa_e_TOL2008.mdb

Data is read. Population and employment related (required) data is saved to
table `data.population_employment`

# Country specific data enrichment

Data preprocessing is done for the whole country, if it is seen that results
will be usable in municipality level also.

One specific counterexample is grid level Corine land cover aggregate data.
It is not possible to correctly compute land use variables from
aggregated country level data. Problem is on the municipality border cells,
where correct land cover aggregate computation requires that land cover data
is clipped with municipality region.

For municipality level, there is a specific routine to compute land cover
aggregates.

## Urban/Rural areas to 250m grid

Urban/rural -clasification is expressed in 250m grid.

## Urban zones to 250m grid

Urban zones are expressed in 250m grid.
## Combine urban/rural and urban zones grid

Urban/rural classification is used in 250m grid. Where urban zones are
defined, urban zone information overwrites urban/rural.
## Processing Corine data

* Select Corine geometries for Finnish extent
* subdivide Corine geometries (to ease grid processing step)
* compute land cover data in grid cells
* compute land cover aggregate for Corine main classes (1, 2, ..., 5)

# Municipality specific data enrichment (Corine)

Municipality specific land cover data aggregate is computed with
provided SQL.

## Travel time from grid cell to nearest center (via road)

Travel time is computed via road network, using provided Python script.

Processing steps:
* obtain urban centers
* obtain all grid cells in specific municipality
* for each grid cell
  * find 10 (configurable) nearest urban centers (shortest beeline distance)
  * find nearest urban center (shortest road distance) from selected ten urban centers
  * save shortest road distance and respective center id as grid cell attributes

# Graphhopper configuration

Graphhopper search radius should be increased. Current tuned value is 10km,
and this value seems to provide reasonable results (with limited test data).

Value must be incorporated into service config file, and it cannot be changed
during run time.

Configuration is done in Dockerfile.

If value is too small, then for grid cells too far from road network are
not assigned a routing result. This will ruin the computation of shortest
distance to nearest urban center.

# Emission database for building materials and services (CO2-data.fi)

CO2data.fi database, API and webite are a responsibility of Finnish Environment Institute or in short SYKE. The service can be accessed at https://co2data.fi. 
The website is available in Finnish, Swedish and English, but the data itself is available only in English. The goal of the database is to standardize 
building lifecycle emission calculations.

The whole database is offered without a charge as a JSON file which can be accessed here: https://co2data.fi/api/co2data_construction.json. 

It is important to note that the database contains four kinds of emission categories. They are stated below. 
- Emissions from material usage presented as kg of CO2 equivalent per square meter (e.g. floor panel)
- Emissions from material usage presented as kg of CO2 equivalent per piece (e.g a kitchen sink)
- Emissions from a processes (e.g. demolition of a building or earthwork) 
- Scenarios (e.g. biofuels as energy resource vs. fossil fuels as energy resource)

Ilmakalu does not utilize scenarios, but all the other three are used and have identical emphasis. Please note that the data structure can slightly differ between different categories. Below are some important attributes to note:

- **ResourceID**: States a unique identifier for a resource.
- **ResourceType**: States to what category a resource belongs to (see above)
- **WasteFactor**: States what proportion of *a material* is gone to waste during utilization. For example a waste factor of 1.05 tells that 5 % of a material goes to waste e.g. during installation so in reality 1.05 of said material is needed.
- **RefServiceLifeNormal**: States expected service life of *a material*.

**End of Life scenario** section tells what happens to *a material* after its lifecycle has ended. It is stated as follows:

```
"End of life scenario": {
    "Reuse": 0,
    "Recycled": 92,
    "Energy": 0,
    "Final": 8,
    "Hazardous": 0
}
```

Where `Reuse` states how much of material is used again as it were, `Recycled` expresses how much of it was recycled, `Energy` states how much of it was used for energy production `Final` states how much of it became waste and `Hazardous` expresses what amount of it become hazardous waste. The value of these five amounts to 100. 

**Conversions** section contains information about amount of *a material* in a different metric than mass (kg) if needed. This can be e.g. volume (m3) or length (m). Conversions are not used by the tool at the moment.

```
"Conversions": [
            {
                "Field": "Volume",
                "Unit": "m3",
                "Value": 338
            }
        ]
```

Please note that any estimations of how much any specific material or service is approximately used per a certain building type have not been conducted by SYKE, but rather is a responsibility of a user of this tool. User can specify this in `building_type_material_mapping.json`. Take a look at separate instructions on how to use it from `instructions_for_building_material_mapping.md`.

In case of any unexpected interruptions in service availibility the JSON database, as it were in 09/09/2022, has been saved to the code repository so that it's
structure at the time could be inspected. 