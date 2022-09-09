rakennusluokitus_1994 = {
                        "011":"A1","012":"A2","013":"A3",
                        "021":"A2","022":"A2",
                        "032":"A3","039":"A3",
                        "041":"B",
                        "111":"C","112":"C","119":"C","121":"C","123":"C","124":"C","129":"C","131":"C", "139":"C","139":"C","141":"C",
                        "151":"D",
                        "161":"E","162":"E","163":"E","164":"E","169":"E",
                        "211":"F","213":"F","214":"F","215":"F","219":"F","221":"F","222":"F","223":"F","229":"F","231":"F","239":"F","241":"F",
                        "311":"G","312":"G","322":"G","323":"G","324":"G","331":"G","341":"G","342":"G","349":"G","351":"G","352":"G","353":"G","354":"G","359":"G","369":"G",
                        "511":"H","521":"H","531":"H","532":"H","541":"H","549":"H",
                        "611":"J","613":"J","691":"J","692":"J","699":"J",
                        "711":"K","712":"K","719":"K",
                        "721":"L","722":"L","729":"L",
                        "811":"M","819":"M","891":"M","892":"M","893":"M","899":"M",
                        "931":"N","941":"N","999":"N"
                         }

                    
def building_type_level1_1994(building:str):

    # check if given parameter is a string. If not return a value error. 
    if type(building) != str:
        raise ValueError("Parameter given is not a string, please check data.")

    # add a leading zero if it it's omitted
    if len(building) == 2:
        building = '0'+building

    # return matching value from the dictionary above. If no matching key is found, return "N" (other building)
    return rakennusluokitus_1994.get(building,"N")
    

if __name__ == "__main__":
    print(building_type_level1_1994('699'))
    print(building_type_level1_1994('011'))
    print(building_type_level1_1994('11'))
    print(building_type_level1_1994('B'))
    print(building_type_level1_1994('1111'))