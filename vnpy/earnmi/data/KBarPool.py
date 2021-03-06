import functools
from datetime import datetime,timedelta
from typing import Sequence, Any, Tuple

from earnmi.data.FetcherDailyBar import FetcherDailyBar
from earnmi.uitl.utils import utils
from vnpy.trader.object import BarData
from vnpy.trader.constant import Exchange, Interval
from earnmi.data.import_data_from_jqdata import save_bar_data_from_jqdata


# def barcmp(bar1,bar2):
#     if bar1.datetime < bar2.datetime:
#         return 1
#     elif bar1.datetime > bar2.datetime:
#         return -1
#     return 0

class KBarPool:

    def __init__(self, code: str):
     self.__code = code
     self.__data_fetch = FetcherDailyBar(code)
     self.__pool_data:Sequence["BarData"] = None


     """
     不包含end 日期的k线
     """
    def getData(self, end:datetime,count: int)-> Sequence["BarData"]:
        #是否满足从缓存里面取
        __pool_data = self.setPoolAt(end,count)
        ret = []
        addingCount = 0
        pool_size = len(__pool_data)
        for i in range(pool_size):
            index = pool_size - i -1
            data = __pool_data[index]
            if addingCount == 0:
                if data.datetime < end and not utils.is_same_day(data.datetime,end):
                    ret.insert(0,data)
                    addingCount = 1
            else:
                ret.insert(0,data)
                addingCount = addingCount+1
            if(addingCount >= count):
                break
        return ret

    def clean(self):
        self.__data_fetch.clearAll()

    """
    不包含end 日期的k线
    """
    def getDataFrom(self, start: datetime,end:datetime)-> Sequence["BarData"]:
        #//是否满足从缓存里面取
        __pool_data = self.__data_fetch.fetch(start,end)
        return __pool_data

    def setPoolAt(self,end:datetime,count:int):

        theEnd = end
        theStart = theEnd - timedelta(days=366)

        pool_start, pool_end, poll_data = self.__makePollSize(theStart, theEnd)

        ##前面缓存
        while len(poll_data)< count:
            theEnd = theStart - timedelta(days=1)
            theStart = theEnd - timedelta(days=366)
            ## 可能很久都没有上市了。
            start2, end2, dataList2 = self.__makePollSize(theStart, theEnd)
            pool_start = start2
            theStart = start2
            if (len(dataList2) < 1):
                break
            dataList2.extend(poll_data)
            poll_data = dataList2

        if(len(poll_data)<1000 - 365):
            theStart = end +  timedelta(days=1)
            nowTime = datetime.now()
            if(theStart < nowTime):
                theEnd = theStart +  timedelta(days=365)
                if theEnd > nowTime:
                    theEnd = nowTime
                start2, end2, dataList2 = self.__makePollSize(theStart, theEnd)
                if len(dataList2) > 0:
                    poll_data.extend(dataList2)
                    pool_end = end2
        return poll_data


    def _buidl_start_date(self,d:datetime) ->datetime:
            return datetime(year=d.year,month=d.month,day=d.day,hour=00,minute=00,second=1)

    def _buidl_end_date(self,d: datetime) -> datetime:
        return datetime(year=d.year, month=d.month, day=d.day, hour=23, minute=59, second=59)

    def __makePollSize(self,start:datetime,end:datetime) ->Tuple[datetime, datetime, Sequence["BarData"]]:
        #print(f"__makePollSize:{start}, {end}")

        from earnmi.uitl.utils import utils

        detal_day = (end-start).days
        extraDay = 365 - detal_day
        if(extraDay > 0):
            end = end + timedelta(days=extraDay)

        pool_data = self.__data_fetch.fetch(start,end)
        #list.sort(pool_data,)
        return start,end,pool_data




if __name__ == "__main__":
    code = "300004"


    print("------------------------------")


    pool1 = KBarPool(code)

    toaday = datetime(year=2018,month=3,day=3)

    toaday = datetime.now()
    bars = pool1.getData(toaday,300)

    preivoubar = None
    for bar in bars:
       assert bar.datetime < toaday
       if preivoubar:
           assert preivoubar.datetime < bar.datetime
       preivoubar = bar

    print(len(bars))
    assert len(bars) == 300

    print("下面从缓存取，不应该有从网络里面取")
    bars = pool1.getData(toaday,200)
    preivoubar = None
    for bar in bars:
        assert bar.datetime < toaday
        if preivoubar:
            assert preivoubar.datetime < bar.datetime
        preivoubar = bar

    assert len(bars) == 200
    barsFromCache = pool1.getDataFrom(datetime.now() - timedelta(days=600),datetime.now())
    preivoubar = None
    for bar in barsFromCache:
        assert bar.datetime < toaday
        if  preivoubar:
            assert preivoubar.datetime < bar.datetime
        preivoubar = bar

    print(len(barsFromCache))

    pool2 = KBarPool(code)
    barsFromNet = pool2.getDataFrom(datetime.now() - timedelta(days=600), datetime.now())

    print(len(barsFromNet))



    assert len(barsFromCache) == len(barsFromNet)

