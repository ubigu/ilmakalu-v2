import pandas as pd

'''
Generalize time of construction to decades accordingly:
Year 1920 and before that are given value of 1920
Years between 1921 and 2019 are notified as 1929, 1939 and etc. 
Years 2020 and later are given value of 2020
'''

def year_mapper(year:int):
    if pd.isna(year):
        return 9999
    if year <= 1920:
        return 1920
    elif year >= 1921 and year <= 2019:
        return year//10*10+9
    elif year >= 2020:
        return 2020
    else:
        print(f"There was a problem with value: {str(year)}")
        raise ValueError("Couldn't process value.")