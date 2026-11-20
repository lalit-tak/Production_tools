"""
Definition of the TAP, used as the basis 
for Gram Power network communication.
"""

import time
# import sys
from copy import deepcopy
import os
import os.path
from gp_node.utils import Address
import crcmod

crc16 = crcmod.predefined.mkPredefinedCrcFun('xmodem')
import gp_node.utils.serialize as serialize
from gp_node.network.protocols.common.rc_packet_mode import rfPacket
from gp_node.network.network_log.network_log import networkDataLogger
# from gp_node.network.protocols._1p.command_mapping_container import commandMappingContainer


class TAPError(Exception):
    """
    The values of error code can be:

    TAPError.TIMEOUT_START_BYTE: used when start byte is not found withing a threshold duration

    TAPError.TIMEOUT_LENGTH: used when sufficient bytes are not received on the serial port \
            within a threshold duration

    TAPError.STOP_BYTE_MISMATCH: used when stop byte in incoming stream is not 0x55

    TAPError.TIMEOUT_PACKET_MODE: used to raise exception if there is any issue in incomming 
    packet parsing in packet mode.

    """

    TIMEOUT_START_BYTE = 1
    TIMEOUT_LENGTH = 2
    STOP_BYTE_MISMATCH = 3
    TIMEOUT_PACKET_MODE = 4
    PACKET_MODE_DATA_CORRUPT = 5
    PORT_ID_MISMATCH = 10

    def __init__(self, error_code):
        self.error_code = error_code

    def __str__(self):
        output = ""
        if self.error_code == self.TIMEOUT_START_BYTE:
            output = "TIMEOUT_START_BYTE"
        elif self.error_code == self.TIMEOUT_LENGTH:
            output = "TIMEOUT_LENGTH"
        elif self.error_code == self.STOP_BYTE_MISMATCH:
            output = "STOP_BYTE_MISMATCH"
        elif self.error_code == self.TIMEOUT_PACKET_MODE:
            output = "TIMEOUT_PACKET_MODE"
        elif self.error_code == self.PACKET_MODE_DATA_CORRUPT:
            output = "PACKET_MODE_DATA_CORRUPT"
        elif self.error_code == self.PORT_ID_MISMATCH:
            output = "PORT_ID_MISMATCH( use: node-shell -id device Port Id )"
        return output


class TAPPacket(object):
    """
    :param src_addr: address of source (sender)
    :type src_addr: Address

    :param dest_addr: address of destination (receiver)
    :type dest_addr: Address

    :param src_port: port number of sender
    :type src_port: int

    :param dest_port: port number of receiver
    :type dest_port: int

    :param data_len: length of self.data
    :type data_len: int

    :param data: content
    :type data_len: str
    """

    def __init__(self):
        """Initializes contents of the packet"""
        self.data_len = 0
        self.data = ''
        self.p_status = True
        self.crc = None

    def __str__(self):
        """Prints out the contents of this packet"""
        output = ""
        output += "Data Length: " + str(self.data_len) + "\n"
        output += "Data: " + str(self.data) + "\n"
        return output

    def __eq__(self, other):
        """Implements == for TAP packets"""
        assert isinstance(other, self.__class__)
        equals = True
        equals = equals and (self.data_len == other.data_len)
        equals = equals and (self.data == other.data)
        return equals

    def __ne__(self, other):
        """Implements != for TAP packets"""
        return not self.__eq__(other)

    def fill(self, data_len, data):
        """Fills the packet with argument values"""
        self.data_len = data_len
        self.data = data

    def serialize(self,param_number):
        """Converts the packet into a buf which can be sent over the serial port

        :returns: serialized buf
        :rtype: str
        """
        transaction_id = 39605
        buf = bytearray()
        buf.extend(chr(0x7E))
        buf.extend(serialize.serialize_uint16(param_number))
        buf.extend(serialize.serialize_uint16(transaction_id))
        self.data_len = self.data_len + 6
        buf.extend(chr(self.data_len))
        mac_id = 0xff
        buf.extend(serialize.serialize_uint8(mac_id))
        buf.extend(serialize.serialize_uint8(mac_id))
        buf.extend(serialize.serialize_uint8(mac_id))
        buf.extend(serialize.serialize_uint8(mac_id))
        buf.extend(serialize.serialize_uint8(mac_id))
        buf.extend(serialize.serialize_uint8(mac_id))

        # The 2 byte CRC forms the stop byte
        for i in range(0, (self.data_len - 6)):
            buf.extend(chr(self.data[i]))

        # CRC is calculated for even bytes to be in sync with the embedded part
        # If data bytes is odd.'0' is appended and then CRC is calculated
        if (len(buf[5:]) % 2) != 0:
            temp_buf = deepcopy(buf)
            temp_buf.extend(chr(0))
            self.crc = crc16(str(temp_buf[5:]))
        else:
            self.crc = crc16(str(buf[5:]))

        buf.extend(serialize.serialize_uint16(self.crc))
        print("Tx:[", end=' ')
        print(' '.join(hex(x) for x in buf), end=' ')
        print("]")
        return buf

    def deserialize(self, buf):
        """
        Populates the TAP packet from buf argument

        :param buf: The string which represents the TAP payload \
                (ie, start byte and stop byte are not included in buf)
        :type buf: bytearray
        """
        self.data_len = buf[0]
        self.data = buf[7:]
    def print_state(self, data):
        """Enable or disable packet Tx/Rx debug printing for this packet.

        Setting ``data`` to ``True`` enables printing of Tx/Rx buffers for
        this packet; ``False`` disables such debug output.

        :param bool data: enable printing if True
        """
        self.p_status = data



