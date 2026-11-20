import datetime
import time
from gp_node.utils import TamperFlag
import gp_node.utils.serialize as serialize
from gp_node.utils.serialize import *

class Bundle(object):

    def __init__(self):
        self.date_time = datetime.datetime(1970, 1, 1, 0, 0, 0)
        self.current = 0
        self.voltage = 0
        self.temperature = "NA"
        self.block_real_energy_imp = 0
        self.block_apparent_energy_imp = 0
        self.block_active_energy_exp = 0
        self.block_apparent_energy_exp = 0
        self.cumm_real_energy_imp = 0
        self.cumm_apparent_energy_imp = 0
        self.cumm_active_energy_exp = 0
        self.cumm_apparent_energy_exp = 0

        self.date_time1 = datetime.datetime(1970, 1, 1, 0, 0, 0)
        self.current1 = 0
        self.voltage1 = 0
        self.temperature1 = "NA"
        self.block_real_energy_imp1 = 0
        self.block_apparent_energy_imp1 = 0
        self.block_active_energy_exp1 = 0
        self.block_apparent_energy_exp1 = 0

        self.date_time2 = datetime.datetime(1970, 1, 1, 0, 0, 0)
        self.current2 = 0
        self.voltage2 = 0
        self.temperature2 = "NA"
        self.block_real_energy_imp2 = 0
        self.block_apparent_energy_imp2 = 0
        self.block_active_energy_exp2 = 0
        self.block_apparent_energy_exp2 = 0

        self.payloadLen = 0
        # self.cum_real_energy = 0
        # self.cum_reactive_lag_energy = 0
        # self.cum_reactive_lead_energy = 0
        # self.cum_apparent_energy = 0
        

    # def __str__(self):
    #     return ("date_time                  : {} \n"
    #             "current                    : {} mA\n"
    #             "voltage                    : {} V\n"
    #             "block_real_energy          : {} Wh\n"
    #             "block_reactive_lag_energy  : {} VArh\n"
    #             "block_reactive_lead_energy : {} VArh\n"
    #             "block_apparent_energy      : {} VAh\n"
    #             "cum_real_energy            : {} Wh\n"
    #             "cum_reactive_lag_energy    : {} VArh\n"
    #             "cum_reactive_lead_energy   : {} VArh\n"
    #             "cum_apparent_energy        : {} VAh").format(self.date_time,
    #                                          self.current,
    #                                          self.voltage,
    #                                          self.block_real_energy,
    #                                          self.block_reactive_lag_energy,
    #                                          self.block_reactive_lead_energy,
    #                                          self.block_apparent_energy,
    #                                          self.cum_real_energy,
    #                                          self.cum_reactive_lag_energy,
    #                                          self.cum_reactive_lead_energy,
    #                                          self.cum_apparent_energy)

    def __str__(self):
        if self.payloadLen == 0:
            return "No data found !!!"
        a1 =   ("date_time                  : {} \n"
                "current                    : {} A\n"
                "voltage                    : {} V\n"
                "block_active_energy_imp    : {} KWh\n"
                "block_apparent_energy_imp  : {} KVAh\n"
                "block_active_energy_exp    : {} KWh\n"
                "block_apparent_energy_exp  : {} KVAh\n"
                "temperature                : {} ^C\n").format(self.date_time,
                                             self.current,
                                             self.voltage,
                                             self.block_real_energy_imp,
                                             self.block_apparent_energy_imp,
                                             self.block_active_energy_exp,
                                             self.block_apparent_energy_exp,
                                             self.temperature)
        if self.payloadLen <= 32:
            return a1

        a2 =   ("\n\ndate_time                  : {} \n"
                "current                    : {} A\n"
                "voltage                    : {} V\n"
                "block_active_energy_imp    : {} KWh\n"
                "block_apparent_energy_imp  : {} KVAh\n"
                "block_active_energy_exp    : {} KWh\n"
                "block_apparent_energy_exp  : {} KVAh\n"
                "temperature                : {} ^C\n").format(self.date_time1,
                                             self.current1,
                                             self.voltage1,
                                             self.block_real_energy_imp1,
                                             self.block_apparent_energy_imp1,
                                             self.block_active_energy_exp1,
                                             self.block_apparent_energy_exp1,
                                             self.temperature1)
        if self.payloadLen <= 64:
            return a1+a2
        a3 =   ("\n\ndate_time                  : {} \n"
                "current                    : {} A\n"
                "voltage                    : {} V\n"
                "block_active_energy_imp    : {} KWh\n"
                "block_apparent_energy_imp  : {} KVAh\n"
                "block_active_energy_exp    : {} KWh\n"
                "block_apparent_energy_exp  : {} KVAh\n"
                "temperature                : {} ^C\n").format(self.date_time2,
                                             self.current2,
                                             self.voltage2,
                                             self.block_real_energy_imp2,
                                             self.block_apparent_energy_imp2,
                                             self.block_active_energy_exp2,
                                             self.block_apparent_energy_exp2,
                                             self.temperature2)
        if self.payloadLen <= 88:
            return a1+a2+a3

    def serialize(self):
        # TODO: Implement this
        raise Exception("Not implemented.")


    def deserialize(self, payload):
        """
        It is assumed that payload size is 30
        """
        byte = payload
        self.payloadLen = len(payload)
        if self.payloadLen == 0:
            return
        unix_str_time = serialize.deserialize_uint32(byte[0:4], "reverse")
        self.date_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(unix_str_time))
        self.block_real_energy_imp = serialize.deserialize_uint32(byte[4:8], "reverse")/100.0
        self.block_apparent_energy_imp = serialize.deserialize_uint32(byte[8:12], "reverse")/100.0
        self.block_active_energy_exp = serialize.deserialize_uint32(byte[12:16], "reverse")/100.0
        self.block_apparent_energy_exp = serialize.deserialize_uint32(byte[16:20], "reverse")/100.0
        self.voltage = serialize.deserialize_uint32(byte[20:24], "reverse")/1000.0
        self.current = serialize.deserialize_uint32(byte[24:28], "reverse")/1000.0
        if((self.payloadLen > 28 and self.payloadLen <=32) or
        (self.payloadLen > 56 and self.payloadLen <=64) or
        (self.payloadLen > 84 and self.payloadLen <=96)):
            self.temperature = serialize.deserialize_int32(byte[28:32], "reverse")/1000.0

        if self.payloadLen > 28 and self.payloadLen > 32:
            if((self.payloadLen > 56 and self.payloadLen <=64) or
            (self.payloadLen > 84 and self.payloadLen <=96)):
                byte = payload[32:]
            else:
                byte = payload[28:]
            unix_str_time = serialize.deserialize_uint32(byte[0:4], "reverse")
            self.date_time1 = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(unix_str_time))
            self.block_real_energy_imp1 = serialize.deserialize_uint32(byte[4:8], "reverse")/100.0
            self.block_apparent_energy_imp1 = serialize.deserialize_uint32(byte[8:12], "reverse")/100.0
            self.block_active_energy_exp1 = serialize.deserialize_uint32(byte[12:16], "reverse")/100.0
            self.block_apparent_energy_exp1 = serialize.deserialize_uint32(byte[16:20], "reverse")/100.0
            self.voltage1 = serialize.deserialize_uint32(byte[20:24], "reverse")/1000.0
            self.current1 = serialize.deserialize_uint32(byte[24:28], "reverse")/1000.0
            if((self.payloadLen > 56 and self.payloadLen <=64) or
            (self.payloadLen > 84 and self.payloadLen <=96)):
                self.temperature1 = serialize.deserialize_int32(byte[28:32], "reverse")/1000.0

        if self.payloadLen > 56 and self.payloadLen > 64:
            if self.payloadLen <=84:
                byte = payload[56:]
            if self.payloadLen <=96:
                byte = payload[64:]
            unix_str_time = serialize.deserialize_uint32(byte[0:4], "reverse")
            self.date_time2 = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(unix_str_time))
            self.block_real_energy_imp2 = serialize.deserialize_uint32(byte[4:8], "reverse")/100.0
            self.block_apparent_energy_imp2 = serialize.deserialize_uint32(byte[8:12], "reverse")/100.0
            self.block_active_energy_exp2 = serialize.deserialize_uint32(byte[12:16], "reverse")/100.0
            self.block_apparent_energy_exp2 = serialize.deserialize_uint32(byte[16:20], "reverse")/100.0
            self.voltage2 = serialize.deserialize_uint32(byte[20:24], "reverse")/1000.0
            self.current2 = serialize.deserialize_uint32(byte[24:28], "reverse")/1000.0
            if self.payloadLen > 84 and self.payloadLen <=96:
                self.temperature2 = serialize.deserialize_int32(byte[28:32], "reverse")/1000.0

    def deserialize_push(self, payload):
        """
        It is assumed that payload size is 48
        """
        byte = payload
        self.payloadLen = len(payload)
        if self.payloadLen == 0:
            return
        unix_str_time = serialize.deserialize_uint32(byte[0:4], "reverse")
        self.date_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(unix_str_time))
        self.block_real_energy_imp = serialize.deserialize_uint32(byte[4:8], "reverse")/100.0
        self.block_apparent_energy_imp = serialize.deserialize_uint32(byte[8:12], "reverse")/100.0
        self.block_active_energy_exp = serialize.deserialize_uint32(byte[12:16], "reverse")/100.0
        self.block_apparent_energy_exp = serialize.deserialize_uint32(byte[16:20], "reverse")/100.0
        self.voltage = serialize.deserialize_uint32(byte[20:24], "reverse")/1000.0
        self.current = serialize.deserialize_uint32(byte[24:28], "reverse")/1000.0
        if len(payload) > 28:
            self.cumm_real_energy_imp = serialize.deserialize_uint32(byte[28:32], "reverse")/100.0
            self.cumm_apparent_energy_imp = serialize.deserialize_uint32(byte[32:36], "reverse")/100.0
            self.cumm_active_energy_exp = serialize.deserialize_uint32(byte[36:40], "reverse")/100.0
            self.cumm_apparent_energy_exp = serialize.deserialize_uint32(byte[40:44], "reverse")/100.0
        if len(payload) > 44:
            self.temperature = serialize.deserialize_int32(byte[44:48], "reverse")/1000.0

    def get_push_bundle(self, payload):
        a1 =   ("date_time                  : {} \n"
                "current                    : {} A\n"
                "voltage                    : {} V\n"
                "block_active_energy_imp    : {} KWh\n"
                "block_apparent_energy_imp  : {} KVAh\n"
                "block_active_energy_exp    : {} KWh\n"
                "block_apparent_energy_exp  : {} KVAh").format(self.date_time,
                                             self.current,
                                             self.voltage,
                                             self.block_real_energy_imp,
                                             self.block_apparent_energy_imp,
                                             self.block_active_energy_exp,
                                             self.block_apparent_energy_exp)
        if len(payload) <= 28:
            return a1
        return ("date_time                  : {} \n"
                "current                    : {} A\n"
                "voltage                    : {} V\n"
                "block_active_energy_imp    : {} KWh\n"
                "block_apparent_energy_imp  : {} KVAh\n"
                "block_active_energy_exp    : {} KWh\n"
                "block_apparent_energy_exp  : {} KVAh\n"
                "cumm_active_energy_imp     : {} KWh\n"
                "cumm_apparent_energy_imp   : {} KVAh\n"
                "cumm_active_energy_exp     : {} KWh\n"
                "cumm_apparent_energy_exp   : {} KVAh\n"
                "temperature                : {} ^C").format(self.date_time,
                                             self.current,
                                             self.voltage,
                                             self.cumm_real_energy_imp,
                                             self.cumm_apparent_energy_imp,
                                             self.cumm_active_energy_exp,
                                             self.cumm_apparent_energy_exp,
                                             self.block_real_energy_imp,
                                             self.block_apparent_energy_imp,
                                             self.block_active_energy_exp,
                                             self.block_apparent_energy_exp,
                                             self.temperature)
    def printlog(self, payload):
        return ("{:<3}{:<5}{:<25}{:<15}{:<15}{:<15}{:<15}{:<15}{:<15}{}")\
                .format(" ",
                        payload,
                        self.date_time,
                        self.current,
                        self.voltage,
                        self.block_real_energy_imp,
                        self.block_apparent_energy_imp,
                        self.block_active_energy_exp,
                        self.block_apparent_energy_exp,
                        self.temperature)
        
