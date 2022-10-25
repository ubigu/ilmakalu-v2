# Handle case when grid cell centroid happens to land on motorway

When blindly routing from grid cell center to nearest urban center, there will be cases
when road distance is larger than expected.

This happens (most likely) due to traveling motorway to "wrong" direction.

## How to detect

If beeline distance is smalle, and road distance is relatively large, one might suspect
that this problem was activated.

## How to mitigate

Cells, where beeline distance and road distances differ (greatly), another computation
round should be activated. New routes should be calculated, e.g. from
* random points
* gridded points, relative to grid coordinates, e.g. (0.25,0.25), (0.25,0.75), (0.75,0.25), (0.75,0.75)

## Implementation estimate

* distance checker limit search (human effort)
* re-looping problematic grid cells
* computing routes
* selecting minimum distance
* detecting if result is valid
* possible refinement with finer new grid

# Get processes from CO2data.fi database

For now we only get materials from the said database due to unclarity on how we should process gwp values for processes. 
The gwp values are served in different groupings which raises many questions. 

## Implementation estimate

Processes can be easily incorporated to existing code as long as we get info on how to handle database numbers and categories properly.
Requires help from substance experts. Once we understand the data, we can first get processes into postgres into a separate table and 
then incorporate that table data in function `calc_material_co2`. 

# Include ability to add materials in pieces-per-building-format to building_type_material_mapping.json

For now all materials listed in said json document are used in kg per m2 format. However many materials (e.g. sink or door)
apply better in calculating emissions if they can be stated as pieces per building. 

## Implementation estimate

* Add "Materials_pieces" key-value pair similar to "Materials_kg" to `building_type_material_mapping.json`.
* Add needed functionality to function `calc_material_co2`.

# Create a more general script for fetching building data from WFS

Current implementation is tailored for building data from Espoo. The data has many holes in it which are handled by the code. 
For general usage we don't want to accommodate all shortages in data input, but rather give informative errors if documented
prerequisities don't apply in customer data. 

## How to detect

Try using any other wfs service and data for the scripts and it will quickly fail. 

## Implementation estimate

- Negociate internally what prerequisities we want to give to building data
- Copy `get_buildings_from_wfs.py` and make changes that apply to general usage
- Copy `calculate_building_emissions_from_materials.py` and make changes that apply to general usage

# Refactor and transfer traficom script from data folder to dataset folder

Traficom script which gets usage power divisions for traffic in a certain municipality exists in separate folder from 
other scripts in the repository. Its code needs still refactoring and it could use the same config module and template
as other scripts.

## Implementation estimate

- In newer config module everything is ready and only adjustments are needed.
- The script uses premade json files at the moment but it would be better if it created them by itself.
- No need to ask user separately for municipality and region code, just add them to `config.yaml` or use an existing attribute there
- Manually made modules used by the script should either be removed or moved to dataset folder adjusted accordingly. 
- Add statistics URLs to config.yaml instead of having them hard coded into the `get_traffic_usage_power_divisions.py`

# Make building type mapping less error prone

Currently we utilize all three/four hierarchy levels in stat.fi building type classification.
For mapping we use number codes in string format (such as 0110). They're easy to mix up while reading and while processing data.

## How to detect

Take a look at `building_type_mapper.py` and any `building_type_material_mapping.json`. 

## Implementation estimate

- Discuss and negociate how we should approach building mapping. Using full string values such as "one-dwelling houses" might be equally problematic since then we have to match strings. 
- Make changes accordingly to `building_type_mapper.py`
- Make changes accordingly to json material mapping files
- Make changes accordingly to `buildings_for_grid_global.py`
- Make changes accordingly to `calculate_building_emissions_from_materials.py`
- Add a new parameter to `config.yaml` and instruct user to use that for applying correct function from `building_type_mapper.py`

# Refactor fuel mapper module for buildings

Module `building_fuel_mapper.py` has a lot of boiler plate code currently and thus it's readability and maintainability are not the best. 

# Refactor building counter for grid cells module for buildings

Module `building_counter_for_grid_cells.py` has a lot of boiler plate code currently and thus it's readability and maintainability are not the best. 

# Change language of traficom usage mode json queries to English from Finnish

Right now the two languages mix uncomfortably. Go to the Traficom site and check if JSONs are available in English. Translate all variables in code. 

This relates to:
 - `get_traffic_power_mode_distribution.py`
 - `config.py`
 - `config_template.yaml`

# Refactor script that gets mode power distribution for traffic

Refactor `get_traffic_power_mode_distribution.py` to get rid of its boilerplate code.