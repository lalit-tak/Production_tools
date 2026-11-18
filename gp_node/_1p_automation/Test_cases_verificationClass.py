import os
import argparse
from gp_node.network.network_api import NetworkAPI
from gp_node.network.protocols.common.tap import TAPHandler, TAPPacket, TAPError
from gp_node.network.protocols._1p.flash_io_new import FlashIOMasterNew, FlashIOErrorNew
from gp_node.utils.address import Address

import serial
import gp_node.utils.serialize as serialize
import json
import datetime


START_ADDRESS = 0x0100
METER_ADDRESS = "255.255.255.255" ##"6.0.7.self.Len0"
DCU_NUMBER_Ver = 0

class TestCasePCTMCT():
    def __init__(self,ser,portID,cfg): 
        # Thread.__init__(self) 
        # self.portID = portID 
        self.cfg = cfg
        self.network_api = NetworkAPI(ser, portID, "irda")
        self.Len = cfg.RETRIES
        

    def Set_dcu_time_val(self):
        return_dict = {}
        for i in range(self.Len):
            try:
                SetTime = self.network_api.set_dcu_time(Address(METER_ADDRESS), "now")
                print ("SetTime",SetTime,type(SetTime))
                if SetTime == 'ok':
                    return_dict["Result"] = 'Pass'
                    return_dict["Retries"] = i+1
                    return return_dict
                
            except:
                if ((i+1)==self.Len):
                    return_dict["Result"] = 'Fail'
                    return_dict["Retries"] = i+1
                
        return return_dict

    def Verify_dcu_time_val(self):
        return_dict = {}
        for i in range(self.Len):
            try:
                GetTime = self.network_api.get_dcu_time(Address(METER_ADDRESS))
                print ("GetTime",GetTime,type(GetTime))
                timeDiff = (datetime.datetime.now() - GetTime).total_seconds()
                print ("time Diff",timeDiff)
                if timeDiff >= 0 and timeDiff < 200  :
                    return_dict["Result"] = 'Pass'
                    return_dict["Retries"] = i+1
                    return return_dict
            except:
                if ((i+1)==self.Len):
                    return_dict["Result"] = 'Fail'
                    return_dict["Retries"] = i+1
                
        return return_dict

    def Set_dcu_number_val(self,index_val):
        return_dict = {}
        for i in range(self.Len):
            try:
                Setnum = self.network_api.set_dcu_number(Address(METER_ADDRESS), index_val)
                print ("Setnum",Setnum,type(Setnum))
                if Setnum == 'ok':
                    return_dict["Result"] = 'Pass'
                    return_dict["Retries"] = i+1
                    return return_dict
            except:
                if ((i+1)==self.Len):
                    return_dict["Result"] = 'Fail'
                    return_dict["Retries"] = i+1
                
        return return_dict   

    def Verify_dcu_number_val(self,index_val):
        return_dict = {}
        for i in range(self.Len):
            try:
                dcuParams = self.network_api.get_dcu_intervals(Address(METER_ADDRESS),isReturn=True)
                print ("DCU number",dcuParams[0][0]['DCU_NUMBER'])
                if int(dcuParams[0][0]['DCU_NUMBER']) == int(index_val):
                    return_dict["Result"] = 'Pass'
                    return_dict["Retries"] = i+1
                    return return_dict
    
            except:
                if ((i+1)==self.Len):
                    return_dict["Result"] = 'Fail'
                    return_dict["Retries"] = i+1        
      
        return return_dict    

    def Verify_dcu_topics_val(self):
        return_dict = {}
        dataC = 'vdcuCollectionTPWM'
        DataP = 'vdcuDataPushingTPWM'
        DataR = 'vdcuRCTPWM'
        for i in range(self.Len):
            try:
                dcuTopics = self.network_api.get_dcu_topics(Address(METER_ADDRESS),isReturn=True)
                RDataC = dcuTopics['Data Collection Topic']
                RDataP = dcuTopics['Data Pushing Topic']
                RDataR = dcuTopics['Remote Command Topic']
                if (RDataC.split('\x00')[0] == dataC):
                    return_dict["ResultC"] = 'Pass'
                    return_dict["RetriesC"] = i+1  

                elif (RDataC.split('\x00')[0] != dataC):
                    return_dict["ResultC"] = 'Fail'
                    return_dict["RetriesC"] = i+1        

                if (RDataP.split('\x00')[0] == DataP):
                    return_dict["ResultP"] = 'Pass'
                    return_dict["RetriesP"] = i+1 

                elif (RDataP.split('\x00')[0] != DataP):
                    return_dict["ResultP"] = 'Fail'
                    return_dict["RetriesP"] = i+1    

                if (RDataR.split('\x00')[0] == DataR):
                    return_dict["ResultR"] = 'Pass'
                    return_dict["RetriesR"] = i+1 
                    return return_dict

                elif (RDataR.split('\x00')[0] != DataR):
                    return_dict["ResultR"] = 'Fail'
                    return_dict["RetriesR"] = i+1    

            except:
                if ((i+1)==self.Len):
                    return_dict["ResultC"] = 'Fail'
                    return_dict["RetriesC"] = i+1 
                    return_dict["ResultP"] = 'Fail'
                    return_dict["RetriesP"] = i+1
                    return_dict["ResultR"] = 'Fail'
                    return_dict["RetriesR"] = i+1       
                
        return return_dict

    def Verify_meter_time_val(self):
        return_dict = {}
        for i in range(self.Len):
            try:
                GetTime = self.network_api.get_time(Address(METER_ADDRESS))
                timeDiff = (datetime.datetime.now() - GetTime ).total_seconds()
                print ("time Diff",timeDiff)
                if timeDiff >= -2000 and timeDiff < 2000  :
                    return_dict["Result"] = 'Pass'
                    return_dict["Retries"] = i+1
                    return return_dict
            except:    
                if ((i+1)==self.Len):
                    return_dict["Result"] = 'Fail'
                    return_dict["Retries"] = i+1
                
        return return_dict 

    def DCU_Factory_reset_val(self):
        return_dict = {}
        for i in range(self.Len):
            try:
                FactoryInit = self.network_api.dcu_factory_init_1(Address(METER_ADDRESS))
                print ("FactoryInit",FactoryInit,type(FactoryInit))
                if FactoryInit == 'ok':
                    return_dict["Result"] = 'Pass'
                    return_dict["Retries"] = i+1
                    return return_dict
                
            except:    
                if ((i+1)==self.Len):
                    return_dict["Result"] = 'Fail'
                    return_dict["Retries"] = i+1
                    print ("In else")

        print ("self_Len",self.Len) 
        print ("return_dict",return_dict)        
        return return_dict       

#     