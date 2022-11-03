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

Resulting table: `data.fi_grid_municipalities`

## Add zone data

This step is performed later

## Add distance to city centers

This step is performed later

# YKR data

Population of YKR data is done in script: `ykr_process.py`

Required data is saved to directory `datasets/ykr`.

Input files used:
* T01_vae_e.mdb
* T03_tpa_e_TOL2008.mdb

Data is read. Population and employment related (required) data is saved to
tables `data.employ` and `data.pop`

# Country specific data enrichment

Data preprocessing is done for the whole country.

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
* compute land and water aggregate ha-areas

Execute file against the database: `sql/urban_zones_and_land_use.sql`

Result table: `data.clc`

Compare table: `grid_globals.clc`

Intermediate tables are generated in `data` -schema during SQL process,
and they are currently preserved.

N.B. All the columns in `grid_globals.clc` can not be generated, due to
source material difference (Corine).

# Other municipality specific data enrichment

Municipality specific other data processing is described below.

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

The whole database is offered without a charge as a JSON file which can be accessed here: https://co2data.fi/api/co2data_construction.json. The URL is already stated in `config.yaml` from where the script looks for it.

It is important to note that the database contains four kinds of emission categories. They are stated below. 
- Emissions from material usage presented as kg of CO2 equivalent per square meter (e.g. floor panel)
- Emissions from material usage presented as kg of CO2 equivalent per piece (e.g a kitchen sink)
- Emissions from a processes (e.g. demolition of a building or earthwork) 
- Scenarios (e.g. biofuels as energy resource vs. fossil fuels as energy resource)

In order to fetch needed building type material costs, run `get_building_material_co2_costs.py`. Note that the script requires database access info from `config.yaml`.

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

# Traffic power mode distribution from Traficom

