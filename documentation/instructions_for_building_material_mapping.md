# Intro

This document describes how user can state materials for each building type.

## Where

Use `building_type_material_mapping.json` located in datasets folder. 

## How

Add wanted materials under building types as key value pairs. 
Keys represent resource IDs in CO2data.fi database and values
kilograms of said material per m2. 

Example stating 10 kg of aerated concrete (7000000995), 5 kilograms of water vapour barrier (7000000252)
and 2 kilograms of bitumen waterproofing membrane per each m2 in attached houses ("A2" for 1994 and "012" for 2018). An empty list is interpreted as no material usage per said building type. 

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

# Building types

Building types are based on classification made by Statistics Finland. They have released two classifications, first in 1994 and second and latest in 2018. Ilmakalu can utilize either one. In the classification buildings are mapped to three different hierarchical levels. In this tool 1st level is used with exception of residential buildings which use 2nd hierarchy level. 

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