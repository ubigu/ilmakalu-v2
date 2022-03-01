# a module for handling municipal and regional codes

def mun_code_handler(code:int):
    if len(str(code)) == 1:
        return "KU00" + str(code)
    elif len(str(code)) == 2:
        return "KU0" + str(code)
    else:
        return "KU" + str(code)


def reg_code_handler(code:int):
    if len(str(code)) == 1:
        return "MK0" + str(code)
    elif len(str(code)) == 2:
        return "MK" + str(code)
