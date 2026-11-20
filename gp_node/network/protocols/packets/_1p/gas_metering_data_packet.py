import datetime
import gp_node.utils.serialize as serialize
import time

class GasMeteringDataPacket(object):

    def __init__(self):
        self.return_params = {  "bundle_version"            : 0,
                                "meter_serial_number"       : 0,
                                "meter_timestamp"           : datetime.datetime(1970, 1, 1, 0, 0, 0),
                                "current_consumed_gas"      : 0.0,
                                "daily_time1"               : datetime.datetime(1970, 1, 1, 0, 0, 0),
                                "daily_balance_amount1"     : 0.0,
                                "daily_consumed_gas1"       : 0.0,
                                "daily_time2"               : datetime.datetime(1970, 1, 1, 0, 0, 0),
                                "daily_balance_amount2"     : 0.0,
                                "daily_consumed_gas2"       : 0.0,
                                "daily_time3"               : datetime.datetime(1970, 1, 1, 0, 0, 0),
                                "daily_balance_amount3"     : 0.0,
                                "daily_consumed_gas3"       : 0.0,
                                "daily_time4"               : datetime.datetime(1970, 1, 1, 0, 0, 0),
                                "daily_balance_amount4"     : 0.0,
                                "daily_consumed_gas4"       : 0.0,
                                "daily_time5"               : datetime.datetime(1970, 1, 1, 0, 0, 0),
                                "daily_balance_amount5"     : 0.0,
                                "daily_consumed_gas5"       : 0.0,
                                "daily_time6"               : datetime.datetime(1970, 1, 1, 0, 0, 0),
                                "daily_balance_amount6"     : 0.0,
                                "daily_consumed_gas6"       : 0.0,
                                "daily_time7"               : datetime.datetime(1970, 1, 1, 0, 0, 0),
                                "daily_balance_amount7"     : 0.0,
                                "daily_consumed_gas7"       : 0.0,
                                "prepaid_status"            : "POSTPAID",
                                "prepaid_balance_amount"    : 0.0,
                                "prepaid_net_recharge"      : 0.0,
                                "last_tariff_TS"            : datetime.datetime(1970, 1, 1, 0, 0, 0),
                                "tariff_gas_price"          : 0.0,
                                "prepaid_event_sts"         : "NONE",
                                "liveTamper"                : "NONE",
                                "Battary_level"             : 0
                                }

    def getMeteringPacket(self):
        return ("bundle_version         : {}    \n"
                "meter_serial_number    : {}    \n"
                "meter_timestamp        : {}    \n"
                "current_consumed_gas   : {} m3 \n"
                "daily_time1            : {}    \n"
                "daily_balance_amount1  : {} Rs \n"
                "daily_consumed_gas1    : {} m3 \n"
                "daily_time2            : {}    \n"
                "daily_balance_amount2  : {} Rs \n"
                "daily_consumed_gas2    : {} m3 \n"
                "daily_time3            : {}    \n"
                "daily_balance_amount3  : {} Rs \n"
                "daily_consumed_gas3    : {} m3 \n"
                "daily_time4            : {}    \n"
                "daily_balance_amount4  : {} Rs \n"
                "daily_consumed_gas4    : {} m3 \n"
                "daily_time5            : {}    \n"
                "daily_balance_amount5  : {} Rs \n"
                "daily_consumed_gas5    : {} m3 \n"
                "daily_time6            : {}    \n"
                "daily_balance_amount6  : {} Rs \n"
                "daily_consumed_gas6    : {} m3 \n"
                "daily_time7            : {}    \n"
                "daily_balance_amount7  : {} Rs \n"
                "daily_consumed_gas7    : {} m3 \n"
                "prepaid_status         : {}    \n"
                "prepaid_balance_amount : {} Rs \n"
                "prepaid_net_recharge   : {} Rs \n"
                "last_tariff_TS         : {}    \n"
                "tariff_gas_price       : {} Rs \n"
                "prepaid_event_sts      : {}    \n"
                "liveTamper             : {}    \n"
                "Battary_level          : {} %  \n"
                )\
                .format(    self.return_params["bundle_version"],
                            self.return_params["meter_serial_number"],
                            self.return_params["meter_timestamp"],
                            self.return_params["current_consumed_gas"],
                            self.return_params["daily_time1"],
                            self.return_params["daily_balance_amount1"],
                            self.return_params["daily_consumed_gas1"],
                            self.return_params["daily_time2"],
                            self.return_params["daily_balance_amount2"],
                            self.return_params["daily_consumed_gas2"],
                            self.return_params["daily_time3"],
                            self.return_params["daily_balance_amount3"],
                            self.return_params["daily_consumed_gas3"],
                            self.return_params["daily_time4"],
                            self.return_params["daily_balance_amount4"],
                            self.return_params["daily_consumed_gas4"],
                            self.return_params["daily_time5"],
                            self.return_params["daily_balance_amount5"],
                            self.return_params["daily_consumed_gas5"],
                            self.return_params["daily_time6"],
                            self.return_params["daily_balance_amount6"],
                            self.return_params["daily_consumed_gas6"],
                            self.return_params["daily_time7"],
                            self.return_params["daily_balance_amount7"],
                            self.return_params["daily_consumed_gas7"],
                            self.return_params["prepaid_status"],
                            self.return_params["prepaid_balance_amount"],
                            self.return_params["prepaid_net_recharge"],
                            self.return_params["last_tariff_TS"],
                            self.return_params["tariff_gas_price"],
                            self.return_params["prepaid_event_sts"],
                            self.return_params["liveTamper"],
                            self.return_params["Battary_level"])

    def serialize(self):
        # TODO: Implement this
        raise Exception("Not implemented.")

    def deserializeMeteringPacket(self, payload):
        """
        It is assumed that payload size is 75
        """

        MAGNET_MASK  = 0x01
        MOPEN_MASK   = 0x02
        COPEN_MASK   = 0x04
        LOW_BAT_MASK = 0x08

        relayEvent = ["RELAY_STATE_UNKNOWN", "AUTO_CONTROL_ON","AUTO_CONTROL_OFF","REMOTE_CONTROL_ON","REMOTE_CONTROL_OFF"]

        prepaidEvent = ["PREPAID_DISABLE","PREPAID_EVENT_NORMAL_CREDIT_ZONE","PREPAID_EVENT_LOW_CREDIT_ZONE",
                        "PREPAID_EVENT_EMERGENCY_CREDIT_ZONE","PREPAID_EVENT_FRIENDLY_HOURS_ZONE",
                        "PREPAID_EVENT_NO_CREDIT_ZONE"]
        TamperEvent  = []

        buf = bytearray()
        buf = payload

        self.return_params["bundle_version"]            = serialize.deserialize_uint8(buf[0:1])
        self.return_params["meter_serial_number"]       = serialize.deserialize_uint32(buf[1:5])
        timearr = serialize.deserialize_uint32(buf[5:9])
        self.return_params["meter_timestamp"]           = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
        self.return_params["current_consumed_gas"]      = serialize.deserialize_uint24(buf[9:12])/100.0

        timearr = serialize.deserialize_uint16(buf[12:14])*86400
        self.return_params["daily_time1"]               = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
        self.return_params["daily_consumed_gas1"]       = serialize.deserialize_uint24(buf[14:17])/100.0
        self.return_params["daily_balance_amount1"]     = serialize.deserialize_int16(buf[17:19])/1.0

        timearr = serialize.deserialize_uint16(buf[19:21])*86400
        self.return_params["daily_time2"]               = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
        self.return_params["daily_consumed_gas2"]       = serialize.deserialize_uint24(buf[21:24])/100.0
        self.return_params["daily_balance_amount2"]     = serialize.deserialize_int16(buf[24:26])/1.0

        timearr = serialize.deserialize_uint16(buf[26:28])*86400
        self.return_params["daily_time3"]               = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
        self.return_params["daily_consumed_gas3"]       = serialize.deserialize_uint24(buf[28:31])/100.0
        self.return_params["daily_balance_amount3"]     = serialize.deserialize_int16(buf[31:33])/1.0

        timearr = serialize.deserialize_uint16(buf[33:35])*86400
        self.return_params["daily_time4"]               = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
        self.return_params["daily_consumed_gas4"]       = serialize.deserialize_uint24(buf[35:38])/100.0
        self.return_params["daily_balance_amount4"]     = serialize.deserialize_int16(buf[38:40])/1.0

        timearr = serialize.deserialize_uint16(buf[40:42])*86400
        self.return_params["daily_time5"]               = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
        self.return_params["daily_consumed_gas5"]       = serialize.deserialize_uint24(buf[42:45])/100.0
        self.return_params["daily_balance_amount5"]     = serialize.deserialize_int16(buf[45:47])/1.0

        timearr = serialize.deserialize_uint16(buf[47:49])*86400
        self.return_params["daily_time6"]               = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
        self.return_params["daily_consumed_gas6"]       = serialize.deserialize_uint24(buf[49:52])/100.0
        self.return_params["daily_balance_amount6"]     = serialize.deserialize_int16(buf[52:54])/1.0

        timearr = serialize.deserialize_uint16(buf[54:56])*86400
        self.return_params["daily_time7"]               = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
        self.return_params["daily_consumed_gas7"]       = serialize.deserialize_uint24(buf[56:59])/100.0
        self.return_params["daily_balance_amount7"]     = serialize.deserialize_int16(buf[59:61])/1.0

        temp = serialize.deserialize_uint8(buf[61:62])
        if (temp == 0x55):
            self.return_params["prepaid_status"]        = "PREPAID"
        self.return_params["prepaid_balance_amount"]    = serialize.deserialize_int32(buf[62:66])/100.0
        self.return_params["prepaid_net_recharge"]      = serialize.deserialize_uint32(buf[66:70])/100.0

        timearr = serialize.deserialize_uint16(buf[70:72])*86400
        self.return_params["last_tariff_TS"]            = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
        self.return_params["tariff_gas_price"]          = serialize.deserialize_uint16(buf[72:74])/100.0

        temp = serialize.deserialize_uint8(buf[74:75])
        if (temp <= 5):
            self.return_params["prepaid_event_sts"]     = prepaidEvent[temp]

        temp = serialize.deserialize_uint8(buf[75:76])
        if (temp & MAGNET_MASK):
            TamperEvent.append("MAGNET")
        if (temp & MOPEN_MASK):
            TamperEvent.append("M-OPEN")
        if (temp & COPEN_MASK):
            TamperEvent.append("C-OPEN")
        if (temp & LOW_BAT_MASK):
            TamperEvent.append("LOW-BAT")

        temp = (temp >> 4)&0x0F;
        TamperEvent.append(relayEvent[temp])

        self.return_params["liveTamper"]                = TamperEvent
        self.return_params["Battary_level"]             = serialize.deserialize_uint8(buf[76:77])/1.0




