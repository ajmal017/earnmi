import os
import timeit
from datetime import datetime
from functools import cmp_to_key
from typing import Tuple, Sequence, Union

import sklearn
from sklearn.ensemble import RandomForestClassifier
import joblib

from earnmi.chart.FloatEncoder import FloatEncoder, FloatRange
from earnmi.model.PredictAbilityData import PredictAbilityData
from earnmi.model.PredictOrder import PredictOrder
from earnmi.model.QuantData import QuantData
from vnpy.trader.object import BarData

from earnmi.data.SWImpl import SWImpl
from earnmi.model.CollectData import CollectData
from earnmi.model.CoreEngine import CoreEngine, BarDataSource, PredictModel
from earnmi.model.Dimension import Dimension, TYPE_3KAGO1, TYPE_2KAGO1
from earnmi.model.PredictData import PredictData
import pickle
import numpy as np
from earnmi.model.CoreEngineModel import CoreEngineModel




class SWDataSource(BarDataSource):
    def __init__(self,start:datetime,end:datetime ):
        self.index = 0
        self.sw = SWImpl()
        self.start = start
        self.end = end

    def onNextBars(self) -> Tuple[Sequence['BarData'], str]:
        # if self.index > 2:
        #     return None,None
        sw_code_list = self.sw.getSW2List()
        if self.index < len(sw_code_list):
            code = sw_code_list[self.index]
            self.index +=1
            return self.sw.getSW2Daily(code,self.start,self.end),code
        return None,None