class TAPHandler1(object):
    """Implementation for sending and receving TAP packets over a serial port"""

    def __init__(self, ser, timeout, mode="rc_packet",
                 network_log_path=os.path.expanduser("~/")):
        """
        :param ser: serial port object pointing to gateway
        :type ser: serial.Serial

        :param timeout: the timeout duration for sending a packet
        :type timeout: int
        """
        self.ser = ser
        self.timeout = timeout
        self.mode = mode
        self.n_log = networkDataLogger(network_log_path)
        self.p_status=False


    def get_packet(self):
        """
        Parses the incoming byte stream from the serial port and 
        returns a TAP packet is parsing is succesful


        :raises: TAPError in case parsing of incoming bytes fails
        :returns: a parsed TAP packet
        :rtype: TAPPacket
        """

        buf = bytearray()
        self.ser.flushInput()
        if self.mode == "rc_packet":
            rply = self.get_rc_packet()
            #check for data length
            if len(rply) < 17:
                raise TAPError(TAPError.PACKET_MODE_DATA_CORRUPT)

            if rply[16] == 0x02:  #if event packet
                ack_rply = rply
                rfp = rfPacket()
                self.n_log.put_network_log(rfp.parse_event_packet(ack_rply)) #print log
                ser_data_rply = self.get_rc_packet()
            else:
                ser_data_rply = rply

            buf = ser_data_rply[18:]

        else:
            start_byte_found = False

            while not start_byte_found:
                byte_read = self.ser.read()
                if len(byte_read) > 0:
                    if byte_read.encode('hex') == "7E":
                        start_byte_found = True
                else:
                    raise TAPError(TAPError.TIMEOUT_START_BYTE)
        my_tap_packet = TAPPacket()

        buf = buf[1:]
        print("stop byte pos ", buf[5])
        stop_byte_pos = buf[5] + 1 + 4 + 1
        response = buf[5:stop_byte_pos]
        my_tap_packet.deserialize(response)

        my_tap_packet.deserialize(buf[0:stop_byte_pos])
        return my_tap_packet

    def get_rc_packet(self):
        """
        Waits and retrieves the radio craft packet from the node.
        This module is currently a helper function for "get_packet"

        :raises : TAP error in case parsing is failed
        :returns : Packet mode packet retrieved from the node
        :rtype : bytearray
        """
        start_time = time.time()
        rc_header_recieved = False
        packet_complete = False
        if self.mode == "rc_packet":
            rc_buf = bytearray()
            while not rc_header_recieved:
                if (time.time() - start_time) > self.timeout:
                    raise TAPError(TAPError.TIMEOUT_PACKET_MODE)
                else:
                    rc_buf.extend(self.ser.read())
                    if len(rc_buf) > 1:
                        rc_header_recieved = True
                        #byte 0 gives the length of the packet(check tiny mesh data sheet)
                        rc_data_length = rc_buf[0]
                        while not packet_complete:
                            if (time.time() - start_time) > self.timeout:
                                raise TAPError(TAPError.TIMEOUT_PACKET_MODE)
                            else:
                                rc_buf.extend(self.ser.read())
                                if len(rc_buf) == rc_data_length:
                                    packet_complete = True

        return rc_buf




    def get_packet_from1(self):
        """
        Drops all packets which are don't have the mentioned source address & source port

        :param src_addr: The expected source address in the incoming TAP packet
        :type src_addr: Address

        :param src_port: The expected source port in the incoming TAP packet
        :type src_port: int

        :returns: TAP packet which matches the address & port as mentioned
        :rtype: TAPPacket

        :raises TAPError:
        """

        while True:
            tap_packet = self.get_packet()
            return tap_packet


    def send_packet(self,data,param_number,dest_addr=None):
        """
        Creates and sends a TAP packet over the serial port. The data_len field 
        is set as len(data).It adds the needed header and tailer if the module
        is operating in packet mode.

        :param src_addr: address of this machine
        :type src_addr: Address

        :param dest_addr: address of node to which the packet is being sent
        :type dest_addr: Address

        :param src_port: source port number
        :type src_port: int

        :param dest_port: destination port number
        :type dest_port: int

        :param data: The payload
        :type data: str
        """
        self.ser.flushOutput()
        assert isinstance(data, bytearray)
        p = TAPPacket()
        p.print_state(self.p_status)
        p.fill(len(data), data)
        #self.ser.write(p.serialize())
        if self.mode == "rc_packet":
            if dest_addr is None:
                # Default to broadcast address if none provided
                dest_addr = Address("255.255.255.255")
            rfp = rfPacket()
            tap_bytes = p.serialize(param_number)
            rfp_bytes = rfp.frame_rf_data_packet(dest_addr, tap_bytes)
            self.ser.write(rfp_bytes)
        else:
            self.ser.write(p.serialize(param_number))

    def send_raw_bytes(self, data):
        """
        This API allows to directly send bytes to the serial port.This is
        kind of bypass over TAP.For instance this API is used by the 
        packet_mode_commands module to send data as it does not depend on
        TAP packets for communication.
        :param data: The data that needds to transmitted over the UART channel
        :type data: bytearray

        :return :None
        """
        assert isinstance(data, bytearray)
        self.ser.write(data)

    def print_status(self, data):
        """Enable or disable debug printing of Tx/Rx at the handler level.

        Setting ``data`` to ``True`` enables printing of Tx/Rx bytes for
        packets handled by this TAPHandler instance. When enabled, the
        string return value explains the current status (verbose message
        used by callers).

        :param bool data: True = enable printing, False = disable
        :returns: descriptive status string
        :rtype: str
        """
        self.p_status = data
        if data == True:
            return "Tx and Rx bytes are enable to print !!!"
        else:
            return "Tx and Rx bytes are disable to print !!!"