For traffic power mode distribution data Traficom statistics are used. We utilize traficom pxAPI and the following statistical resources. These URLs are already present in the script. 
- [Passenger cars in traffic on 31 June 2021 by area](https://trafi2.stat.fi/PXWeb/pxweb/en/TraFi/TraFi__Liikennekaytossa_olevat_ajoneuvot/010_kanta_tau_101.px/)
- [Vehicles in traffic by quarter in 2008 to 2021](https://trafi2.stat.fi/PXWeb/pxweb/en/TraFi/TraFi__Liikennekaytossa_olevat_ajoneuvot/040_kanta_tau_104.px/)

Run `get_traffic_power_mode_distribution.py`. Provide municipality and region codes in `config.yaml`. The reason for this is that passenger car
statistics exist at a municipality level, but all other vehicle types only at a region level. When providing codes make sure they match (e.g. Helsinki and Uusimaa or Turku and Varsinais-Suomi). 

Note that the script also requires an existing database, its access info from `config.yaml` and finally existing schemas which are created by following the instructions in `restore_dump.md`. 

## Coding schemas

### Energy modes for passenger cars

Naming in Finnish.

| Energy mode | Code |
| ----------- | ----------- |
| Bensiini | 01 |
| Diesel | 02 |
| Polttoöljy | 03 |
| Sähkö | 04 |
| Vety | 05 |
| Kaasu | 06 |
| Nestekaasu (LPG) | 11 |
| Maakaasu (CNG) | 13 |
| Bensiini/Puu | 33 |
| Bensiini + moottoripetroli | 34 |
| Etanoli | 37 |
| Bensiini/CNG | 38 |
| Bensiini/Sähkö (ladattava hybridi) | 39 |
| Bensiini/Etanoli | 40 |
| Bensiini/Metanoli | 41 |
| Bensiini/LPG | 42 |
| Diesel/CNG | 43 |
| Diesel/Sähkö (ladattava hybridi) | 44 |
| Muu | Y |
| Yhteensä | YH |

### Energy modes for vans/trucks/busses

Naming in Finnish.

| Energy mode | Code |
| ----------- | ----------- |
| Bensiini | 01 |
| Diesel | 02 |
| Polttoöljy | 03 |
| Sähkö | 04 |
| Vety | 05 |
| Kaasu | 06 |
| Biodiesel | 10 |
| Nestekaasu (LPG) | 11 |
| Maakaasu (CNG) | 13 |
| Moottoripetroli | 31 |
| Bensiini/Puu | 33 |
| Bensiini + moottoripetroli | 34 |
| Etanoli | 37 |
| Bensiini/CNG | 38 |
| Bensiini/Sähkö (ladattava hybridi) | 39 |
| Bensiini/Etanoli | 40 |
| Bensiini/LPG | 42 |
| Diesel/CNG | 43 |
| Diesel/Sähkö (ladattava hybridi) | 44 |
| H-ryhmän maakaasu | 56 |
| LNG | 65 |
| Diesel/LNG | 67 |
| Muu | Y |
| Yhteensä | YH |

### Mode of transport codes for vans/trucks/busses

Naming in Finnish. 

| Mode of transport | Code |
| ----------- | ----------- |
| Henkilöautot | 01 |
| Pakettiautot | 02 |
| Kuorma-autot | 03 |
| Linja-autot | 04 |
| Erikoisautot | 05 |
| Moottoripyörät | 06 |
| Mopot | 07 |
| Moottorikelkat | 08 |
| Traktorit | 09 |
| Moottorityökoneet | 10 |
| Kolmi- tai nelipyörät L5/L5e  | 11 |
| Kevyet nelipyörät L6/L6e | 12 |
| Nelipyörät L7/L7e | 13 |
| Matkailuperävaunut | 15 |
| Puoliperävaunut | 16 |
| Muut perävaunut yhteensä | 17 |
| Kaikki autot | 00 |
| Yhteensä | YH |

# Get buildings from WFS

*Note that these scripts are currently tailored for Espoo WFS buildings data.*

In order to fetch buildings from WFS service, provide necessary wfs parameters in `config.yaml`. These include service URL, version, layer and attributes of interest. 
Note that for now the script that gets buildings is more or less tailored for the specific building data layer from the service of the city of Espoo. Providing any other service
and specs will probably cause an error or unexpected results.

Note that the script additionally requires database access info from `config.yaml`.

After fetching buildings to database run `buildings_for_grid_global.py`. This script calculates a new database table based on building data which is identical to the original ilmakalu dataschema so that the original SQL functions will run.

# Calculate co2 emissions from building material costs for each grid cell

*Note that this section is future developing and not connected to the rest of the tool yet.*

By running `calculate_building_emissions_from_materials.py` you can create a layer in postgis that states total building material co2 costs for each grid cell. 

Before running the script take a look at the following files located in datasets folder.

- `building_type_material_mapping_1994.json` 
- `building_type_material_mapping_2018.json` 
- `building_type_material_mapping_grid_global.json` (2018)
  
Add wanted materials under building types as key value pairs. Keys represent resource IDs in CO2data.fi database and values kilograms of said material per m2. 

Example stating 10 kg of aerated concrete (7000000995), 5 kilograms of water vapour barrier (7000000252) and 2 kilograms of bitumen waterproofing membrane per each m2 in attached houses ("A2" for 1994 and "012" for 2018). An empty list is interpreted as no material usage per said building type. 

```
    "A2": 
        {
        "Materials_kg": {
            "7000000995": 10,
            "7000000252": 5,
            "7000000270": 2
            }
        }
```

For additional information on material codes check https://co2data.fi or https://co2data.fi/api/co2data_construction.json. Note that they utilize different building type mapping and should match the function used in scripts. The mapping in `building_type_material_mapping_grid_global.json` is based on hand picked types by Ubigu.

If you don't assign any costs at all in json file, the sript will still run, but all co2 costs will be zero. 

The json files are partioned by building types. They all have basis on stat.fi classification, either 1994 or 2018 one, but are all modifications of it. In the classification buildings are mapped to three different hierarchical levels. 

## 1994 classification

The classification is decsribed in Statistics Finland website [here](https://www.stat.fi/en/luokitukset/rakennus/rakennus_1_19940101). 

| Code | Level | Description |
| ----------- | ----------- | ----------- |
| A1 | 2 | Detached and semi-detached houses |
| A2 | 2 | Attached houses |
| A3 | 2 | Blocks of flats |
| B | 1 | Free-time residential buildings |
| C | 1 | Commercial buildings |
| D | 1 | Office buildings |
| E | 1 | Transport and communications buildings |
| F | 1 | Buildings for institutional care |
| G | 1 | Assembly buildings |
| H | 1 | Educational buildings |
| J | 1 | Industrional buildings |
| K | 1 | Warehouses |
| L | 1 | Fire fighting and rescue service buildings |
| M | 1 | Agricultural buildings |
| N | 1 | Other buildings |


## 2018 classification

The classification is decsribed in Statistics Finland website [here](https://www.stat.fi/en/luokitukset/rakennus/). 

| Code | Level | Description |
| ----------- | ----------- | ----------- |
| 011 | 2 | Detached and semi-detached houses |
| 012 | 2 | Blocks of flats |
| 013 | 2 | Residential buildings for communities |
| 014 | 2 | Dwellings for special groups |
| 02 | 1 | Free-time residential buildings |
| 03 | 1 | Commercial buildings |
| 04 | 1 | Office buildings |
| 05 | 1 | Transport and communications buildings |
| 06 | 1 | Buildings for institutional care |
| 07 | 1 | Assembly buildings |
| 08 | 1 | Educational buildings |
| 09 | 1 | Industrional buildings |
| 10 | 1 | Warehouses |
| 11 | 1 | Fire fighting and rescue service buildings |
| 12 | 1 | Agricultural buildings |
| 13 | 1 | Other buildings |
| 14 | 1 | Other buildings |
| 19 | 1 | Other buildings |

## Hand picked classification by Ubigu based on 2018 mapping (grid globals)

This classification is another modification of the 2018 classification. See it fully [here](https://www.stat.fi/en/luokitukset/rakennus/). 

| Code | Level | Description |
| ----------- | ----------- | ----------- |
| 0110 | 3 | One-dwelling houses |
| 0111 | 3 | Two-dwelling houses |
| 0112 | 3 | Terraced houses |
| 0120 | 3 | Low-rise blocks of flats |
| 0121 | 3 | Residential blocks of flats |
| 0130 | 3 | Residential buildings for communities |
| 02 | 1 | Free-time residential buildings |
| 031 | 2 | Wholesale and retail trade buildings |
| 032 | 2 | Hotel buildings |
| 033 | 2 | Restaurants and other similar buildings |
| 04 | 1 | Office buildings |
| 05 | 1 | Transport and communications buildings |
| 06 | 1 | Buildings for institutional care |
| 07 | 1 | Assembly buildings |
| 08 | 1 | Educational buildings |
| 09 | 1 | Industrial and mining and quarrying buildings |
| 10 | 1 | Energy supply buildings |
| 12 | 1 | Warehouses |
| 19 | 1 | Other buildings |