class SVMPredictModel(PredictModel):

    def __init__(self,engine:CoreEngine,dimen:Dimension):
        self.engine = engine
        self.dimen = dimen
        self.quantData:QuantData = None
        self.classifierSell_1 = None
        self.classifierSell_2 = None
        self.classifierBuy_1 = None
        self.classifierBuy_2 = None
        self.labelListSell1:[] = None  ##标签值列表
        self.labelListSell2:[] = None  ##标签值列表
        self.labelListBuy1:[] = None  ##标签值列表
        self.labelListBuy2:[] = None  ##标签值列表


    def save(self,dirPath:str):
        if not os.path.exists(dirPath):
            os.makedirs(dirPath)
        f = open(f"{dirPath}/classifierSell_1", 'wb+')
        f.close()
        f = open(f"{dirPath}/classifierSell_2", 'wb+')
        f.close()
        f = open(f"{dirPath}/classifierBuy_1", 'wb+')
        f.close()
        f = open(f"{dirPath}/classifierBuy_2", 'wb+')
        f.close()

        joblib.dump(self.classifierSell_1, f"{dirPath}/classifierSell_1")
        joblib.dump(self.classifierSell_2, f"{dirPath}/classifierSell_2")
        joblib.dump(self.classifierBuy_1, f"{dirPath}/classifierBuy_1")
        joblib.dump(self.classifierBuy_2, f"{dirPath}/classifierBuy_2")
        modelBin =[self.quantData, self.labelListSell1, self.labelListSell2,self.labelListBuy1,self.labelListBuy2]
        with open(f"{dirPath}/modelBin", 'wb+') as fp:
            pickle.dump(modelBin, fp, -1)


    def load(self,dirPath:str):
        self.classifierSell_1 = joblib.load(f"{dirPath}/classifierSell_1")
        self.classifierSell_2 = joblib.load(f"{dirPath}/classifierSell_2")
        self.classifierBuy_1 = joblib.load(f"{dirPath}/classifierBuy_1")
        self.classifierBuy_2 = joblib.load(f"{dirPath}/classifierBuy_2")
        with open(f"{dirPath}/modelBin", 'rb') as fp:
            self.quantData, self.labelListSell1, self.labelListSell2,self.labelListBuy1,self.labelListBuy2 = pickle.load(fp)

    """
    建造模型
    """
    def build(self,engine:CoreEngine, sampleData:Sequence['CollectData'], quantData:QuantData):
        useSVM = True
        start = timeit.default_timer()
        self.quantData = quantData
        trainDataList = engine.getEngineModel().generateSampleData(engine, sampleData)
        size = len(trainDataList)
        engine.printLog(f"build PredictModel:dime={self.dimen}, sample size:{size} use SVM ={useSVM}",True)
        engine.printLog(f"   history quantdata: {self.quantData}")


        ##建立特征值
        x, y_sell_1,y_buy_1,y_sell_2,y_buy_2 = engine.getEngineModel().generateFeature(engine, trainDataList)
        y_sell_1 = y_sell_1.astype(int)
        y_buy_1 = y_buy_1.astype(int)
        y_sell_2 = y_sell_2.astype(int)
        y_buy_2 = y_buy_2.astype(int)
        self.labelListSell1 = np.sort(np.unique(y_sell_1))
        self.labelListSell2 = np.sort(np.unique(y_sell_2))
        self.labelListBuy1 = np.sort(np.unique(y_buy_1))
        self.labelListBuy2 = np.sort(np.unique(y_buy_2))
        engine.printLog(f"   labelListSell1: {self.labelListSell1}")
        engine.printLog(f"   labelListSell2: {self.labelListSell2}")
        engine.printLog(f"   labelListBuy1: {self.labelListBuy1}")
        engine.printLog(f"   labelListBuy2: {self.labelListBuy2}")

        self.classifierSell_1 = self.__createClassifier(x,y_sell_1,useSVM=useSVM)
        self.classifierSell_2 = self.__createClassifier(x,y_sell_2,useSVM=useSVM)
        self.classifierBuy_1 = self.__createClassifier(x,y_buy_1,useSVM=useSVM)
        self.classifierBuy_2 = self.__createClassifier(x,y_buy_2,useSVM=useSVM)

        elapsed = (timeit.default_timer() - start)
        engine.printLog(f"build PredictModel finished! elapsed = %.3fs" % (elapsed),True)
        pass

    def __createClassifier(self,x,y,useSVM=True):
        classifier = None
        if useSVM:
            classifier = sklearn.svm.SVC(C=2, kernel='rbf', gamma=10, decision_function_shape='ovr', probability=True)  # ovr:一对多策略
            classifier.fit(x, y)
        else:
            classifier = RandomForestClassifier(n_estimators=100, max_depth=None,min_samples_split=50, bootstrap=True)
            classifier.fit(x, y)
        return classifier

    def buldRangeList(self,label_list:[],probal_list:[]):
        fillList = []
        for index in range(0, len(probal_list)):
            encode = label_list[index]
            floatRange = FloatRange(encode=encode, probal=probal_list[index])
            fillList.append(floatRange)
        return fillList

    def predict(self, data: Union[CollectData, Sequence['CollectData']]) -> Union[PredictData, Sequence['PredictData']]:
        single = False
        engine = self.engine
        if type(data) is CollectData:
            data = [data]
            single = True
        if type(data) is list:
            x, y_sell_1,y_buy_1,y_sell_2,y_buy_2 = engine.getEngineModel().generateFeature(engine, data)
            retList = []
            buyRange1_probal_list = self.classifierBuy_1.predict_proba(x)
            buyRange2_probal_list = self.classifierBuy_2.predict_proba(x)
            sellRange1_probal_list = self.classifierSell_1.predict_proba(x)
            sellRange2_probal_list = self.classifierSell_2.predict_proba(x)
            for i in range(0,len(data)):
                collectData = data[i]
                pData = PredictData(dimen=self.dimen, quantData=self.quantData, collectData=collectData)
                floatSellRangeList1 = self.buldRangeList(self.labelListSell1,sellRange1_probal_list[i])
                floatBuyRangeList1 = self.buldRangeList(self.labelListBuy1,buyRange1_probal_list[i])
                floatSellRangeList2 = self.buldRangeList(self.labelListSell2,sellRange2_probal_list[i])
                floatBuyRangeList2 = self.buldRangeList(self.labelListBuy2,buyRange2_probal_list[i])

                pData.buyRange1 = FloatRange.sort(floatBuyRangeList1)
                pData.buyRange2 = FloatRange.sort(floatBuyRangeList2)
                pData.sellRange1 = FloatRange.sort(floatSellRangeList1)
                pData.sellRange2 = FloatRange.sort(floatSellRangeList2)
                retList.append(pData)
            if single:
                return retList[-1]
            else:
                return retList
        raise RuntimeError("unsupport data！！！")

    def predictResult(self, predict: PredictData) -> Union[bool, bool]:
        order = self.engine.getEngineModel().generatePredictOrder(self.engine,predict)
        high_price = -99999999
        low_price = -high_price
        for bar in predict.collectData.predictBars:
            high_price = max(high_price,bar.high_price)
            low_price = min(low_price, bar.low_price)

        ## 预测价格有无到底最高价格
        sell_ok = high_price>=order.suggestSellPrice
        buy_ok = low_price <= order.suggestBuyPrice
        return sell_ok,buy_ok

    def testScore(self,trainSampleDataList:[]) -> Tuple[float, float]:
        self.engine.printLog("start PredictModel.selfTest()",True)
        predictList: Sequence['PredictData'] = self.predict(trainSampleDataList)
        count = len(predictList);
        if count < 0:
            return
        sellOk = 0
        buyOk = 0
        for predict in predictList:
            sell_ok, buy_ok = self.predictResult(predict)
            if sell_ok:
                sellOk +=1
            if buy_ok:
                buyOk +=1
        sell_core = sellOk / count
        buy_core = buyOk / count
        self.engine.printLog("selfTest : sell_core=%.2f, buy_core=%.2f" % (sell_core * 100,buy_core * 100),True)
        return sell_core,buy_core




