import os
import argparse
from gp_node.network.network_api import NetworkAPI
from gp_node.network.protocols.common.tap import TAPHandler, TAPPacket, TAPError
from gp_node.network.protocols._1p.flash_io_dcu import FlashIOMasterDcu, FlashIOErrorDcu
from gp_node.utils.address import Address
import serial
import gp_node.utils.serialize as serialize
import json
import datetime
import time


START_ADDRESS = 0x0100
MAGIC_NUMBER  = 0xDEADBEEF
MAGIC_ADDRESS = 0x41000

def program(filepath, flash_io_dcu):
    erase_block  = False # erase multiple of 0x10000
    erase_sector = True  # erase multiple of 0x1000

    flash_io_dcu.erase(Address("255.255.255.255"), 0, erase_block)  # 0x00000
    flash_io_dcu.erase(Address("255.255.255.255"), 1, erase_block)  # 0x10000
    flash_io_dcu.erase(Address("255.255.255.255"), 2, erase_block)  # 0x20000
    flash_io_dcu.erase(Address("255.255.255.255"), 3, erase_block)  # 0x30000
    flash_io_dcu.erase(Address("255.255.255.255"), 64, erase_sector) # 0x40000
    # Here we have to do erase sector command
    binary_file = open(filepath, "rb")
    block = binary_file.read()
    hexfile_payload = bytearray()
    for ch in block:
        hexfile_payload.append(ch)
    flash_io_dcu.burn(Address("255.255.255.255"), START_ADDRESS, hexfile_payload, to_print=True)
    flash_io_dcu.erase(Address("255.255.255.255"), 65, erase_sector) # 0x41000
    time.sleep(1)
    print ("Write Magic Number")
    magicPck=bytearray([0xEF,0xBE,0xAD,0xDE])
    flash_io_dcu.writeData(Address("255.255.255.255"), start_address = MAGIC_ADDRESS, data = magicPck)
    time.sleep(1)
    print ("Reset dcu")
    reset_data = bytearray([0xEA,0x0F,0x00])
    flash_io_dcu.powerCycle(Address("255.255.255.255"), reset_data, Address("1.78.71.201"))
    # [170, 1, 234, 15, 201, 255, 255, 255, 255, 4, 4, 3, 234, 15, 0, 47, 12]


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
    parser.add_argument('-t', action="store", dest="timeout", type=int,
                        help="port time out")
    parser.add_argument("--id", "--portID", dest="portID",
                      help="device id")
    
    args = parser.parse_args()
    if args.device is None:
        args.device = "/dev/gp-gateway"
    if args.baud_rate is None:
        args.baud_rate = 9600
    if args.timeout is None:
        args.timeout = 5
    if args.portID is None:
        args.portID = 4

    ser = serial.Serial(args.device, args.baud_rate, timeout=args.timeout)

    network_api = NetworkAPI(ser, args.portID, "irda")
    starttime = datetime.datetime.now()
    # print network_api.enable_print_rxtx(Address('255.255.255.255'))
    print (network_api.get_dcu_live_version(Address('255.255.255.255')))
    if args.hex_file is not None:
        print ("Programming...")
        program(args.hex_file, network_api.my_flash_io_master_dcu)
    if args.version == "live":
        print (network_api.get_live_version(Address('255.255.255.255')))
    if args.version == "ext":
        print (network_api.get_ext_version(Address('255.255.255.255')))
        
    EndTime = datetime.datetime.now()
    print ("StartTime:",starttime)
    print ("EndTime:",EndTime)
    print ("Diff : ", EndTime - starttime)


if __name__ == "__main__":
    run()
