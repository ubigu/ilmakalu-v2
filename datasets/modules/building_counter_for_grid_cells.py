import pandas as pd

'''
Below section creates separate dataframes for count and area calculations per 
building type and grid cell. These dataframes are concatenated in the end with
the common index (xyind, fuel, decade) and returned to client. 
'''

def building_counter_for_grid_cells(df,grid_cell_field:str,fuel_field:str,decade_field:str,floor_area_field:str,generalized_building_type_field:str):

    index = [grid_cell_field,fuel_field,decade_field]
    
    # Create an empty list for building type count and area dataframes
    dfs = []

    # Add building count per agreed index element to the list
    dfs.append(df.groupby(index,dropna=False)[grid_cell_field].count().reset_index(name="rakyht_lkm"))

    # Add building area per agreed index element to the list
    dfs.append(df.groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="rakyht_ala"))

    # Add warehouse count per index element to the list
    dfs.append(df[df[generalized_building_type_field]=="12"].groupby(index,dropna=False)[grid_cell_field].count().reset_index(name="varast_lkm"))

    # Add industrial and mining and quarrying buildings count per index element to the list
    dfs.append(df[df[generalized_building_type_field]=="09"].groupby(index,dropna=False)[grid_cell_field].count().reset_index(name="teoll_lkm"))

    # Add total floor area for residential buildings per index element to the list
    # Note that this takes dwellings for special groups (014) into account for now
    dfs.append(df[df[generalized_building_type_field].isin(["011","012","014"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="asuin_ala"))

    # Add total floor area for one-dwelling and two-dwelling houses
    # Existing module for building type aggregation doesn't take 3rd hierarchy level into account so right now we have detached and semidetached under same value
    dfs.append(df[df[generalized_building_type_field].isin(["011"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="erpien_ala"))

    # Add total floor area for terraced houses per index element to the list
    # Existing module for building type aggregation doesn't take 3rd hierarchy level into account so right now we have detached and semidetached with same value
    dfs.append(df[df[generalized_building_type_field].isin(["011"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="rivita_ala"))

    # Add total floor area for blocks of flats per index element to the list
    dfs.append(df[df[generalized_building_type_field].isin(["012"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="askert_ala"))

    # Add total floor area for residential buildings for communities per index element to the list
    dfs.append(df[df[generalized_building_type_field].isin(["013"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="asla_ala"))

    # Add total floor area for commercial buildings per index element to the list
    # Commercial buildings is a sum of wholesale buildings, hotels and restaurants
    dfs.append(df[df[generalized_building_type_field].isin(["031","032","033"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="liike_ala"))

    # Add total floor area for wholesale buildings per index element to the list
    dfs.append(df[df[generalized_building_type_field].isin(["031"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="myymal_ala"))

    # Add total floor area for hotel buildings per index element to the list
    dfs.append(df[df[generalized_building_type_field].isin(["032"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="majoit_ala"))

    # Add total floor area for restaurants for communities per index element to the list
    dfs.append(df[df[generalized_building_type_field].isin(["033"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="ravint_ala"))

    # Add total floor area for office buildings per index element to the list
    dfs.append(df[df[generalized_building_type_field].isin(["04"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="tsto_ala"))

    # Add total floor area for transport and communications buildings per index element to the list
    dfs.append(df[df[generalized_building_type_field].isin(["05"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="liiken_ala"))

    # Add total floor area for buildings for institutional care per index element to the list
    dfs.append(df[df[generalized_building_type_field].isin(["06"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="hoito_ala"))

    # Add total floor area for assembly buildings per index element to the list
    dfs.append(df[df[generalized_building_type_field].isin(["07"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="kokoon_ala"))

    # Add total floor area for educational buildings per index element to the list
    dfs.append(df[df[generalized_building_type_field].isin(["08"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="opetus_ala"))

    # Add total floor area for industrial and mining and quarrying buildings per index element to the list
    # Note that in 1994 energy supply buildings were part of main class 09, but in 2018 they form their own main class (10)
    dfs.append(df[df[generalized_building_type_field].isin(["09"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="teoll_ala"))

    # add total floor area for warehouses per index element to the list
    dfs.append(df[df[generalized_building_type_field].isin(["12"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="varast_ala"))

    # add total floor area for other buildings per index element to the list
    dfs.append(df[df[generalized_building_type_field].isin(["19"])].groupby(index,dropna=False)[floor_area_field].sum().reset_index(name="muut_ala"))

    # set common index for all dataframes in 
    inputs = [df.set_index(index) for df in dfs]

    # Merge all dataframes together (with concat)
    result = pd.concat(inputs, axis=1).reset_index()

    # fill NA with zero value in count and sum fields
    nullable_fields = ["rakyht_lkm", "rakyht_ala","varast_lkm","teoll_lkm","asuin_ala",
                      "erpien_ala","rivita_ala","askert_ala","asla_ala","liike_ala","myymal_ala",
                      "majoit_ala","ravint_ala","tsto_ala","liiken_ala","hoito_ala","kokoon_ala",
                      "opetus_ala","teoll_ala","varast_ala","muut_ala"]
    result[nullable_fields] = result[nullable_fields].fillna(0)

    return result