class CoreEngineImpl(CoreEngine):

    COLLECT_DATA_FILE_NAME = "colllect"
    ##量化数据的涨幅分布区域。
    quantFloatEncoder = FloatEncoder([-7, -4.5, -3, -1.5, 0, 1.5, 3, 4.5, 7])

    def __init__(self, dirPath: str):
        self.mAllDimension:['Dimension'] = None
        self.mQuantDataMap:{}= None
        self.mAbilityMap:{} = None
        self.__file_dir = dirPath
        self.__model = None
        self.enableLog = False

        if not os.path.exists(dirPath):
            os.makedirs(dirPath)
        collectDir = self.__getCollectDirPath()
        if not os.path.exists(collectDir):
            os.makedirs(collectDir)
        modelDir = self.__getModelDirPath()
        if not os.path.exists(modelDir):
            os.makedirs(modelDir)


    def printLog(self,info:str,forcePrint = False):
        if self.enableLog or forcePrint:
            print(f"[CoreEngineImpl]: {info}")

    def __getDimenisonFilePath(self):
        return f"{self.__file_dir}/dimension.bin"

    def __getCollectDirPath(self):
        return  f"{self.__file_dir}/colllect"

    def __getModelDirPath(self):
        return  f"{self.__file_dir}/model"

    def __getQuantFilePath(self):
        return f"{self.__file_dir}/quantData.bin"

    def __getAbilityFilePath(self):
        return f"{self.__file_dir}/abilityData.bin"

    def __getCollectFilePath(self,dimen:Dimension):
        dirPath =  f"{self.__getCollectDirPath()}/{dimen.getKey()}"
        return dirPath
    def __getModelFilePath(self,dimen:Dimension):
        dirPath =  f"{self.__getModelDirPath()}/{dimen.getKey()}"
        return dirPath


    def load(self, model:CoreEngineModel):
        self.__model = model
        self.printLog("load() start...",True)
        with open(self.__getDimenisonFilePath(), 'rb') as fp:
            self.mAllDimension  = pickle.load(fp)
        with open(self.__getQuantFilePath(), 'rb') as fp:
            self.mQuantDataMap = pickle.load(fp)
        with open(self.__getAbilityFilePath(), 'rb') as fp:
            self.mAbilityMap = pickle.load(fp)

        self.printLog(f"load() finished,总共加载{len(self.mAllDimension)}个维度数据",True)
        assert len(self.mQuantDataMap) == len(self.mAllDimension)

    def build(self, soruce: BarDataSource, model: CoreEngineModel,split_rate = 0.7,limit_dimen_size = -1):
        self.printLog("build() start...", True)
        self.__model = model
        # collector.onCreate()
        bars, code = soruce.onNextBars()
        dataSet = {}
        totalCount = 0
        while not bars is None:
            finished, stop = CoreEngineModel.collectBars(bars, code, model)
            self.printLog(f"collect code:{code}, finished:{len(finished)},stop:{len(stop)}")
            totalCount += len(finished)
            bars, code = soruce.onNextBars()
            for data in finished:
                ##收录
                listData: [] = dataSet.get(data.dimen)
                if listData is None:
                    listData = []
                    dataSet[data.dimen] = listData
                listData.append(data)

        dimes = dataSet.keys()
        self.printLog(f"总共收集到{totalCount}数据，维度个数:{len(dimes)}",True)

        MIN_SIZE = 300
        fitlerDataSet = {}
        __the_count = 0
        for dimen, listData in dataSet.items():
            if limit_dimen_size > 0 and limit_dimen_size <= __the_count:
                ##限制个数
                break
            size = len(listData)
            if size >= MIN_SIZE:
                __the_count +=1
                fitlerDataSet[dimen] = listData

        dataSet = fitlerDataSet
        self.__saveDimeenAndQuantData(dataSet)
        self.__buildAndSaveModelData(split_rate)
        self.printLog(f"创建模型完成",True)

        self.load(model)

    def __saveDimeenAndQuantData(self,dataSet:{}):
        self.printLog(f"开始保存数据",True)
        saveDimens = []
        saveCollectCount = 0
        maxSize = 0
        minSize = 9999999999
        quantMap = {}
        for dimen, listData in dataSet.items():
            size = len(listData)
            quantData = self.computeQuantData(listData)
            quantMap[dimen] = quantData
            maxSize = max(maxSize, size)
            minSize = min(minSize, size)
            saveDimens.append(dimen)
            saveCollectCount += size
            filePath = self.__getCollectFilePath(dimen)
            with open(filePath, 'wb+') as fp:
                pickle.dump(listData, fp, -1)

        with open(self.__getDimenisonFilePath(), 'wb+') as fp:
            pickle.dump(saveDimens, fp, -1)

        with open(self.__getQuantFilePath(), 'wb+') as fp:
            pickle.dump(quantMap, fp, -1)
        self.mAllDimension = saveDimens
        self.mQuantDataMap = quantMap
        self.printLog(
            f"build() finished, 总共保存{len(saveDimens)}/{len(dataSet)}个维度数据，共{saveCollectCount}个数据，其中最多{maxSize},最小{minSize}",
            True)

    def __buildAndSaveModelData(self,split_rate:float):

        dimen_list:Sequence['Dimension'] = []
        with open(self.__getDimenisonFilePath(), 'rb') as fp:
            dimen_list = pickle.load(fp)

        abilityDataMap = {}
        count = len(dimen_list)
        run_count = 0
        for dimen in dimen_list:
            run_count +=1
            self.printLog(f"正在计算并保存模型数据：dime={dimen},progress={run_count}/{count}", True)
            dataList = self.loadCollectData(dimen)
            size = len(dataList)
            trainSize = int( size* split_rate)
            trainDataList:Sequence['CollectData'] = []
            testDataList:Sequence['CollectData'] = []
            split_date = None

            #quant_list = sorted(quant_list, key=cmp_to_key(com_quant), reverse=True)

            for i in range(0,size):
                data = dataList[i]
                if i < trainSize:
                    trainDataList.append(data)
                elif i == trainSize:
                    testDataList.append(data)
                    split_date = data.occurBars[-1].datetime
                else:
                    testDataList.append(data)
                    ##确保切割的时间顺序
                    #assert  data.occurBars[-1].datetime >= split_date
            ablityData = self.__buildModelAbility(dimen, trainDataList, testDataList)
            abilityDataMap[dimen] = ablityData
            ##保存模型
            model = SVMPredictModel(self, dimen)
            model.build(self, dataList, self.mQuantDataMap[dimen])
            model.save(self.__getModelFilePath(dimen))

        ##saveAbliitTy
        with open(self.__getAbilityFilePath(), 'wb+') as fp:
            pickle.dump(abilityDataMap, fp, -1)
        pass
    def __buildModelAbility(self, dimen:Dimension, trainDataList:Sequence['CollectData'], testDataList:Sequence['CollectData']):
        self.printLog("buildAbilityData:", True)
        trainQauntData = self.computeQuantData(trainDataList)
        model = SVMPredictModel(self, dimen)
        model.build(self, trainDataList,trainQauntData)
        sell_score_train, buy_score_train=  model.testScore(trainDataList)  ##训练集验证分数
        sell_score_test, buy_score_test=  model.testScore(testDataList)  ##训练集验证分数

        abilityData = PredictAbilityData()
        abilityData.count_train = len(trainDataList)
        abilityData.sell_score_train = sell_score_train
        abilityData.buy_score_train = buy_score_train
        abilityData.count_test = len(testDataList)
        abilityData.sell_score_test = sell_score_test
        abilityData.buy_score_test = buy_score_test
        return abilityData


    def loadCollectData(self, dimen: Dimension) -> Sequence['CollectData']:
        filePath = self.__getCollectFilePath(dimen)
        collectData = None
        with open(filePath, 'rb') as fp:
            collectData = pickle.load(fp)
        return collectData

    def getEngineModel(self) ->CoreEngineModel:
        return self.__model

    def computeQuantData(self, dataList: Sequence['CollectData']) -> QuantData:
        return self.__computeQuantData(CoreEngineImpl.quantFloatEncoder,CoreEngineImpl.quantFloatEncoder,dataList)

    """
        计算编码分区最佳的QuantData
        """
    def __findCenterPct(self,pct_list, min_pct,max_pct,best_pct,best_probal) -> Union[float, float]:
        if max_pct - min_pct < 0.01:
            return best_pct, best_probal

        pct = (max_pct + min_pct) / 2
        encoder = FloatEncoder([pct])
        flaotRangeList = self.__computeRangeFloatList(pct_list, encoder,False)
        probal = flaotRangeList[0].probal

        if abs(probal - 0.5) < abs(best_probal - 0.5):
            best_pct = pct
            best_probal = probal

        if probal > 0.5:
            ##说明pct值过大
            pct2,probal2 = self.__findCenterPct(pct_list,min_pct,pct,best_pct,best_probal)
        else:
            pct2,probal2 = self.__findCenterPct(pct_list,pct,max_pct,best_pct,best_probal)

        if abs(probal2 - 0.5) < abs(best_probal - 0.5):
            best_pct = pct2
            best_probal = probal2

        return best_pct,best_probal

    """
    计算编码分区最佳的QuantData
    """
    def __findBestFloatEncoder(self,pct_list:[],originEncoder:FloatEncoder)->Union[FloatEncoder,Sequence['FloatRange']]:
        SCALE = 5000
        min,max = originEncoder.parseEncode(int(originEncoder.mask()/2))
        min = int(min * SCALE)
        max = int(max * SCALE)
        step = int((max - min) / 100)

        bestProbal = 0
        bestEncoder = originEncoder
        bestRnageList = None
        for shift in range(min,max,step):
            d = shift / SCALE
            encoder = originEncoder.shift(d)
            flaotRangeList = self.__computeRangeFloatList(pct_list, encoder)
            probal = flaotRangeList[0].probal
            if probal > bestProbal:
                bestProbal = probal
                bestEncoder = encoder
                bestRnageList = flaotRangeList

        return bestEncoder,bestRnageList

    def __computeRangeFloatList(self,pct_list:[],encoder:FloatEncoder,sort = True)->Sequence['FloatRange']:
        rangeCount = {}
        totalCount = len(pct_list)
        for i in range(0, encoder.mask()):
            rangeCount[i] = 0
        for pct in pct_list:
            encode = encoder.encode(pct)
            rangeCount[encode] +=1

        rangeList = []
        for encode, count in rangeCount.items():
            probal = 0.0
            if totalCount > 0:
                probal = count / totalCount
            floatRange = FloatRange(encode=encode, probal=probal)
            rangeList.append(floatRange)
        if sort:
            return FloatRange.sort(rangeList)
        return rangeList

    def __computeQuantData(self,sellEncoder:FloatEncoder,buyEncoder:FloatEncoder,dataList: Sequence['CollectData']):

        sell_pct_list = []
        buy_pct_list = []
        totalCount = len(dataList)
        for data in dataList:
            bars: ['BarData'] = data.predictBars
            assert len(bars) > 0
            sell_pct, buy_pct = self.getEngineModel().getSellBuyPctLabel(data)
            sell_pct_list.append(sell_pct)
            buy_pct_list.append(buy_pct)
        sellEncoder,sellRangeFloat = self.__findBestFloatEncoder(sell_pct_list,sellEncoder)
        buyEncoder,buyRangeFloat = self.__findBestFloatEncoder(buy_pct_list,buyEncoder)

        sell_center_pct, best_probal1 = self.__findCenterPct(sell_pct_list,sellEncoder.splits[0],sellEncoder.splits[-1],0.0,0.0)
        buy_center_pct, best_probal2 = self.__findCenterPct(buy_pct_list,buyEncoder.splits[0],buyEncoder.splits[-1],0.0,0.0)
        return QuantData(count=totalCount,sellRange=sellRangeFloat,buyRange=buyRangeFloat,
                         sellCenterPct=sell_center_pct,
                         buyCenterPct=buy_center_pct,
                         sellSplits=sellEncoder.splits,buySplits=buyEncoder.splits)


    def collect(self, bars: ['BarData']) -> Tuple[Sequence['CollectData'], Sequence['CollectData']]:
        collector = self.__model
        #collector.onCreate()
        code = bars[0].symbol
        finished, stop = CoreEngineModel.collectBars(bars, code, collector)
        return finished,stop

    def loadAllDimesion(self) -> Sequence['Dimension']:
        return self.mAllDimension

    def queryQuantData(self, dimen: Dimension) -> QuantData:
        return self.mQuantDataMap.get(dimen)

    def queryPredictAbilityData(self, dimen: Dimension) -> PredictAbilityData:
        return self.mAbilityMap.get(dimen)

    def loadPredictModel(self, dimen: Dimension) -> PredictModel:
        try:
            model = SVMPredictModel(self,dimen)
            model.load(self.__getModelFilePath(dimen))
            return model
        except FileNotFoundError:
            return None
        except BaseException:
            return None


    def printTopDimension(self,pow_rate_limit = 1.0):


        def com_quant(q1, q2):
            return q1.getPowerRate() - q2.getPowerRate()

        print(f"做多Top列表")
        dimeValues = []
        quant_list = []
        for dimen in dimens:
            quant = engine.queryQuantData(dimen)
            if quant.getPowerRate() >= pow_rate_limit:
                quant_list.append(quant)
                dimeValues.append(dimen.value)
        quant_list = sorted(quant_list, key=cmp_to_key(com_quant), reverse=True)
        for i in range(0,len(quant_list)):
            quant = quant_list[i]
            encoder = quant.getSellFloatEncoder()
            _min,_max = encoder.parseEncode(quant.sellRange[0].encode)
            print(f"[dime:{dimeValues[i]}]: count={quant.count},pow_rate=%.3f, probal=%.2f%%,centerPct=%.2f,sell:[{_min},{_max}]" % (quant.getPowerRate(), quant.getPowerProbal(True), quant.sellCenterPct))
        print(f"top dimeValues: {dimeValues}")

        print(f"做空Top列表")
        dimeValues = []
        quant_list = []
        for dimen in dimens:
            quant = engine.queryQuantData(dimen)
            if quant.getPowerRate() <= -pow_rate_limit:
                quant_list.append(quant)
                dimeValues.append(dimen.value)
        quant_list = sorted(quant_list, key=cmp_to_key(com_quant), reverse=False)
        for i in range(0,len(quant_list)):
            quant = quant_list[i]
            encoder = quant.getBuyFloatEncoder()
            _min, _max = encoder.parseEncode(quant.buyRange[0].encode)
            print(f"[dime:{dimeValues[i]}]: count={quant.count},pow_rate=%.3f, probal=%.2f%%,centerPct=%.2f,buy:[{_min},{_max}]" % (quant.getPowerRate(), quant.getPowerProbal(False), quant.buyCenterPct))
        print(f"top dimeValues: {dimeValues}")



if __name__ == "__main__":
    from earnmi.model.EngineModel2KAlgo1 import EngineModel2KAlgo1

    engineModel = EngineModel2KAlgo1()


    start = datetime(2014, 5, 1)
    end = datetime(2018, 5, 17)
    engine = CoreEngineImpl("files/impltest")
    #engine.enableLog = True

    #engine.build(SWDataSource(start,end), engineModel)
    engine.load(engineModel)
    dimens = engine.loadAllDimesion()
    print(f"dimension：{dimens}")

    testDateSource = SWDataSource(end,datetime(2019, 5, 17))

    # ablityDataMap = engine.buildAbilityData(testDateSource)
    #
    print(f"\n ability list:")
    for dimen in dimens:
        abilityData = engine.queryPredictAbilityData(dimen)
        print(f"dimen:{dimen} => {abilityData}")


    dist_list = []
    #engine.printTopDimension()



    pass
