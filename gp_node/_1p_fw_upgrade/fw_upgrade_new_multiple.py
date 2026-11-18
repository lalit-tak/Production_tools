import os
import argparse
from gp_node.network.network_api import NetworkAPI
from gp_node.network.protocols.common.tap import TAPHandler, TAPPacket, TAPError
from gp_node.network.protocols._1p.flash_io_new import FlashIOMasterNew, FlashIOErrorNew
from gp_node.utils.address import Address
import serial
import serial.tools.list_ports
import gp_node.utils.serialize as serialize
import json
import datetime
import time
import threading


def program_thread(com_port, hex_file, portID):
    print(hex_file)
    print (com_port)
    ser = serial.Serial(com_port, baudrate=9600, timeout=3)

    network_api = NetworkAPI(ser, portID, "irda")
    starttime = datetime.datetime.now()
    print ("\nStartTime:",starttime, com_port)

    START_ADDRESS = 0x0100
    METER_ADDRESS = "255.255.255.255"
    packet_size = 128
    
    # network_api.enable_print_rxtx(Address(METER_ADDRESS))
    print (starttime)
    retryCnt = 3
    while (retryCnt):
        try:
            print ("Live Version: ", com_port, network_api.get_live_version(Address(METER_ADDRESS)))
            retryCnt = 0
        except:
            retryCnt = retryCnt-1
            time.sleep(1)
            # if (retryCnt == 0):
            #     exit()

    if hex_file is not None:
        print ("Erasing...")
        binary_file = open(hex_file, "rb")
        block = binary_file.read()
        hexfile_payload = bytearray()
        for ch in block:
            hexfile_payload.append(ch)

        network_api.my_flash_io_master_new.erase(Address(METER_ADDRESS), 0)
        network_api.my_flash_io_master_new.set_packet_size(packet_size)
        network_api.my_flash_io_master_new.burn(Address(METER_ADDRESS), START_ADDRESS, hexfile_payload, to_print=True)

        retryCnt = 3
        while (retryCnt):
            try:
                print ("\nExt Version: ", network_api.get_ext_version(Address(METER_ADDRESS)))
                retryCnt = 0
            except:
                retryCnt = retryCnt-1
                time.sleep(1)
                if (retryCnt == 0):
                    exit()

    retryCnt = 3
    while (retryCnt):
        try:
            print ("Initiate Firmware... ", network_api.initiate_fw_upgrade(Address(METER_ADDRESS)))
            retryCnt = 0
        except:
            retryCnt = retryCnt-1
            time.sleep(1)
            if (retryCnt == 0):
                exit()
    EndTime = datetime.datetime.now()
    print ("\nStartTime:",starttime)
    print ("EndTime:",EndTime)
    print ("Diff : ", EndTime - starttime)



def run():
    parser = argparse.ArgumentParser()

    parser.add_argument('-p', action="store", dest="hex_file", 
                        help="programs new hex file")
    parser.add_argument("--id",action="store", dest="portID",
                      help="device id")
    
    args = parser.parse_args()
    if args.portID is None:
        args.portID = 4

    list_port = []

    try:
        ports = serial.tools.list_ports.comports()
    except:
        print ("No port found...")
        exit()

    for port, desc, hwid in sorted(ports):
        print("{}: {} [{}]".format(port, desc, hwid))
        comp = str(port)
        list_port.append(comp)

    print (list_port)

    # list_portx = ['COM1', 'COM3']

    # Create a thread for each serial port
    threads = [threading.Thread(target=program_thread, args=(port_name, args.hex_file, args.portID)) for port_name in list_port]

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()



if __name__ == "__main__":
    run()
