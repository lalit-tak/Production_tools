import os
import argparse
from gp_node.network.network_api import NetworkAPI
from gp_node.network.protocols.common.tap import TAPHandler, TAPPacket, TAPError
from gp_node.network.protocols._1p.flash_io import FlashIOMaster, FlashIOError
from gp_node.utils.address import Address
import serial
import gp_node.utils.serialize as serialize
import json
import datetime
import time


# START_ADDRESS = 0xAC000
METER_ADDRESS = "255.255.255.255"
"""
This is purely for debugging purpose
Create ext_flash.bin binary file by reading external flash firmware image
"""
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
        args.device = "COM1"
    if args.baud_rate is None:
        args.baud_rate = 9600
    if args.timeout is None:
        args.timeout = 3
    if args.portID is None:
        args.portID = 4
    if args.sectorId is None:
        args.sectorId = 151

    ser = serial.Serial(args.device, args.baud_rate, timeout=args.timeout)

    network_api = NetworkAPI(ser, args.portID, "irda")
    data = bytearray()
    #data = network_api.my_flash_io_master.fetch(Address("0.0.0.255"), START_ADDRESS, 128)
    #print "Header :", data
    """
    TODO: get binary file length from header rather than manually updating...????
    """
    # bin_file_length = 146240
    starttime = datetime.datetime.now()
    network_api.enable_print_rxtx(Address(METER_ADDRESS))
    freq_data = []
    read_data_flag = 0xFFFFFFFF
    tot_retries = 3

    while read_data_flag >= 0 and tot_retries > 0:
        try:
            if read_data_flag == 0xFFFFFFFF:
                data = network_api.get_num_metering_record(Address(METER_ADDRESS))
                print ("No of Entries found: ", data)
                if data == 0:
                    print ("NO Entries found...")
                    read_data_flag = data
                else:
                    read_data_flag = data-1

                if read_data_flag >= 640:
                    read_data_flag = 640-1
                freq_data.append("NO data found")

            data = network_api.get_metering_record_by_index(Address(METER_ADDRESS), read_data_flag)
            for i in range(0,32):
                freq_value = ((data[i*2]) + (data[(i*2)+1]<<8))/100.0
                freq_data.append(freq_value)

            read_data_flag = read_data_flag-1
            tot_retries = 3
        except:
            print ("Retries")
            tot_retries = tot_retries-1
            time.sleep(1)
        print ("read_data_flag : ", read_data_flag)
    print ("All Data Recieved")
    # print "Recieved Data is :", data
    # open file
    with open('Freq_Samples.txt', 'w') as outfile:
         
        outfile.write(', '.join(str(i) for i in freq_data))
         
        print("File written successfully")
     
     
    # close the file
    outfile.close()

    tot_retries = 3
    while(tot_retries):
        try:
            network_api.clear_metering_record(Address(METER_ADDRESS))
            print ("Record resets to meter")
            tot_retries = 0
        except:
            tot_retries -= 1


    EndTime = datetime.datetime.now()
    print ("StartTime:",starttime)
    print ("EndTime:",EndTime)

    print ("Diff:",EndTime-starttime)
if __name__ == "__main__":
    run()
