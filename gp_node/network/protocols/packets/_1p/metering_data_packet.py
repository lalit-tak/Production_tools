import datetime
import gp_node.utils.serialize as serialize

class MeteringDataPacket(object):

    def __init__(self):
        self.return_params = {  "voltage"               : 0.0,
                                "phase_current"         : 0.0,
                                "neutral_current"       : 0.0,
                                "active_power"          : 0.0,
                                "apparent_power"        : 0.0,
                                "reactive_power"        : 0.0,
                                "frequency"             : 0.0,
                                "power_factor"          : 0.0,
                                "active_energy_imp"     : 0.0,
                                "active_energy_exp"     : 0.0,
                                "apparent_energy_imp"   : 0.0,
                                "apparent_energy_exp"   : 0.0,
                                "reactive_energy_imp"   : 0.0,
                                "reactive_energy_exp"   : 0.0,
                                "activeHr_energy_imp"   : 0.0,
                                "activeHr_energy_exp"   : 0.0,
                                "apparentHr_energy_imp" : 0.0,
                                "apparentHr_energy_exp" : 0.0,
                                "reactiveHr_energy_imp" : 0.0,
                                "reactiveHr_energy_exp" : 0.0,
                                "tamper_event"          : [],
                                "factory_init_time"     : datetime.datetime(1970, 1, 1, 0, 0, 0),
                                "battery_voltage"       : 0.0,
                                "tot_nm_kwh"            : 0.0,
                                "tod1_ts"               : "",
                                "tod1_nm_kwh"           : 0.0,
                                "tod1_nm_kvah"          : 0.0,
                                "tod2_ts"               : "",
                                "tod2_nm_kwh"           : 0.0,
                                "tod2_nm_kvah"          : 0.0,
                                "tod3_ts"               : "",
                                "tod3_nm_kwh"           : 0.0,
                                "tod3_nm_kvah"          : 0.0,
                                "tod4_ts"               : "",
                                "tod4_nm_kwh"           : 0.0,
                                "tod4_nm_kvah"          : 0.0,
                                "Temprature"            : 0.0 
                                }

    def __str__(self):
        return ("Battery voltage        : {} V dc   \n"
                "voltage                : {} V      \n"
                "phase_current          : {} A      \n"
                "neutral_current        : {} A      \n"
                "active_power           : {} KW     \n"
                "apparent_power         : {} KVA    \n"
                "reactive_power         : {} KVAr   \n"
                "frequency              : {} Hz     \n"
                "power_factor           : {}        \n"
                "active_energy_imp      : {} KWh    \n"
                "active_energy_exp      : {} KWh    \n"
                "apparent_energy_imp    : {} KVAh   \n"
                "apparent_energy_exp    : {} KVAh   \n"
                "reactive_energy_imp    : {} KVArh  \n"
                "reactive_energy_exp    : {} KVArh  \n"
                "activeHr_energy_imp    : {} KWh    \n"
                "activeHr_energy_exp    : {} KWh    \n"
                "apparentHr_energy_imp  : {} KVAh   \n"
                "apparentHr_energy_exp  : {} KVAh   \n"
                "reactiveHr_energy_imp  : {} KVArh  \n"
                "reactiveHr_energy_exp  : {} KVArh  \n"
                "tamper_event           : {}        \n"
                "factory_init_time      : {}        \n"
                )\
                .format(    self.return_params["battery_voltage"],
                            self.return_params["voltage"],
                            self.return_params["phase_current"],
                            self.return_params["neutral_current"],
                            self.return_params["active_power"],
                            self.return_params["apparent_power"],
                            self.return_params["reactive_power"],
                            self.return_params["frequency"],
                            self.return_params["power_factor"],
                            self.return_params["active_energy_imp"],
                            self.return_params["active_energy_exp"],
                            self.return_params["apparent_energy_imp"],
                            self.return_params["apparent_energy_exp"],
                            self.return_params["reactive_energy_imp"],
                            self.return_params["reactive_energy_exp"],
                            self.return_params["activeHr_energy_imp"],
                            self.return_params["activeHr_energy_exp"],
                            self.return_params["apparentHr_energy_imp"],
                            self.return_params["apparentHr_energy_exp"],
                            self.return_params["reactiveHr_energy_imp"],
                            self.return_params["reactiveHr_energy_exp"],
                            self.return_params["tamper_event"],
                            self.return_params["factory_init_time"])

    def serialize(self):
        # TODO: Implement this
        raise Exception("Not implemented.")

    def deserialize(self, payload):
        """
        It is assumed that payload size is 29
        """

        liveTamper = ['OVER_VOLTAGE','LOW_VOLTAGE','CURRENT_REVERSE','OVER_CURRENT',
                      'EARTH','MAGNET','NEUTRAL_DISTURBANCE','NEUTRAL_MISSING','OVERLOAD',
                      'C-OPEN','FREQ_MALFUNCTION','LOW_PF','NO_BAL','PLUG_OUT_COMM_MODULE']
        buf = bytearray()
        buf = payload

        self.return_params["voltage"]                = serialize.deserialize_uint32(buf[0:4])/1000.0
        self.return_params["phase_current"]          = serialize.deserialize_uint32(buf[4:8])/1000.0
        self.return_params["neutral_current"]        = serialize.deserialize_uint32(buf[8:12])/1000.0
        self.return_params["active_power"]           = serialize.deserialize_int32(buf[12:16])/1000000.0
        self.return_params["apparent_power"]         = serialize.deserialize_uint32(buf[16:20])/1000000.0
        self.return_params["reactive_power"]         = serialize.deserialize_int32(buf[20:24])/1000000.0
        self.return_params["frequency"]              = serialize.deserialize_uint32(buf[24:28])/100.0
        self.return_params["power_factor"]           = serialize.deserialize_int32(buf[28:32])/1000.0
        self.return_params["active_energy_imp"]      = serialize.deserialize_uint32(buf[32:36])/100.0
        self.return_params["apparent_energy_imp"]    = serialize.deserialize_uint32(buf[36:40])/100.0
        self.return_params["reactive_energy_imp"]    = serialize.deserialize_uint32(buf[40:44])/100.0
        self.return_params["reactive_energy_exp"]    = serialize.deserialize_uint32(buf[44:48])/100.0
        self.return_params["activeHr_energy_imp"]    = serialize.deserialize_uint32(buf[48:52])/10000.0
        self.return_params["apparentHr_energy_imp"]  = serialize.deserialize_uint32(buf[52:56])/10000.0
        self.return_params["reactiveHr_energy_imp"]  = serialize.deserialize_uint32(buf[56:60])/10000.0
        self.return_params["reactiveHr_energy_exp"]  = serialize.deserialize_uint32(buf[60:64])/10000.0
        
        temp = serialize.deserialize_uint16(buf[64:66])
        live = []
        for i in range(len(liveTamper)):
            if(temp%2):
                live.append(liveTamper[i])
            temp /= 2  


        self.return_params["tamper_event"]           = live
        self.return_params["factory_init_time"]      = datetime.datetime(1970, 1, 1) +\
                                                       datetime.timedelta(seconds=((buf[66]<<24) +\
                                                       (buf[67]<<16) + (buf[68]<<8) + buf[69]))
        if len(payload)>70:
            self.return_params["active_energy_exp"]      = serialize.deserialize_uint32(buf[70:74])/100.0
            self.return_params["apparent_energy_exp"]    = serialize.deserialize_uint32(buf[74:78])/100.0
            self.return_params["activeHr_energy_exp"]    = serialize.deserialize_uint32(buf[78:82])/10000.0
            self.return_params["apparentHr_energy_exp"]  = serialize.deserialize_uint32(buf[82:86])/10000.0
        if len(payload)>86 and len(payload)<=88:
            self.return_params["battery_voltage"]        = serialize.deserialize_uint16(buf[86:88])
            if (self.return_params["battery_voltage"] >= 0 and self.return_params["battery_voltage"] <= 2):
                self.return_params["battery_voltage"] += 1
            else:
                self.return_params["battery_voltage"] = self.return_params["battery_voltage"]/1000.0
        elif len(payload)>88 and len(payload)<=90:
            self.return_params["battery_voltage"]        = serialize.deserialize_uint32(buf[86:90])/1000.0

    def deserialize_nm_ene_by_index(self, payload):
        buf = bytearray()
        buf = payload
        self.return_params["tot_nm_kwh"]     = serialize.deserialize_uint32(buf[0:4], "reverse")/100.0
        temp = serialize.deserialize_uint16(buf[4:6], "reverse")
        self.return_params["tod1_ts"]        = str(temp/60) + ":" + str(temp%60) + ":00"
        self.return_params["tod1_nm_kwh"]    = serialize.deserialize_uint32(buf[6:10], "reverse")/100.0
        self.return_params["tod1_nm_kvah"]   = serialize.deserialize_uint32(buf[10:14], "reverse")/100.0
        temp = serialize.deserialize_uint16(buf[14:16], "reverse")
        self.return_params["tod2_ts"]        = str(temp/60) + ":" + str(temp%60) + ":00"
        self.return_params["tod2_nm_kwh"]    = serialize.deserialize_uint32(buf[16:20], "reverse")/100.0
        self.return_params["tod2_nm_kvah"]   = serialize.deserialize_uint32(buf[20:24], "reverse")/100.0
        temp = serialize.deserialize_uint16(buf[24:26], "reverse")
        self.return_params["tod3_ts"]        = str(temp/60) + ":" + str(temp%60) + ":00"
        self.return_params["tod3_nm_kwh"]    = serialize.deserialize_uint32(buf[26:30], "reverse")/100.0
        self.return_params["tod3_nm_kvah"]   = serialize.deserialize_uint32(buf[30:34], "reverse")/100.0
        temp = serialize.deserialize_uint16(buf[34:36], "reverse")
        self.return_params["tod4_ts"]        = str(temp/60) + ":" + str(temp%60) + ":00"
        self.return_params["tod4_nm_kwh"]    = serialize.deserialize_uint32(buf[36:40], "reverse")/100.0
        self.return_params["tod4_nm_kvah"]   = serialize.deserialize_uint32(buf[40:44], "reverse")/100.0

    def get_nm_ene_by_index_packet(self):
        return ("Total NM kWh           : {} kWh \n"
                "TOD1 TimeStamp         : {}     \n"
                "TOD1 NM kWh            : {} kWh \n"
                "TOD1 NM kVAh           : {} kVAh\n"
                "TOD2 TimeStamp         : {}     \n"
                "TOD2 NM kWh            : {} kWh \n"
                "TOD2 NM kVAh           : {} kVAh\n"
                "TOD3 TimeStamp         : {}     \n"
                "TOD3 NM kWh            : {} kWh \n"
                "TOD3 NM kVAh           : {} kVAh\n"
                "TOD4 TimeStamp         : {}     \n"
                "TOD4 NM kWh            : {} kWh \n"
                "TOD4 NM kVAh           : {} kVAh\n"
               )\
                .format(self.return_params["tot_nm_kwh"],
                        self.return_params["tod1_ts"],
                        self.return_params["tod1_nm_kwh"],
                        self.return_params["tod1_nm_kvah"],
                        self.return_params["tod2_ts"],
                        self.return_params["tod2_nm_kwh"],
                        self.return_params["tod2_nm_kvah"],
                        self.return_params["tod3_ts"],
                        self.return_params["tod3_nm_kwh"],
                        self.return_params["tod3_nm_kvah"],
                        self.return_params["tod4_ts"],
                        self.return_params["tod4_nm_kwh"],
                        self.return_params["tod4_nm_kvah"])

    def deserialize_nxp_ene_HRdebug(self, payload):
        buf = bytearray()
        buf = payload
        bufLen = 0
        self.return_params["MeteringMode"]              =        serialize.deserialize_uint8(buf[bufLen:bufLen+1])
        bufLen += 1     
        self.return_params["activeHr_energy_imp"]       = serialize.deserialize_uint32(buf[bufLen:bufLen+4])/1000000.0
        bufLen += 4     
        self.return_params["activeHr_energy_exp"]       = serialize.deserialize_uint32(buf[bufLen:bufLen+4])/1000000.0
        bufLen += 4
        self.return_params["apparentHr_energy_imp"]     = serialize.deserialize_uint32(buf[bufLen:bufLen+4])/1000000.0
        bufLen += 4 
        self.return_params["apparentHr_energy_exp"]     = serialize.deserialize_uint32(buf[bufLen:bufLen+4])/1000000.0
        bufLen += 4
        self.return_params["reactiveHr_energy_q1"]      = serialize.deserialize_uint32(buf[bufLen:bufLen+4])/1000000.0
        bufLen += 4
        self.return_params["reactiveHr_energy_q2"]      = serialize.deserialize_uint32(buf[bufLen:bufLen+4])/1000000.0
        bufLen += 4
        self.return_params["reactiveHr_energy_q3"]      = serialize.deserialize_uint32(buf[bufLen:bufLen+4])/1000000.0
        bufLen += 4
        self.return_params["reactiveHr_energy_q4"]      = serialize.deserialize_uint32(buf[bufLen:bufLen+4])/1000000.0
        bufLen += 4
        self.return_params["nmHR_energy"]               = serialize.deserialize_uint32(buf[bufLen:bufLen+4])/10000.0
        bufLen += 4
        self.return_params["defraudHR_energy"]          = serialize.deserialize_uint32(buf[bufLen:bufLen+4])/10000.0
        bufLen += 4
        if (len(buf) > bufLen):
            self.return_params["md_kwh_imp"] = serialize.deserialize_uint16(buf[bufLen:bufLen+2])/1000.0
            bufLen += 2
            temp = serialize.deserialize_uint32(buf[bufLen:bufLen+4])
            bufLen += 4
            self.return_params["md_kwh_imp_ts"] = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=temp)
            self.return_params["md_kwh_exp"] = serialize.deserialize_uint16(buf[bufLen:bufLen+2])/1000.0
            bufLen += 2
            temp = serialize.deserialize_uint32(buf[bufLen:bufLen+4])
            bufLen += 4
            self.return_params["md_kwh_exp_ts"] = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=temp)
            self.return_params["md_kvah_imp"] = serialize.deserialize_uint16(buf[bufLen:bufLen+2])/1000.0
            bufLen += 2
            temp = serialize.deserialize_uint32(buf[bufLen:bufLen+4])
            bufLen += 4
            self.return_params["md_kvah_imp_ts"] = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=temp)
            self.return_params["md_kvah_exp"] = serialize.deserialize_uint16(buf[bufLen:bufLen+2])/1000.0
            bufLen += 2
            temp = serialize.deserialize_uint32(buf[bufLen:bufLen+4])
            bufLen += 4
            self.return_params["md_kvah_exp_ts"] = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=temp)

    def deserialize_nxp_ene_by_index(self, payload):
        buf = bytearray()
        buf = payload
        self.return_params["active_energy_imp"]     = serialize.deserialize_uint32(buf[0:4], "reverse")/100.0
        self.return_params["active_energy_exp"]     = serialize.deserialize_uint32(buf[4:8], "reverse")/100.0
        self.return_params["apparent_energy_imp"]   = serialize.deserialize_uint32(buf[8:12], "reverse")/100.0
        self.return_params["apparent_energy_exp"]   = serialize.deserialize_uint32(buf[12:16], "reverse")/100.0
        self.return_params["reactive_energy_imp"]   = serialize.deserialize_uint32(buf[16:20], "reverse")/100.0
        self.return_params["reactive_energy_exp"]   = serialize.deserialize_uint32(buf[20:24], "reverse")/100.0

    def get_nxp_ene_by_index_packet(self):
        return ("active_energy_imp      : {} KWh    \n"
                "active_energy_exp      : {} KWh    \n"
                "apparent_energy_imp    : {} KVAh   \n"
                "apparent_energy_exp    : {} KVAh   \n"
                "reactive_energy_imp    : {} KVArh  \n"
                "reactive_energy_exp    : {} KVArh  \n"
               )\
                .format(self.return_params["active_energy_imp"],
                        self.return_params["active_energy_exp"],
                        self.return_params["apparent_energy_imp"],
                        self.return_params["apparent_energy_exp"],
                        self.return_params["reactive_energy_imp"],
                        self.return_params["reactive_energy_exp"])

    def get_metering_data_2(self):
        return ("Temprature      : {} C    \n"
            )\
            .format(self.return_params["Temprature"])
                
    def deserialize_metering_data_2(self, payload):
        buf = bytearray()
        buf = payload
        self.return_params["Temprature"]     = serialize.deserialize_int32(buf[0:4])/1000.0            

    def deserialize_nxp_ene_debug(self, payload):
        buf = bytearray()
        buf = payload
        self.return_params["active_energy_imp"]     = serialize.deserialize_uint32(buf[0:4])/100.0
        self.return_params["active_energy_exp"]     = serialize.deserialize_uint32(buf[4:8])/100.0
        self.return_params["apparent_energy_imp"]   = serialize.deserialize_uint32(buf[8:12])/100.0
        self.return_params["apparent_energy_exp"]   = serialize.deserialize_uint32(buf[12:16])/100.0
        self.return_params["reactive_energy_imp"]   = serialize.deserialize_uint32(buf[16:20])/100.0
        self.return_params["reactive_energy_exp"]   = serialize.deserialize_uint32(buf[20:24])/100.0

    def get_nxp_ene_debug_packet(self):
        return ("Lib_active_energy_imp      : {} KWh    \n"
                "Lib_active_energy_exp      : {} KWh    \n"
                "Lib_apparent_energy_imp    : {} KVAh   \n"
                "Lib_apparent_energy_exp    : {} KVAh   \n"
                "Lib_reactive_energy_imp    : {} KVArh  \n"
                "Lib_reactive_energy_exp    : {} KVArh  \n"
               )\
                .format(self.return_params["active_energy_imp"],
                        self.return_params["active_energy_exp"],
                        self.return_params["apparent_energy_imp"],
                        self.return_params["apparent_energy_exp"],
                        self.return_params["reactive_energy_imp"],
                        self.return_params["reactive_energy_exp"])
    def get_nxp_ene_debug_packet_hr(self):
        return ("Metering_Mode               : {}        \n"
                "ActiveHr_energy_imp         : {} KWh    \n"
                "ActiveHr_energy_exp         : {} KWh    \n"
                "ApparentHr_energy_imp       : {} KVAh   \n"
                "ApparentHr_energy_exp       : {} KVAh   \n"
                "ReactiveHr_energy_q1        : {} KVArh  \n"
                "ReactiveHr_energy_q2        : {} KVArh  \n"
                "ReactiveHr_energy_q3        : {} KVArh  \n"
                "ReactiveHr_energy_q4        : {} KVArh  \n"
                "NmHR_energy                 : {} KWh    \n"
                "DefraudHR_energy            : {} KWh    \n"
               )\
                .format(self.return_params["MeteringMode"],
                        self.return_params["activeHr_energy_imp"],
                        self.return_params["activeHr_energy_exp"],
                        self.return_params["apparentHr_energy_imp"],
                        self.return_params["apparentHr_energy_exp"],
                        self.return_params["reactiveHr_energy_q1"],
                        self.return_params["reactiveHr_energy_q2"],
                        self.return_params["reactiveHr_energy_q3"],
                        self.return_params["reactiveHr_energy_q4"],
                        self.return_params["nmHR_energy"],
                        self.return_params["defraudHR_energy"])