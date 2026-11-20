"""
Implements the packet reader of Maxwell board. This utility
should be used when an FTDI cable is attached to the Rx/Tx
lines of the Maxwell board, and a laptop is being used
to read the packets sent by the Maxwell board.

The run() method is the entry point of the maxwell-packet-monitor

The parser is implemented as a state machine; the parser can
be in three possible state:
    1. STATE_IDLE: when the parser is waiting to receive a start byte (0xAA)
    2. STATE_IN_PROGRESS: when the parser has received 0xAA and is waiting to\
            receive a total of 58 bytes (including the start byte)
    3. STATE_RECEIVED: when the parser has received 58 bytes (including start byte)\
            and when it has been verified that the CRC of the incoming \
            packet is consistent
"""
import argparse
import serial
import time
import datetime

STATE_IDLE = 0
STATE_IN_PROGRESS = 1
STATE_LEN_RECEIVED = 2
STATE_RECEIVED = 3

PACKET_LENGTH_INDEX = 16

def run():
    parser = argparse.ArgumentParser( \
        description=("Monitor serial") );
    parser.add_argument('-d', '--device', default='com3', \
            help='Device filename of the FTDI cable. Default is com5');
    parser.add_argument('-b', '--baud', default=19200, \
            help='Baud rate to use to communicate with Maxwell board. Default is 19200');
    args = parser.parse_args()
    ser = serial.Serial(args.device, args.baud, timeout=1)
    ser1= serial.Serial('com2', 19200, timeout=1)

    print ("STATE_IDLE")

    while True:
        try:
            if ser.inWaiting()>0:
                print ("Rx: ["),
                while ser.inWaiting()>0:
                    byte = ser.read()
                    if len(byte) > 0:
                        ser1.write(byte)
                        print (byte.encode('hex')),
                    if ser.inWaiting() == 0:
                        time.sleep(0.05)
                print ("]")


            if ser1.inWaiting()>0:
                print ("Tx: ["),
                while ser1.inWaiting()>0:
                    byte = ser1.read()
                    if len(byte) > 0:
                        ser.write(byte)
                        print (byte.encode('hex')),
                    if ser1.inWaiting() == 0:
                        time.sleep(0.05)
                print ("]")
        except Exception as err:
            print ("Error: ", err)



if __name__ == "__main__":
    run()
