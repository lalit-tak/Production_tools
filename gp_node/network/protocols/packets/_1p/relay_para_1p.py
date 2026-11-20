import gp_node.utils.serialize as serialize
from gp_node.utils import TamperFlag
# import time
# import datetime


class   IP_RelayPara(object):

    def __init__(self):
        """
        The constructor instantiates a default dictionary to store the ecop data
        """
        self.return_params = {"control_mode":0, 
                              "control_state": 0,
                              "relay_state": 0,
                              "switch_off_reason": 0}


    def deserialize_packet_bundle(self,payload):
        """
        Deserializes the input payload and populates the data to the default
        dictionary.This API needs to be used to retrieve information from the 
        reply bytestream.
        :param payload:input bytestream
        :return :none
        """
        bytes = bytearray()
        bytes = payload

        a = bytes[0]
        self.return_params["control_mode"]          =  "Mode " + str(a)

        a = bytes[1]
        if (1 == a):
            self.return_params["control_state"]     =  "CONNECTED"
        elif (2 == a):
            self.return_params["control_state"]     =  "READY FOR RE-CONNECTION"
        elif (0 == a):
            self.return_params["control_state"]     =  "DISCONNECTED"

        a = bytes[2]
        if (1 == a):
            self.return_params["relay_state"]     =  "ON"
        elif (0 == a):
            self.return_params["relay_state"]     =  "OFF"

        a = bytes[3]
        if (0 == a):
            self.return_params["switch_off_reason"]     =  "none"
        elif (1 == (a & 0x01)):
            self.return_params["switch_off_reason"]     =  "Over Power"
        elif (2 == (a & 0x02)):
            self.return_params["switch_off_reason"]     =  "Cover Open"
        elif (4 == (a & 0x04)):
            self.return_params["switch_off_reason"]     =  "Over Current"
        elif (8 == (a & 0x08)):
            self.return_params["switch_off_reason"]     =  "Remote"
        elif (16 == (a & 0x10)):
            self.return_params["switch_off_reason"]     =  "Account Empty"
        elif (32 == (a & 0x20)):
            self.return_params["switch_off_reason"]     =  "High Load"
        elif (64 == (a & 0x40)):
            self.return_params["switch_off_reason"]     =  "Manual"
        elif (128 == (a & 0x80)):
            self.return_params["switch_off_reason"]     =  "Manual On with Acc Empty"

    
    def get_packet_bundle(self):
        """
        Prints out the stored information in the dictionary.
        Useful along with print statements.
        ex: print EcopDataStreamPacket()
        :param :none
        :return :none
        """
        return (" Control Mode      : {} \n"
                " Control State     : {} \n"
                " Output State      : {} \n"
                " Off Reason        : {} \n"
                )\
                .format(self.return_params["control_mode"],
                        self.return_params["control_state"],
                        self.return_params["relay_state"],
                        self.return_params["switch_off_reason"])

    def deserialize_gas_packet(self,payload):
        """
        Deserializes the input payload and populates the data to the default
        dictionary.This API needs to be used to retrieve information from the 
        reply bytestream.
        :param payload:input bytestream
        :return :none
        """
        bytes = bytearray()
        bytes = payload

        control_status   = ['CONTROL_CLEAR', 'AUTO_CONTROL_ON', 'AUTO_CONTROL_OFF', 'REMOTE_CONTROL_ON', 'REMOTE_CONTROL_OFF']
        switchOffReasons = ['SWOFF_COPEN', 'SWOFF_MOPEN', 'SWOFF_MAGNET', 'SWOFF_ACCNT_EMPTY', 'SWOFF_MANUAL']
        relay_status     = ['RELAY_STATE_OFF', 'RELAY_STATE_ON']

        control_mode = bytes[0]
        if (control_mode >= 0) or (control_mode <= 4):
            self.return_params["control_mode"]  = control_status[control_mode]
        else:
            self.return_params["control_mode"]  = 'CONTROL_CLEAR'

        reason = bytes[1]
        self.return_params["control_state"] = []
        for b in range(0,5):
            if (reason & (1 << b)):
                self.return_params["control_state"].append(switchOffReasons[b])

        state = bytes[2]
        self.return_params["relay_state"] = relay_status[state]

    
    def get_gas_packet(self):
        """
        Prints out the stored information in the dictionary.
        Useful along with print statements.
        ex: print EcopDataStreamPacket()
        :param :none
        :return :none
        """
        return (" ControlMode       : {} \n"
                " SwitchOFFReason   : {} \n"
                " OutputState       : {} \n"
                )\
                .format(self.return_params["control_mode"],
                        self.return_params["control_state"],
                        self.return_params["relay_state"])


# if __name__ == "__main__":
#     event = IP_RelayPara()
#     payload = [1,5,1]
#     event.deserialize_gas_packet(payload)
#     print event.get_gas_packet()