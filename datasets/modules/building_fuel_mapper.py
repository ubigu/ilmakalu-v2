import pandas as pd
import string as str

'''
Steps:
- Generate most common fuel types in each generalized building type (lvl 1 and 2 hierarchies)
- Handle building types without fuel info
- Generalize fuel types
- Return a new dataframe (varmaan pääscripting puolella pitää ottaa kopio (copy), koska muuten viittauksiin voi tulla jotain häikkää?)
'''

# the function takes dataframe and field specifications as parameters
def fuel_mapper(df, building_type_field:str,building_type_generalized_field:str,fuel_field:str) -> pd.DataFrame:
    
    # figure out most common fuel for each existing building type (generalized)
    # note that in case of ties mode() returns several rows. In this case, we just take the first row. 
    most_common_fuel = {}
    for i in df[building_type_generalized_field].unique():
        most_common_fuel[i] = df[df[building_type_generalized_field]==i][fuel_field].mode().iloc[0]
        
    # For rows which lack fuel info delete the ones which building type is null or in the list below
    '''
    lämmittämättömät varastot (1210), varastokatokset (1215), hevostallit (1414), muut eläinsuojat (1419),
    kasvihuoneet (1490), maatalouden varastorakennukset (1492), muut maa- metsä- ja kalatalouden rakennukset (1499),
    saunarakennukset (1910), talousrakennukset (1911), muualla luokittelemattomat rakennukset (1919), 
    ympärivuotiseen käyttöön soveltuvat vapaa-ajan asuinrakennukset (210),
    osavuotiseen käyttöön soveltuvat vapaa-ajan asuinrakennukset (211), 
    kulkuneuvojen katokset (514)
    '''
    removal = df[(df[fuel_field].str.lower() == 'ei') & (df[building_type_field].isin([1210,1215,1414,1419,1490,1492,1499,1910,1911,1919,210,211,514]))].index
    df.drop(removal, inplace=True)

    
    # For rows which lack fuel info and are in the list below, give the most common fuel in assembly buildings
    '''
    avopalvelujen rakennukset (621), museot ja taidegalleriat (713), seura- ja kerhorakennukset (720),
    uskonnonharjoittamisrakennukset (730), muut uskonnollisten yhteisöjen rakennukset (739),
    urheilu- ja palloiluhallit (743), muut urheilu- ja liikuntarakennukset (749),
    muut kokoontumisrakennukset (790), lasten päiväkodit (810),
    yleissivistävien oppilaitosten rakennukset (820), ammatillisten oppilaitosten rakennukset (830),
    korkeakoulurakennukset (840)
    '''
    df.loc[(df[fuel_field].str.lower() == 'ei') & (df[building_type_field].isin([621,713,720,730,739,743,749,790,810,820,830,840])), fuel_field] =  most_common_fuel["07"]
    

    # For rows which lack fuel info and are in the list below, give the most common fuel in warehouses
    '''
    yleiskäyttöiset teollisuushallit (910), lämpimät varastot (1211)
    '''
    df.loc[(df[fuel_field].str.lower() == 'ei') & (df[building_type_field].isin([910,1211])), fuel_field] =  most_common_fuel["12"]


    # For rows which lack fuel info and are in the list below, give the most common fuel in wholesale and retail trade buildings (level 2 hierarchy)
    '''
    kauppakeskukset ja liike- ja tavaratalot (311), muut myymälärakennukset (319)
    '''
    df.loc[(df[fuel_field].str.lower() == 'ei') & (df[building_type_field].isin([311,319])), fuel_field] =  most_common_fuel["031"]

    # For rows which lack fuel info and are 'Teollisuus- ja pienteollisuustalot' (920) give the most common fuel in industrial buildings
    df.loc[(df[fuel_field].str.lower() == 'ei') & (df[building_type_field] == 920), fuel_field] =  most_common_fuel["09"]

    # For rows which lack fuel info and are office buildings (400) give the most common fuel in that respective building type
    df.loc[(df[fuel_field].str.lower() == 'ei') & (df[building_type_field] == 400), fuel_field] =  most_common_fuel["04"]

    # For rows which lack fuel info and are 'muut majoitusliikerakennukset' (329) give the most common fuel in hotel buildings
    df.loc[(df[fuel_field].str.lower() == 'ei') & (df[building_type_field] == 329), fuel_field] =  most_common_fuel["032"]

    # For rows which lack fuel info and are 'ravintolarakennukset ja vastaavat liikerakennukset' (330) give the most common fuel in restaurants
    df.loc[(df[fuel_field].str.lower() == 'ei') & (df[building_type_field] == 330), fuel_field] =  most_common_fuel["033"]


    # For rows which lack fuel info and are in the list below, give the most common fuel in residential buildings for communities
    '''
    asuntolarakennukset (130), loma- lepo- ja virkistyskodit (322), laitospalvelujen rakennukset (620)
    '''
    df.loc[(df[fuel_field].str.lower() == 'ei') & (df[building_type_field].isin([130,322,620])), fuel_field] =  most_common_fuel["0130"]

    # For rows which lack fuel info and are one-dwelling houses give the most common fuel in that respective building type
    df.loc[(df[fuel_field].str.lower() == 'ei') & (df[building_type_field] == 110), fuel_field] =  most_common_fuel["0110"]

    # For rows which lack fuel info and are two-dwelling houses give the most common fuel in that respective building type
    df.loc[(df[fuel_field].str.lower() == 'ei') & (df[building_type_field] == 111), fuel_field] =  most_common_fuel["0111"]
    
    # For rows which lack fuel info and are terraced houses give the most common fuel in that respective building type 
    df.loc[(df[fuel_field].str.lower() == 'ei') & (df[building_type_field] == 112), fuel_field] =  most_common_fuel["0112"]

    # For rows which lack fuel info and are low-rise blocks of flats give the most common fuel in that respective building type
    df.loc[(df[fuel_field].str.lower() == 'ei') & (df[building_type_field] == 120), fuel_field] =  most_common_fuel["0120"]

    # For rows which lack fuel info and are residential blocks of flats give the most common fuel in that respective building type 
    df.loc[(df[fuel_field].str.lower() == 'ei') & (df[building_type_field] == 121), fuel_field] =  most_common_fuel["0121"]

    
    # For the following rows which lack fuel info give a value of 'other' for fuel
    '''
    pysäköintitalot ja -hallit (513), muut liikenteen rakennukset (590), jäähallit (740)
    '''
    df.loc[(df[fuel_field].str.lower() == 'ei') & (df[building_type_field].isin([513,590,740])), fuel_field] =  'muu_lammitys'

    
    # Generalize some fuel types based on the mapping below in assistant function and standardize spelling
    def generalize_fuels(fuel:str):
        kutsu = fuel.lower().replace('ä','a').replace('ö','o')
        if "kivihiili" in kutsu:
            return "kevyt_oljy"
        elif "turve" in kutsu:
            return "kevyt_oljy"
        elif "raskas" in kutsu:
            return "kevyt_oljy"
        elif "puu" in kutsu:
            return "puu"
        elif "kaasu" in kutsu:
            return "kaasu"
        elif "sahko" in kutsu:
            return "sahko"
        elif "maalampo" in kutsu:
            return "maalampo"
        elif "muu" in kutsu:
            return "muu_lammitys"
        elif "kauko" in kutsu:
            return "kaukolampo"
        elif "kevyt" in kutsu:
            return "kevyt_oljy"
        elif "ei" == kutsu:
            return pd.NA
        else:
            raise ValueError(f"Found a value that couldn't be processed: {fuel}")

    df[fuel_field] = [generalize_fuels(x) for x in df[fuel_field]]

    return df
