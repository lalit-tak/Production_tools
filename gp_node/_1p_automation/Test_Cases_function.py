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
import threading
from threading import Thread 
import time
import socket
import paho.mqtt.client as mqtt
import datetime
import signal
import sys
import os
from config import config
from Test_cases_verificationClass import TestCasePCTMCT
import easygui


START_ADDRESS = 0x0100
METER_ADDRESS = "255.255.255.255" ##"6.0.7.40"
DCU_NUMBER_Ver = 0


class CasesThread(Thread):
    def __init__(self,ser,portID,dcu_number): 
        Thread.__init__(self) 
        self.portID = portID 
        self.ser = ser
        self.dcu_number = dcu_number
        

    def run(self):
    
    #     network_api = NetworkAPI(self.ser, self.portID, "irda")
        starttime = datetime.datetime.now()
    #     print "In class cases thread"

    # # live_version = network_api.get_live_version(Address(METER_ADDRESS))
    # # print "type", type(live_version)
    # # print live_version

    #     try:
    #         SetTime = network_api.set_dcu_time(Address(METER_ADDRESS), "now")
    #         print "type", type(SetTime)
    #         print 'set_dcu_time',SetTime

    #         GetTime = network_api.get_dcu_time(Address(METER_ADDRESS))
    #         print "type", type(GetTime)
    #         print 'get_dcu_time',GetTime

    #         GetTimeM = network_api.get_time(Address(METER_ADDRESS))
    #         print "type", type(GetTimeM)
    #         print 'get_time',GetTimeM
    #     except Exception as e:
    #         print "type", type(e)
    #         print e

    # try:
    #     index_val = input("Set dcu Number : ")
    #     address = network_api.set_dcu_number(Address(METER_ADDRESS),index_val)
    #     print "type", type(address)
    #     print address
    # except Exception as e:
    #     print "type", type(e)
    #     print e

    # try:
    #     # index_val = input("Set dcu Number : ")
    #     dcuParams = network_api.get_dcu_intervals(Address(METER_ADDRESS),isReturn=True)
    #     print "type", type(dcuParams),len(dcuParams)
    #     # print dcuParams
    #     DCU_NUMBER_Ver = int(dcuParams[0][0]['DCU_NUMBER'])
    #     print dcuParams[0][0]['DCU_NUMBER']
    # except Exception as e:
    #     print "type", type(e)
    #     print e  

    # try:  
    #     dcuTopics = network_api.get_dcu_topics(Address(METER_ADDRESS),isReturn=True)
    #     print "type", type(dcuTopics),len(dcuTopics)
    #     print dcuTopics,
    # except Exception as e:
    #     print "type", type(e)
    #     print e  

    # print '\nDCU_NUMBER_Ver',DCU_NUMBER_Ver 
    # ovrMqtt = OverMQTT(args.device,DCU_NUMBER_Ver)
    # ovrMqtt.run()    
    # # if "BATTERY_FAIL" in address:
    # #     print "battery not ok"

    # # if args.hex_file is not None:
    # #     # print "Erasing..."
    # #     # program(args.hex_file, network_api.my_flash_io_master_new, args.sectorId)
    # #     print network_api.get_ext_version(Address(METER_ADDRESS))

    # # # metering_data = MeteringDataPacket()
    # # metering_data = network_api.get_1p_metering_data(Address(METER_ADDRESS))
    # # print "type", type(metering_data)
    # # print metering_data
    # # print "type", type(metering_data.return_params["voltage"])
    # # print metering_data.return_params["voltage"]
    # # print "type", type(metering_data.return_params["factory_init_time"])
    # # print metering_data.return_params["factory_init_time"]
    # # print metering_data.get_nxp_ene_debug_packet()
    # # print "type", type(metering_data.return_params["active_energy_imp"])
    # # print metering_data.return_params["active_energy_imp"]

    # # #get_block_load_index:1
    # # index_val = input("Enter block load fetch index : ")
    # # index_bl = network_api.get_block_load_profile_by_index(Address(METER_ADDRESS), 1)
    # # print "type", type(index_bl)
    # # print index_bl
    # # print "type", type(index_bl.voltage)
    # # print index_bl.voltage
        cfg = config()
        cfg.verify_config_json()
        cases = TestCasePCTMCT(self.ser,self.portID,cfg)

        serial_num = 0 # Initialization of meter serial number 
        address = 0 # Initialization of 
        is_excel_file_present = True
        meter_type = "DCU_"
        TOOL_TYPE = cfg.TOOL_TYPE
        print ("TOOL_TYPE",TOOL_TYPE)
        #Meter type selection done---------------------------------------------
        bookName = meter_type+"_"+TOOL_TYPE+"_LOG.xlsx"
        fileName = TOOL_TYPE+"_DATA_LOG"
        toolName = str(meter_type)
        toolName += str(TOOL_TYPE)
        toolName += "  || GRAMPOWER ||"
        cfg.is_excel_present()

        mac = cfg.get_system_mac_address()    
        for k in range(1):
            os.system('cls' if os.name == 'nt' else 'clear')
            displayDashboard(TOOL_TYPE)
            displayList = "NONE"
            print ("\nSystem setup completed\n")
            result_list = []
            MeterInfo = []
            TOPIC_TEST = []
            case_for_RF = "\n"
            message = []
            serial_num = self.dcu_number
            MeterInfo.append(serial_num) 
            if(("MRI" == TOOL_TYPE) or ("MCT" == TOOL_TYPE)):
                addDefaultMriLog(cfg,bookName,fileName)
                MCT_Fail_list = ["Fail in Verify DCU time","Fail in Verify Meter Time"]
                result_list.append(cases.Verify_dcu_time_val()) 
                result_list.append(cases.Verify_meter_time_val())
                
            elif("PCT" == TOOL_TYPE):
                addDefaultPCTLog(cfg,bookName,fileName)
                PCT_Fail_list = ["Fail In Set DCU Time","Fail in Verify DCU Time","Fail in Set DCU number","Fail in Verify DCU number","Fail in Verify Collection Topic","Fail in Verify data Pushing topic","Fail in Verify Remote command Topic","Fail in DCU factory reset"]
                result_list.append(cases.Set_dcu_time_val())
                result_list.append(cases.Verify_dcu_time_val()) 
                result_list.append(cases.Set_dcu_number_val(int(serial_num)))
                result_list.append(cases.Verify_dcu_number_val(int(serial_num)))
                Return_result = []
                Return_result.append(cases.Verify_dcu_topics_val())
                return_dict = {}
                return_dict['Result'] = Return_result[0]['ResultC']
                return_dict['Retries'] = Return_result[0]['RetriesC']
                result_list.append(return_dict)
                return_dict = {}
                return_dict['Result'] = Return_result[0]['ResultP']
                return_dict['Retries'] = Return_result[0]['RetriesP']
                result_list.append(return_dict)
                return_dict = {}
                return_dict['Result'] = Return_result[0]['ResultR']
                return_dict['Retries'] = Return_result[0]['RetriesR']
                result_list.append(return_dict)
                result_list.append(cases.DCU_Factory_reset_val())

                
            final_result = []
            ResultFinal = []
            FailResult = []
            for j in range(len(result_list)):
                # print "final_response",result_list[j]
                final_result.append(result_list[j]["Result"])
                final_result.append(result_list[j]["Retries"])
                if result_list[j]["Result"] == 'Fail':
                    ResultFinal.append('Fail')
                    if (len(result_list) == 2):
                        FailResult.append(MCT_Fail_list[j])
                    else:
                        FailResult.append(PCT_Fail_list[j])

            if (len(ResultFinal) > 0):
                message.append(ResultFinal[0])
                message.append(FailResult)
                MeterInfo.append(ResultFinal[0])
            else:
                ResultFinal.append('Pass') 
                message = ResultFinal[0]
                MeterInfo.append(ResultFinal[0]) 
  


            
            # if (message[0]=="PASS:"):
            #     MeterInfo.append("PASS")
            # else: 
            #     MeterInfo.append("Failed")    
            cfg.add_log_xlsc(mac,MeterInfo,final_result,bookName,fileName)
            

            

        EndTime = datetime.datetime.now()
        print ("\nStartTime:",starttime)
        print ("EndTime:",EndTime)
        print ("Diff : ", EndTime - starttime)
        easygui.msgbox(message, title=toolName)
        os._exit(0)

    # case = test_case_procedures(cfg, ser)
    # case.load_no_load_test_case() 

