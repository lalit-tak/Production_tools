import datetime
import time
from gp_node.utils import TamperFlag
import gp_node.utils.serialize as serialize
from gp_node.utils.serialize import *

class DailyLoadProfilePacket(object):

    def __init__(self):
        self.date_time = datetime.datetime(1970, 1, 1, 0, 0, 0)
        self.daily_real_energy_imp = 0
        self.daily_apparent_energy_imp = 0
        self.daily_active_energy_exp = 0
        self.daily_apparent_energy_exp = 0
        self.temperature = "NA"

        self.date_time1 = datetime.datetime(1970, 1, 1, 0, 0, 0)
        self.daily_real_energy_imp1 = 0
        self.daily_apparent_energy_imp1 = 0
        self.daily_active_energy_exp1 = 0
        self.daily_apparent_energy_exp1 = 0
        self.temperature1 = "NA"

        self.date_time2 = datetime.datetime(1970, 1, 1, 0, 0, 0)
        self.daily_real_energy_imp2 = 0
        self.daily_apparent_energy_imp2 = 0
        self.daily_active_energy_exp2 = 0
        self.daily_apparent_energy_exp2 = 0
        self.temperature2 = "NA"

        self.payloadLen = 0
        

    def __str__(self):
        if self.payloadLen == 0:
            return "No data found !!!"

        a1 =   ("date_time                  : {} \n"
                "daily_active_energy_imp    : {} KWh\n"
                "daily_apparent_energy_imp  : {} KVAh\n"
                "daily_active_energy_exp    : {} KWh\n"
                "daily_apparent_energy_exp  : {} KVAh\n"
                "temperature                : {} ^C\n").format(self.date_time,
                                             self.daily_real_energy_imp,
                                             self.daily_apparent_energy_imp,
                                             self.daily_active_energy_exp,
                                             self.daily_apparent_energy_exp,
                                             self.temperature)
        if self.payloadLen <= 24:
            return a1
        a2 =   ("\n\ndate_time                  : {} \n"
                "daily_active_energy_imp    : {} KWh\n"
                "daily_apparent_energy_imp  : {} KVAh\n"
                "daily_active_energy_exp    : {} KWh\n"
                "daily_apparent_energy_exp  : {} KVAh\n"
                "temperature                : {} ^C\n").format(self.date_time1,
                                             self.daily_real_energy_imp1,
                                             self.daily_apparent_energy_imp1,
                                             self.daily_active_energy_exp1,
                                             self.daily_apparent_energy_exp1,
                                             self.temperature1)
        if self.payloadLen <= 48:
            return a1+a2
        a3 =   ("\n\ndate_time                  : {} \n"
                "daily_active_energy_imp    : {} KWh\n"
                "daily_apparent_energy_imp  : {} KVAh\n"
                "daily_active_energy_exp    : {} KWh\n"
                "daily_apparent_energy_exp  : {} KVAh\n"
                "temperature                : {} ^C\n").format(self.date_time2,
                                             self.daily_real_energy_imp2,
                                             self.daily_apparent_energy_imp2,
                                             self.daily_active_energy_exp2,
                                             self.daily_apparent_energy_exp2,
                                             self.temperature2)
        return a1+a2+a3
    def serialize(self):
        # TODO: Implement this
        raise Exception("Not implemented.")


    def deserialize(self, payload):
        """
        It is assumed that payload size is 14
        """
        byte = payload
        self.payloadLen = len(payload)
        if self.payloadLen == 0:
            return
        unix_time = serialize.deserialize_uint32(byte[0:4], "reverse")
        self.date_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(unix_time))
        self.daily_real_energy_imp = serialize.deserialize_uint32(byte[4:8], "reverse")/100.0
        self.daily_apparent_energy_imp = serialize.deserialize_uint32(byte[8:12], "reverse")/100.0
        self.daily_active_energy_exp = serialize.deserialize_uint32(byte[12:16], "reverse")/100.0
        self.daily_apparent_energy_exp = serialize.deserialize_uint32(byte[16:20], "reverse")/100.0
        if((self.payloadLen > 20 and self.payloadLen <=24) or
        (self.payloadLen > 40 and self.payloadLen <=48) or
        (self.payloadLen > 60 and self.payloadLen <=72)):
            self.temperature = serialize.deserialize_int32(byte[20:24], "reverse")/1000.0

        if self.payloadLen > 20 and self.payloadLen > 24:
            if((self.payloadLen > 40 and self.payloadLen <=48) or
            (self.payloadLen > 60 and self.payloadLen <=72)):
                byte = payload[24:]
            else:
                byte = payload[20:]
            unix_time = serialize.deserialize_uint32(byte[0:4], "reverse")
            self.date_time1 = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(unix_time))
            self.daily_real_energy_imp1 = serialize.deserialize_uint32(byte[4:8], "reverse")/100.0
            self.daily_apparent_energy_imp1 = serialize.deserialize_uint32(byte[8:12], "reverse")/100.0
            self.daily_active_energy_exp1 = serialize.deserialize_uint32(byte[12:16], "reverse")/100.0
            self.daily_apparent_energy_exp1 = serialize.deserialize_uint32(byte[16:20], "reverse")/100.0
            if((self.payloadLen > 40 and self.payloadLen <=48) or
            (self.payloadLen > 60 and self.payloadLen <=72)):
                self.temperature1 = serialize.deserialize_int32(byte[20:24], "reverse")/1000.0

        if self.payloadLen > 40 and self.payloadLen > 48:
            if self.payloadLen <= 60:
                byte = payload[40:]
            elif self.payloadLen <= 72:
                byte = payload[48:]
            unix_time = serialize.deserialize_uint32(byte[0:4], "reverse")
            self.date_time2 = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(unix_time))
            self.daily_real_energy_imp2 = serialize.deserialize_uint32(byte[4:8], "reverse")/100.0
            self.daily_apparent_energy_imp2 = serialize.deserialize_uint32(byte[8:12], "reverse")/100.0
            self.daily_active_energy_exp2 = serialize.deserialize_uint32(byte[12:16], "reverse")/100.0
            self.daily_apparent_energy_exp2 = serialize.deserialize_uint32(byte[16:20], "reverse")/100.0
            if (self.payloadLen > 60 and self.payloadLen <=72):
                self.temperature2 = serialize.deserialize_int32(byte[20:24], "reverse")/1000.0

    def printlog(self, payload):
        return ("{:<3}{:<7}{:<25}{:<17}{:<17}{:<17}{:<17}{}")\
                .format(" ",
                        payload,
                        self.date_time,
                        self.daily_real_energy_imp,
                        self.daily_apparent_energy_imp,
                        self.daily_active_energy_exp,
                        self.daily_apparent_energy_exp,
                        self.temperature)