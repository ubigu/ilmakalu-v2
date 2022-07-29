rakennusluokitus_1994 = {
                        "A1: Erilliset pientalot":['011', '012','013'],
                        "A2: Rivi- ja ketjutalot": ['021','022'],
                        "A3: Asuinkerrostalot": ['032', '039'],
                        "B: Vapaa-ajan asuinrakennukset":['041'],
                        "C: Liikerakennukset":['111','112','119','121','123','124','129', '131','139','141'],
                        "D: Toimistorakennukset":['151'],
                        "E: Liikenteen rakennukset":['161','162','163','164','169'],
                        "F: Hoitoalan rakennukset":['211','213','214','215','219','221','222','223','229','231','239','241'],
                        "G: Kokoontumisrakennukset":['311','312', '322','323','324', '331', '341','342','349', '351','352','353','354','359', '369'],
                        "H: Opetusrakennukset":['511', '521', '531','532', '541','549'],
                        "J: Teollisuusrakennukset":['611','613','691','692','699'],
                        "K: Varastorakennukset":['711','712','719'],
                        "L: Palo- ja pelastustoimen rakennukset":['721','722','729'],
                        "M: Maatalousrakennukset":['811','819','891','892','893','899'],
                        "N: Muut rakennukset":['931','941','999']
                         }
                    
def building_type_level1_1994(building:str):

    # check if given parameter is a string. If not return a value error. 
    if type(building) != str:
        raise ValueError("Parameter given is not a string, please check data.")

    # make given parameter's length to three if a leading zero has been omitted before
    if len(building) == 2:
        building = '0'+building

    # loop through 1994 classification data structure
    for key, values in rakennusluokitus_1994.items():
        if building in values:
            return key
    
    # if value was not found in the classification return value error. 
    raise ValueError("Code not found in 1994 classification, please check data.")

if __name__ == "__main__":
    print(building_type_level1_1994('699'))
    print(building_type_level1_1994('011'))
    print(building_type_level1_1994('11'))
    #print(building_type_1994('1111')) <-- raises value error