class GasMeteringTariffPacket(object):

    def __init__(self):
        self.return_params = {  "tariff_ackid"             : 0,
                                "tariff_activationTS"      : datetime.datetime(1970, 1, 1, 0, 0, 0),
                                "tariff_gasPrice"          : 0,
                                "tariff_topUpLimit"        : 0,
                                "tariff_creditLimit"       : 0,
                                "tariff_emergencyLimit"    : 0,
                                "recharge_token1"          : 0,
                                "recharge1"                : 0,
                                "recharge_token2"          : 0,
                                "recharge2"                : 0,
                                "recharge_token3"          : 0,
                                "recharge3"                : 0,
                                "recharge_token4"          : 0,
                                "recharge4"                : 0,
                                "recharge_token5"          : 0,
                                "recharge5"                : 0
                                }

    # def getMeteringTariffPacket(self):
    #     return ("tariff_activationTS    : {}       \n"
    #             "tariff_gasPrice        : {} Paise \n"
    #             "tariff_topUpLimit      : {} Rs    \n"
    #             "tariff_creditLimit     : {} Rs    \n"
    #             "tariff_emergencyLimit  : {} Rs    \n"
    #             )\
    #             .format(    self.return_params["tariff_activationTS"],
    #                         self.return_params["tariff_gasPrice"],
    #                         self.return_params["tariff_topUpLimit"],
    #                         self.return_params["tariff_creditLimit"],
    #                         self.return_params["tariff_emergencyLimit"])

    def serializeMeteringTariffPacket(self):

        payload = bytearray()

        payload.extend(serialize.serialize_uint16(self.return_params["tariff_ackid"]))
        payload.extend(serialize.serialize_uint16(self.return_params["tariff_activationTS"], "reverse"))
        payload.extend(serialize.serialize_uint16(self.return_params["tariff_gasPrice"], "reverse"))
        payload.extend(serialize.serialize_uint16(self.return_params["tariff_topUpLimit"], "reverse"))
        payload.extend(serialize.serialize_int16(self.return_params["tariff_creditLimit"], "reverse"))
        payload.extend(serialize.serialize_int16(self.return_params["tariff_emergencyLimit"], "reverse"))
        payload.extend(serialize.serialize_uint32(self.return_params["recharge_token1"], "reverse"))
        payload.extend(serialize.serialize_int32(self.return_params["recharge1"], "reverse"))
        payload.extend(serialize.serialize_uint32(self.return_params["recharge_token2"], "reverse"))
        payload.extend(serialize.serialize_int32(self.return_params["recharge2"], "reverse"))
        payload.extend(serialize.serialize_uint32(self.return_params["recharge_token3"], "reverse"))
        payload.extend(serialize.serialize_int32(self.return_params["recharge3"], "reverse"))
        payload.extend(serialize.serialize_uint32(self.return_params["recharge_token4"], "reverse"))
        payload.extend(serialize.serialize_int32(self.return_params["recharge4"], "reverse"))
        payload.extend(serialize.serialize_uint32(self.return_params["recharge_token5"], "reverse"))
        payload.extend(serialize.serialize_int32(self.return_params["recharge5"], "reverse"))
        return payload

    def serializeMeteringTariff(self):

        payload = bytearray()

        payload.extend(serialize.serialize_uint16(self.return_params["tariff_activationTS"], "reverse"))
        payload.extend(serialize.serialize_uint16(self.return_params["tariff_gasPrice"], "reverse"))
        payload.extend(serialize.serialize_uint16(self.return_params["tariff_topUpLimit"], "reverse"))
        payload.extend(serialize.serialize_int16(self.return_params["tariff_creditLimit"], "reverse"))
        payload.extend(serialize.serialize_int16(self.return_params["tariff_emergencyLimit"], "reverse"))
        return payload

    def deserializeMeteringTariffPacket(self, payload, dataindex):
        """
        It is assumed that payload size is 10
        """
        buf = payload
        dataLen = len(buf)
        index = 0
        data_index = dataindex * 7
        retVal = ""

        print ("{:<10}{:<23}{:<17}{:<19}{:<20}{} \n"
               "{:<10}{:<23}{:<17}{:<19}{:<20}{}").format(
        "Index", "Tariff_ActiveTS"    ,"GasPrice(Rs)" ,"TopUpLimit(Rs)" ,"CreditLimit(Rs)","EmergencyLimit(Rs)",
        "------","-------------------","-------------","---------------","----------------","------------------")
        while(dataLen >= 10):
            timearr = serialize.deserialize_uint16(buf[index+0:index+2], "reverse") * 86400
            self.return_params["tariff_activationTS"]       = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(timearr))
            self.return_params["tariff_gasPrice"]           = serialize.deserialize_uint16(buf[index+2:index+4], "reverse")/100.0
            self.return_params["tariff_topUpLimit"]         = serialize.deserialize_uint16(buf[index+4:index+6], "reverse")/1.0
            self.return_params["tariff_creditLimit"]        = serialize.deserialize_int16(buf[index+6:index+8], "reverse")/1.0
            self.return_params["tariff_emergencyLimit"]     = serialize.deserialize_int16(buf[index+8:index+10], "reverse")/1.0
            retVal += ("{:<10}{:<23}{:<17}{:<19}{:<20}{} \n").format(data_index,
                                                        self.return_params["tariff_activationTS"],
                                                        self.return_params["tariff_gasPrice"],
                                                        self.return_params["tariff_topUpLimit"],
                                                        self.return_params["tariff_creditLimit"],
                                                        self.return_params["tariff_emergencyLimit"])
            dataLen = dataLen-10
            index = index+10
            data_index = data_index+1
        return retVal

if __name__ == '__main__':
    entry = GasMeteringTariffPacket()
    payload = bytearray([0x7,0x4c,0x18,0x15,0xb8,0xb,0x64,0x0,0x9c,0xff])
    print(entry.deserializeMeteringTariffPacket(payload, 1))