def displayDashboard(toolType):    
    print ("****************************************************************")
    print ("****************************************************************")
    print ("\n")
    print (toolType)#METER CUSTOMISATION TOOL V - ", MCT_SOFTWARE_VERSION
    print ("\n")
    print ("****************************************************************")
    print ("****************************************************************")  

def addDefaultMriLog(cfg,bookName,fileName):
    if False == cfg.verify_log_xlsc(bookName,fileName):
        print("xlsx file for log not found. creating one to store test report")
        mac = "MAC_ADDR"
        MeterInfo = ['Index','SERIAL_NUM','OVER ALL RESULT'] 
        # = bytearray()
    
    
        # UID = {'UID1','UID2','UID3','UID4'}
        # result = []
        result = ["Verify DCU time","Retry","Verify meter time","Retry"]#,"MTR_ADDRESS","NET_CHAN","LIVE_VER",\
        # "SET_TIME_ZONE","UI_DISPLAY_STATUS","LOAD TEST","FACTORY_RESET","RELAY_STATE","PUSHED_INDEX"]
        # print "UID = ",MeterInfo
        # print "Result = ",result
    
        cfg.add_log_xlsc(mac,MeterInfo,result,bookName,fileName)
         # if log file is not present or corrupted 
                                                # than create a new log file
        # cfg.add_index_of_pushed_data(1,bookName,fileName)
    # return "METER CUSTOMIZATION TOOL - (MCT) V - "  

def addDefaultPCTLog(cfg,bookName,fileName):
    if False == cfg.verify_log_xlsc(bookName,fileName):
        print("xlsx file for log not found. creating one to store test report")
        mac = "MAC_ADDR"
        MeterInfo = ['Index','SERIAL_NUM','OVER ALL RESULT'] 
        # = bytearray()
    
    
        # UID = {'UID1','UID2','UID3','UID4'}
        # result = []
        result = ["Set dcu time","Retry","Verify DCU time","Retry","Set dcu Number","Retry","Verify dcu Serial number","Retry","Verify DCU Collection Topic","Retry","Verify DCU Data Pushing Topic","Retry","Verify DCU Remote command Topic","Retry","Do DCU factory reset","Retry"]#,"MTR_ADDRESS","NET_CHAN","LIVE_VER",\
        # "SET_TIME_ZONE","UI_DISPLAY_STATUS","LOAD TEST","FACTORY_RESET","RELAY_STATE","PUSHED_INDEX"]
        # print "UID = ",MeterInfo
        # print "Result = ",result
    
        cfg.add_log_xlsc(mac,MeterInfo,result,bookName,fileName)    
     

        
        # signal.signal(signal.SIGINT, handler)


# if __name__ == "__main__":
#     run()
