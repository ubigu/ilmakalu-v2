rakennusluokitus_1994 = {
                        "A1":['011', '012','013'],
                        "A2": ['021','022'],
                        "A3": ['032', '039'],
                        "B":['041'],
                        "C":['111','112','119','121','123','124','129', '131','139','141'],
                        "D":['151'],
                        "E":['161','162','163','164','169'],
                        "F":['211','213','214','215','219','221','222','223','229','231','239','241'],
                        "G":['311','312', '322','323','324', '331', '341','342','349', '351','352','353','354','359', '369'],
                        "H":['511', '521', '531','532', '541','549'],
                        "J":['611','613','691','692','699'],
                        "K":['711','712','719'],
                        "L":['721','722','729'],
                        "M":['811','819','891','892','893','899'],
                        "N":['931','941','999']
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
    
    # if value was not found in the classification return "Other buildings" 
    return "N"

if __name__ == "__main__":
    print(building_type_level1_1994('699'))
    print(building_type_level1_1994('011'))
    print(building_type_level1_1994('11'))
    print(building_type_level1_1994('B'))
    print(building_type_level1_1994('1111'))