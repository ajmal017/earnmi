from datetime import datetime

from earnmi.uitl.jqSdk import jqSdk

code = "601318" #在datetime(2019, 2, 27, 9, 48)，到达 high_price=68.57

jq = jqSdk.get()

end_day = datetime(year=2019, month=6, day=30,hour=23)

code = '801742'
__sw_code_list = ["801011",
                      "801012",
                      "801013",
                      "801014",
                      "801015",
                      "801016",
                      "801017",
                      "801018",
                      "801021",
                      "801022",
                      "801023",
                      "801024",
                      "801032",
                      "801033",
                      "801034",
                      "801035",
                      "801036",
                      "801037",
                      "801041",
                      "801051",
                      "801053",
                      "801054",
                      "801055",
                      "801072",
                      "801073",
                      "801074",
                      "801075",
                      "801076",
                      "801081",
                      "801082",
                      "801083",
                      "801084",
                      "801085",
                      "801092",
                      "801093",
                      "801094",
                      "801101",
                      "801102",
                      "801111",
                      "801112",
                      "801123",
                      "801124",
                      "801131",
                      "801132",
                      "801141",
                      "801142",
                      "801143",
                      "801151",
                      "801152",
                      "801153",
                      "801154",
                      "801155",
                      "801156",
                      "801161",
                      "801163",
                      "801164",
                      "801171",
                      "801172",
                      "801173",
                      "801174",
                      "801175",
                      "801176",
                      "801177",
                      "801178",
                      "801181",
                      "801182",
                      "801191",
                      "801192",
                      "801193",
                      "801194",
                      "801202",
                      "801203",
                      "801204",
                      "801205",
                      "801211",
                      "801212",
                      "801213",
                      "801214",
                      "801222",
                      "801223",
                      "801231",
                      "801711",
                      "801712",
                      "801713",
                      "801721",
                      "801722",
                      "801723",
                      "801724",
                      "801725",
                      "801731",
                      "801732",
                      "801733",
                      "801734",
                      "801741",
                      "801742",
                      "801743",
                      "801744",
                      "801751",
                      "801752",
                      "801761",
                      "801881"]

for code in __sw_code_list:
    stocks = jq.get_industry_stocks(code)
    listStr = ""
    for stock in stocks:
        sCode:str = stock
        end = sCode.index(".")
        if (len(listStr) > 0):
            listStr = listStr + ","
        listStr = listStr + f"'{sCode[0:end]}'"
    print(f"stockMap=['{code}']=[{listStr}]")



