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
from config import config
import time


START_ADDRESS = 0x0100
METER_ADDRESS = "255.255.255.255" ##"6.0.7.40"

# def program(filepath, flash_io, flash_sector):
#     binary_file = open(filepath, "rb")
#     block = binary_file.read()
#     hexfile_payload = bytearray()
#     for ch in block:
#         hexfile_payload.append(ch)

#     if flash_sector == 151:
#         flash_io.erase(Address(METER_ADDRESS), 0)
#         # flash_io.erase(Address("255.255.255.255"), 1)
#         # flash_io.erase(Address("255.255.255.255"), 2)
#         # flash_io.erase(Address("255.255.255.255"), 3)
#         # Here we have to do erase sector command
#     else:

#         flash_io.erase(Address(METER_ADDRESS), 0, sector_erase = True)
#     flash_io.burn(Address(METER_ADDRESS), START_ADDRESS, hexfile_payload, to_print=True)

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', action="store", dest="device", 
                        type=str, help="device name, eg. /dev/ttyUSB0")
    parser.add_argument('-b', action="store", dest="baud_rate", 
                        type=str, help="baud rate")
    parser.add_argument('-p', action="store", dest="hex_file", 
                        help="programs new hex file")
    parser.add_argument('-V', action="store", dest="version", 
                        help="options are 'live' and 'ext'")
    parser.add_argument('-t', action="store", dest="timeout",type=int, 
                        help="port time out")
    parser.add_argument("--id",action="store", dest="portID",
                      help="device id")
    parser.add_argument("--sector", action="store", dest="sectorId",type=int,
                      help="Image Transfer of particular sector")
    
    args = parser.parse_args()
    if args.device is None:
        args.device = "COM8"
    if args.baud_rate is None:
        args.baud_rate = 9600
    if args.timeout is None:
        args.timeout = 3
    if args.portID is None:
        args.portID = 19
    if args.sectorId is None:
        args.sectorId = 151

    ser = serial.Serial(args.device, args.baud_rate, timeout=args.timeout)

    network_api = NetworkAPI(ser, args.portID, "irda")
    starttime = datetime.datetime.now()

    cfg = config()
    cfg.verify_config_json()
    is_excel_file_present = True
    #Meter type selection done---------------------------------------------
    bookName = "INSTANTANEOUS_DATA_LOG.xlsx"
    fileName = "INSTANTANEOUS_DATA_LOG"
    mac = "NA"
    Parse_Only = 0xABCE
    result = ["voltage","phase_current","neutral_current","active_power","apparent_power","reactive_power","frequency","power_factor","battery_voltage",\
                  "active_energy_imp","active_energy_exp","apparent_energy_imp","apparent_energy_exp","reactive_energy_imp","reactive_energy_exp",\
                  "activeHr_energy_imp","activeHr_energy_exp","apparentHr_energy_imp","apparentHr_energy_exp","reactiveHr_energy_imp","reactiveHr_energy_exp","Temprature"]
    
    addDefaultMriLog(cfg,bookName,fileName,result)
    interval = int(input("Please enter time interval in sec. : "))
    while(1):
        MeterInfo = []
        final_result = []
        print("Sending command for metering data")
        
        try:
            LV = network_api.get_1p_metering_data(Address(METER_ADDRESS),Parse_Only)
            print("Data Recieved")
            for i in range((len(result) - 1)):
                MeterInfo.append(LV.return_params[result[i]])
            DateTime = datetime.datetime.now()
            try:
                temp = network_api.get_1p_metering_data2(Address(METER_ADDRESS),Parse_Only)
                print("Temperature",temp.return_params["Temprature"])
                MeterInfo.append(temp.return_params["Temprature"])
            except:
                MeterInfo.append(0)    
            final_result.append(DateTime)
            cfg.add_log_xlsc(mac,final_result,MeterInfo,bookName,fileName)   
        except Exception as e:
            print(e)

        time.sleep(interval) 


def addDefaultMriLog(cfg,bookName,fileName,result):
    if False == cfg.verify_log_xlsc(bookName,fileName):
        print("xlsx file for log not found. creating one to store test report")
        mac = "MAC_ADDR"
        MeterInfo = ["Index","DATA Timestamp"] 
        #,"MTR_ADDRESS","NET_CHAN","LIVE_VER",\    
        cfg.add_log_xlsc(mac,MeterInfo,result,bookName,fileName)


if __name__ == "__main__":
    run()
