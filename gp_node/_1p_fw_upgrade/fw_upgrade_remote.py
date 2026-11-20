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

def program(filepath, flash_io, dest_addr):
    flash_io.erase(Address(dest_addr), 0)
    # flash_io.erase(Address("255.255.255.255"), 1)
    # flash_io.erase(Address("255.255.255.255"), 2)
    # flash_io.erase(Address("255.255.255.255"), 3)
    # Here we have to do erase sector command
    binary_file = open(filepath, "rb")
    block = binary_file.read()
    hexfile_payload = bytearray()
    for ch in block:
        hexfile_payload.append(ch)
    flash_io.burn(Address(dest_addr), START_ADDRESS, hexfile_payload, to_print=True)

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
    parser.add_argument("--id", "--portID", dest="portID",
                      help="device id")
    parser.add_argument('-a', action="store", dest="dest_addr", 
                        help="contain meter address")
    
    args = parser.parse_args()
    if args.device is None:
        args.device = "/dev/gp-gateway"
    if args.baud_rate is None:
        args.baud_rate = 9600
    if args.timeout is None:
        args.timeout = 3
    if args.portID is None:
        args.portID = 4
    if args.dest_addr is None:
        args.dest_addr = "0.0.0.0"
        print ("Meter_address : ", args.dest_addr)
        return "Please Enter Meter address e.g : -a \"1.2.3.4 \" "


    ser = serial.Serial(args.device, args.baud_rate, timeout=args.timeout)

    network_api = NetworkAPI(ser, args.portID, "irda")
    starttime = datetime.datetime.now()
    if args.hex_file is not None:
        print ("Erasing...")
        program(args.hex_file, network_api.my_flash_io_master_new, args.dest_addr)
    if args.version == "live":
        print (network_api.get_live_version(Address(args.dest_addr)))
    if args.version == "ext":
        print (network_api.get_ext_version(Address(args.dest_addr)))
        
    EndTime = datetime.datetime.now()
    print ("\nStartTime:",starttime)
    print ("EndTime:",EndTime)
    print ("Diff : ", EndTime - starttime)


if __name__ == "__main__":
    run()
