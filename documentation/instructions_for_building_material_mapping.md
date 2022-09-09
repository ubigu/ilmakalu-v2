# Intro

This document describes how user can state materials for each building type. 

## Where

Use `building_type_material_mapping.json` located in datasets folder. 

## How

Add wanted materials under building types as key value pairs. 
Keys represent resource IDs in CO2data.fi database and values
kilograms of said material per m2. 

Example stating 10 kg of aerated concrete (7000000995), 5 kilograms of water vapour barrier (7000000252)
and 2 kilograms of bitumen waterproofing membrane per each m2 in attached houses (A2). List can be empty as well.

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

Building types are based on classification made by Statistics Finland. There buildings are mapped to 
three different hierarchical levels from which mainly 1st level is used in this tool. The classification 
is decsribed in their website [here](https://www.stat.fi/en/luokitukset/rakennus/rakennus_1_19940101/?code=02&name=Attached%20houses) in detail.

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
