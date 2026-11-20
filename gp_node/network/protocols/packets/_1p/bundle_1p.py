import datetime
import gp_node.utils.serialize as serialize
import time
from gp_node.utils.serialize import deserialize_int16
from gp_node.utils.serialize import deserialize_int32
from gp_node.utils.serialize import deserialize_uint32
from gp_node.utils import TamperFlag

class  DCUBundlePacket(object):

    def __init__(self):
        """
        The constructor instantiates a default dictionary to store the ecop data
        """
        dt = datetime.datetime(1970, 1, 1)
        self.return_params = {
                "date_time":dt
                ,"meter_type ":0
                ,"voltage":0.00
                ,"phase_current":0.000
                ,"neutral_current":0.00
                ,"avg_pf":0.00
                ,"cumm_total_real_energy":0.000
                ,"cumm_total_real_energy_exp":0.000
                ,"cumm_total_apparent_energy":0.000
                ,"cumm_total_apparent_energy_exp":0.000
                ,"cumm_total_reactive_energy":0.00
                ,"total_real_power":0.000
                ,"total_apparent_power": 0.000
                ,"reactive_power":0.00
                ,"avg_frequency":0
                ,"credits_left":0.00
                ,"live_tamper_flags":[]
                ,"exist_tamper_flags":[]
                ,"current_events":0.00
                ,"power_events":0.00
                ,"others_events":0.00
                ,"voltage_events":0
                ,"data_valid":0.00
                ,"kw_md_flag":0
                ,"kva_md_flag":0
                ,"relay_state":0
                ,"current_tariff_grp":"DATA_NOT_AVAILABLE"
                ,"prepaid_status":"DATA_NOT_AVAILABLE"
                ,"account_status":"DATA_NOT_AVAILABLE"
                ,"control_Mode":"DATA_NOT_AVAILABLE"
                ,"total_net_recharge":0.0
                ,"current_net_recharge":0.0
                ,"DG_energy_consumed":0.0
                ,"EG_energy_consumed":0.0
                ,"DG_energy_amount_deducted":0.0
                ,"EG_energy_amount_deducted":0.0
                ,"current_running_price":0.0
                ,"cummulative_FDCost":0.0
                ,"Meter_Serial_Number":0
                ,"live_version":0
                ,"hw_version":"unknown"
                ,"billType":"kWh"}

    def __str__(self):
        """
        Prints out the stored information in the dictionary.
        Useful along with print statements.
        ex: print EcopDataStreamPacket()
        :param :none
        :return :none
        """
        return ("Packet Type                   : {}\n"
                "date & time                   : {}\n"
                "Firmware version              : {}\n"
                "Hardware version              : {}\n"
                "Phase Voltage                 : {} V\n"
                "Phase Current                 : {} A\n"
                "Neutral current               : {}\n"
                "Avg Pf                        : {}\n"
                "Cumm Active Energy Imp        : {} WH\n"
                "Cumm Active Energy Exp        : {} WH\n"
                "Cumm Apparent Energy Imp      : {} VAh\n"
                "Cumm Apparent Energy Exp      : {} VAh\n"
                "Cumm Reactive Energy          : {} VArh\n"
                "Active Power                  : {} W\n"
                "Apparent Power                : {} VA\n"   
                "Reactive Power                : {} VAr\n"
                "Frequency                     : {} Hz\n"
                "Credits Left                  : {} credits\n"
                "Live Tampers                  : {}\n"
                "No Of Current Related Events  : {}\n"
                "No Of Power Related Events    : {}\n"
                "No Of Others Related Events   : {}\n"
                "No Of Voltage Related Events  : {}\n"
                "Data Valid                    : {}\n"
                "Active MD Change Flag         : {}\n"
                "Apparent MD Change Flag       : {}\n"
                "Relay Status                  : {}\n"    
                "Activated Tariff Group        : {}\n"
                "Prepaid Status                : {}\n"
                "Account Status                : {}\n"
                "Relay Control Mode            : {}\n"
                "Total Net Recharge            : {}\n"
                "Current Net Recharge          : {}\n"
                "DG Energy Consumed            : {}\n"
                "EG Energy Consumed            : {}\n"                     
                "DG Energy Deducted Amount     : {}\n"                     
                "EG Energy Deducted Amount     : {}\n"                     
                "Current Running Price         : {}\n"
                "Cummulative Total FD Cost     : {}\n"
                "Meter Serial Number           : {}   ")\
                .format(self.return_params["meter_type"],
                        self.return_params["date_time"],
                        self.return_params["live_version"],
                        self.return_params["hw_version"],
                        self.return_params["voltage"],
                        self.return_params["phase_current"],
                        self.return_params["neutral_current"],
                        self.return_params["avg_pf"],
                        self.return_params["cumm_total_real_energy"],
                        self.return_params["cumm_total_real_energy_exp"],
                        self.return_params["cumm_total_apparent_energy"],
                        self.return_params["cumm_total_apparent_energy_exp"],
                        self.return_params["cumm_total_reactive_energy"],
                        self.return_params["total_real_power"],
                        self.return_params["total_apparent_power"],
                        self.return_params["reactive_power"],
                        self.return_params["avg_frequency"],
                        self.return_params["credits_left"],
                        self.return_params["live_tamper_flags"],
                        self.return_params["current_events"],
                        self.return_params["power_events"],
                        self.return_params["others_events"],
                        self.return_params["voltage_events"],
                        self.return_params["data_valid"],
                        self.return_params["kw_md_flag"],
                        self.return_params["kva_md_flag"],
                        self.return_params["relay_state"],
                        self.return_params["current_tariff_grp"],
                        self.return_params["prepaid_status"],
                        self.return_params["account_status"],
                        self.return_params["control_Mode"],
                        self.return_params["total_net_recharge"],
                        self.return_params["current_net_recharge"],
                        self.return_params["DG_energy_consumed"],
                        self.return_params["EG_energy_consumed"],
                        self.return_params["DG_energy_amount_deducted"],
                        self.return_params["EG_energy_amount_deducted"],
                        self.return_params["current_running_price"],
                        self.return_params["cummulative_FDCost"],
                        self.return_params["Meter_Serial_Number"])

    def deserialize_packet_bundle_new(self,payload):
        """
        Deserializes the input payload and populates the data to the default
        dictionary.This API needs to be used to retrieve information from the 
        reply bytestream.
        :param payload:input bytestream
        :return :none
        """
        bytes = bytearray()
        bytes = payload
        #print "Deserializing"
        #print "length of payload",len(payload)
        # temp = bytearray()
        # temp.extend(payload)
        # for byte in temp:
        #     print hex(byte)
        self.return_params["meter_type"] = bytes[0] 
        dt = datetime.datetime(1970, 1, 1) +\
                datetime.timedelta(seconds=((bytes[1]<<24) +\
                    (bytes[2]<<16) + (bytes[3]<<8) + bytes[4]))
        self.return_params["date_time"] = dt
        self.return_params["voltage"] =  ((bytes[5]<<8) + bytes[6])/100.0
        self.return_params["phase_current"] =  (serialize.deserialize_int24(bytes[7:10]))/100.0
        self.return_params["neutral_current"] =  (serialize.deserialize_int24(bytes[10:13]))/100.0
        self.return_params["avg_pf"] = (serialize.deserialize_int16(bytes[13:15]))/1000.0 
        self.return_params["cumm_total_real_energy"] = (serialize.deserialize_int32(bytes[15:19]))*10.0
        self.return_params["cumm_total_apparent_energy"] = (serialize.deserialize_int32(bytes[19:23]))*10.0
        self.return_params["cumm_total_reactive_energy"] = (serialize.deserialize_int32(bytes[23:27]))*10.0
        self.return_params["total_real_power"] = (serialize.deserialize_int32(bytes[27:31]))/1000.0
        self.return_params["total_apparent_power"] =  (serialize.deserialize_int32(bytes[31:35]))/1000.0
        self.return_params["reactive_power"] =  (serialize.deserialize_int32(bytes[35:39]))/1000.0
        self.return_params["avg_frequency"] = ((bytes[39]<<8) + bytes[40])/100.0
        self.return_params["credits_left"] =  (serialize.deserialize_int32(bytes[41:45]))/100.0
        instant_tamper_tmp = bytes[45]
        #print "tampers ", instant_tamper_tmp 
        self.tamper_events = []
        if ((instant_tamper_tmp/2**0 % 2) == 1):
            self.tamper_events.append(TamperFlag("EARTH"))
            #instant_tamper_tmp = instant_tamper_tmp - 32
        if ((instant_tamper_tmp/2**1 % 2) == 1):
            self.tamper_events.append(TamperFlag("LINE_LOAD_REVERSAL"))
            #instant_tamper_tmp = instant_tamper_tmp - 16
        if ((instant_tamper_tmp/2**2 % 2) == 1):
            self.tamper_events.append(TamperFlag("MAGNETIC"))
            #instant_tamper_tmp = instant_tamper_tmp - 8
        if ((instant_tamper_tmp/2**3 % 2) == 1):
            self.tamper_events.append(TamperFlag("COVER_OPEN"))
            #instant_tamper_tmp = instant_tamper_tmp - 4
        if ((instant_tamper_tmp/2**4 % 2) == 1):
            self.tamper_events.append(TamperFlag("NEUTRAL_MISSING"))

        if ((instant_tamper_tmp/2**5 % 2) == 1):
            self.tamper_events.append(TamperFlag("NEUTRAL_DISTURBANCE"))
        # if ((instant_tamper_tmp/2**6 % 2) == 1):
        #     self.tamper_events.append(TamperFlag("LOW_VOLTAGE"))
        # if ((instant_tamper_tmp/2**7 % 2) == 1):
        #     self.tamper_events.append(TamperFlag("HIGH_VOLTAGE"))
        self.tamper_flags = self.tamper_events

        self.return_params["live_tamper_flags"] =  self.tamper_flags

        occured_tampered_tamp = ((bytes[46]<<8) + bytes[47])
        #hex_tamper = hex(occured_tampered_tamp)
        
        current_releated = occured_tampered_tamp & 0xF000
        current_releated = (current_releated >> 12) 

        power_releated = occured_tampered_tamp & 0xF00
        power_releated = (power_releated >> 8)

        others_related = occured_tampered_tamp & 0x00F0
        others_related = (others_related >> 4)

        voltage_related = occured_tampered_tamp & 0x000F

        self.return_params["others_events"] = others_related
        self.return_params["power_events"] = power_releated
        self.return_params["current_events"] = current_releated
        self.return_params["voltage_events"] = voltage_related
        self.return_params["data_valid"] = bytes[48] & 0x01
        
        if(self.return_params["data_valid"]):
            self.return_params["data_valid"] = "DATA_VALID"
        else:
            self.return_params["data_valid"] = "DATA_INVALID"
        
        #print bytes[48]
        active_flag  = bytes[48] & 0x02

        if(active_flag == 0x02):
            self.return_params["kw_md_flag"] = 0x01
        else:
            self.return_params["kw_md_flag"] = 0x00

        apparent_flag = bytes[48] & 0x04
        if(apparent_flag == 0x04):
            self.return_params["kva_md_flag"]  = 0x01
        else:
            self.return_params["kva_md_flag"]  = 0x00

        relay_sw_off_reasons = bytes[48] & 0xF8
        relay_sw_off_reasons = relay_sw_off_reasons >> 3
        self.return_params["relay_state"]  = relay_sw_off_reasons

        prepaid_flag = bytes[50]


        a = prepaid_flag & 0x80

        if a > 0:
            self.return_params["current_tariff_grp"]   =  "EG Tariff Activated"   
        else:
            self.return_params["current_tariff_grp"]   =  "DG Tariff Activated"

        b = prepaid_flag & 0x40

        if b > 0:
            self.return_params["prepaid_status"]       =  "Prepaid Activated"
        else:
            self.return_params["prepaid_status"]       =  "Prepaid Deactivated"

        temp2 = (prepaid_flag & 0x38)
        temp2 = temp2 >> 3

        if temp2 == 0:            
            self.return_params["account_status"]             = "ACC_NO_BALANCE"        
        elif temp2 == 1:
            self.return_params["account_status"]             = "ACC_NO_BALANCE_FRIENDLY_HOURS"
        elif temp2 == 2:
            self.return_params["account_status"]             = "ACC_EMERGENCY_CREDIT"
        elif temp2 == 3:
            self.return_params["account_status"]             = "ACC_LOW_BALANCE"
        elif temp2 == 4:   
            self.return_params["account_status"]             = "ACC_ENOUGH_BALANCE"   
        elif temp2 == 5:   
            self.return_params["account_status"]             = "ACC_PREPAID_DISABLED"   
        elif temp2 == 6:   
            self.return_params["account_status"]             = "ACC_DATA_NOT_AVAILABLE"

        temp = (prepaid_flag & 0x07)

        if temp == 1:
            self.return_params["control_Mode"] = "AUTO_CONTROL_ON"
        elif temp == 2:
            self.return_params["control_Mode"] = "AUTO_CONTROL_OFF"
        elif temp == 3:
            self.return_params["control_Mode"] = "MANUAL_CONTROL_ON"
        elif temp == 4:     
            self.return_params["control_Mode"] = "MANUAL_CONTROL_OFF"

        self.return_params["total_net_recharge"] =          serialize.deserialize_int32(bytes[51:55])/100.00
        self.return_params["current_net_recharge"] =        serialize.deserialize_int32(bytes[55:59])/100.00    
        self.return_params["DG_energy_consumed"] =          serialize.deserialize_uint32(bytes[59:63])/100.00
        self.return_params["EG_energy_consumed"] =          serialize.deserialize_uint32(bytes[63:67])/100.00
        self.return_params["DG_energy_amount_deducted"] =   serialize.deserialize_uint32(bytes[67:71])/100.00        
        self.return_params["EG_energy_amount_deducted"] =   serialize.deserialize_uint32(bytes[71:75])/100.00        
        self.return_params["current_running_price"] =       serialize.deserialize_uint16(bytes[75:77])/100.00
        if len(payload) > 77:
            self.return_params["cummulative_FDCost"] =   serialize.deserialize_uint32(bytes[77:81])/100.00
            self.return_params["Meter_Serial_Number"] =   serialize.deserialize_uint32(bytes[81:85])
            version = serialize.deserialize_uint16(bytes[85:87])
            self.return_params["live_version"] = version % 10000

            version = version/10000
            if(version == 0):
                self.return_params["hw_version"] = "3.3 PCB"
            elif (version == 1):
                self.return_params["hw_version"] = "3.3I PCB"
            elif (version == 2):
                self.return_params["hw_version"] = "WIFI PCB"
            elif (version == 3):
                self.return_params["hw_version"] = "4.1 PCB"
            elif (version == 4):
                self.return_params["hw_version"] = "6.0 PCB"
            else:
                self.return_params["hw_version"] = "unknown"

        if len(payload) > 87:
            self.return_params["cumm_total_real_energy_exp"] = (serialize.deserialize_int32(bytes[87:91]))*10.0
            self.return_params["cumm_total_apparent_energy_exp"] = (serialize.deserialize_int32(bytes[91:95]))*10.0
        if len(payload) > 95 and payload[95]==0:
            self.return_params["billType"] = "kVAh"              

    def deserialize_packet_bundle(self,payload):
        """
        Deserializes the input payload and populates the data to the default
        dictionary.This API needs to be used to retrieve information from the 
        reply bytestream.
        :param payload:input bytestream
        :return :none
        """
        if len(payload)>88:
            self.deserialize_packet_bundle_new(payload)
            return

        bytes = bytearray()
        bytes = payload
        #print "Deserializing"
        #print "length of payload",len(payload)
        # temp = bytearray()
        # temp.extend(payload)
        # for byte in temp:
        #     print hex(byte)
        self.return_params["meter_type"] = bytes[0] 
        dt = datetime.datetime(1970, 1, 1) +\
                datetime.timedelta(seconds=((bytes[1]<<24) +\
                    (bytes[2]<<16) + (bytes[3]<<8) + bytes[4]))
        self.return_params["date_time"] = dt
        self.return_params["voltage"] =  ((bytes[5]<<8) + bytes[6])/100.0
        self.return_params["phase_current"] =  (serialize.deserialize_int24(bytes[7:10]))/100.0
        self.return_params["neutral_current"] =  (serialize.deserialize_int24(bytes[10:13]))/100.0
        self.return_params["avg_pf"] = (serialize.deserialize_int16(bytes[13:15]))/1000.0 
        self.return_params["cumm_total_real_energy"] = (serialize.deserialize_int32(bytes[15:19]))*10.0
        self.return_params["cumm_total_apparent_energy"] = (serialize.deserialize_int32(bytes[19:23]))*10.0
        self.return_params["cumm_total_reactive_energy"] = (serialize.deserialize_int32(bytes[23:27]))*10.0
        self.return_params["total_real_power"] = (serialize.deserialize_int32(bytes[27:31]))/1000.0
        # self.return_params["total_apparent_power"] =  (serialize.deserialize_int32(bytes[31:35]))/1000.0
        self.return_params["reactive_power"] =  (serialize.deserialize_int32(bytes[35:39]))/1000.0
        self.return_params["avg_frequency"] = ((bytes[39]<<8) + bytes[40])/100.0
        self.return_params["credits_left"] =  (serialize.deserialize_int32(bytes[41:45]))/100.0
        instant_tamper_tmp = bytes[45]
        #print "tampers ", instant_tamper_tmp 
        self.tamper_events = []
        if ((instant_tamper_tmp/2**0 % 2) == 1):
            self.tamper_events.append(TamperFlag("EARTH"))
            #instant_tamper_tmp = instant_tamper_tmp - 32
        if ((instant_tamper_tmp/2**1 % 2) == 1):
            self.tamper_events.append(TamperFlag("LINE_LOAD_REVERSAL"))
            #instant_tamper_tmp = instant_tamper_tmp - 16
        if ((instant_tamper_tmp/2**2 % 2) == 1):
            self.tamper_events.append(TamperFlag("MAGNETIC"))
            #instant_tamper_tmp = instant_tamper_tmp - 8
        if ((instant_tamper_tmp/2**3 % 2) == 1):
            self.tamper_events.append(TamperFlag("COVER_OPEN"))
            #instant_tamper_tmp = instant_tamper_tmp - 4
        if ((instant_tamper_tmp/2**4 % 2) == 1):
            self.tamper_events.append(TamperFlag("NEUTRAL_MISSING"))

        if ((instant_tamper_tmp/2**5 % 2) == 1):
            self.tamper_events.append(TamperFlag("NEUTRAL_DISTURBANCE"))
        # if ((instant_tamper_tmp/2**6 % 2) == 1):
        #     self.tamper_events.append(TamperFlag("LOW_VOLTAGE"))
        # if ((instant_tamper_tmp/2**7 % 2) == 1):
        #     self.tamper_events.append(TamperFlag("HIGH_VOLTAGE"))
        self.tamper_flags = self.tamper_events

        self.return_params["live_tamper_flags"] =  self.tamper_flags

        occured_tampered_tamp = ((bytes[46]<<8) + bytes[47])
        #hex_tamper = hex(occured_tampered_tamp)
        
        current_releated = occured_tampered_tamp & 0xF000
        current_releated = (current_releated >> 12) 

        power_releated = occured_tampered_tamp & 0xF00
        power_releated = (power_releated >> 8)

        others_related = occured_tampered_tamp & 0x00F0
        others_related = (others_related >> 4)

        voltage_related = occured_tampered_tamp & 0x000F

        self.return_params["others_events"] = others_related
        self.return_params["power_events"] = power_releated
        self.return_params["current_events"] = current_releated
        self.return_params["voltage_events"] = voltage_related
        self.return_params["data_valid"] = bytes[48] & 0x01
        
        if(self.return_params["data_valid"]):
            self.return_params["data_valid"] = "DATA_VALID"
        else:
            self.return_params["data_valid"] = "DATA_INVALID"
        
        #print bytes[48]
        active_flag  = bytes[48] & 0x02

        if(active_flag == 0x02):
            self.return_params["kw_md_flag"] = 0x01
        else:
            self.return_params["kw_md_flag"] = 0x00

        apparent_flag = bytes[48] & 0x04
        if(apparent_flag == 0x04):
            self.return_params["kva_md_flag"]  = 0x01
        else:
            self.return_params["kva_md_flag"]  = 0x00

        relay_sw_off_reasons = bytes[48] & 0xF8
        relay_sw_off_reasons = relay_sw_off_reasons >> 3
        self.return_params["relay_state"]  = relay_sw_off_reasons

        prepaid_flag = bytes[50]


        a = prepaid_flag & 0x80

        if a > 0:
            self.return_params["current_tariff_grp"]   =  "EG Tariff Activated"   
        else:
            self.return_params["current_tariff_grp"]   =  "DG Tariff Activated"

        b = prepaid_flag & 0x40

        if b > 0:
            self.return_params["prepaid_status"]       =  "Prepaid Activated"
        else:
            self.return_params["prepaid_status"]       =  "Prepaid Deactivated"

        temp2 = (prepaid_flag & 0x38)
        temp2 = temp2 >> 3

        if temp2 == 0:            
            self.return_params["account_status"]             = "ACC_NO_BALANCE"        
        elif temp2 == 1:
            self.return_params["account_status"]             = "ACC_NO_BALANCE_FRIENDLY_HOURS"
        elif temp2 == 2:
            self.return_params["account_status"]             = "ACC_EMERGENCY_CREDIT"
        elif temp2 == 3:
            self.return_params["account_status"]             = "ACC_LOW_BALANCE"
        elif temp2 == 4:   
            self.return_params["account_status"]             = "ACC_ENOUGH_BALANCE"   
        elif temp2 == 5:   
            self.return_params["account_status"]             = "ACC_PREPAID_DISABLED"   
        elif temp2 == 6:   
            self.return_params["account_status"]             = "ACC_DATA_NOT_AVAILABLE"

        temp = (prepaid_flag & 0x07)

        if temp == 1:
            self.return_params["control_Mode"] = "AUTO_CONTROL_ON"
        elif temp == 2:
            self.return_params["control_Mode"] = "AUTO_CONTROL_OFF"
        elif temp == 3:
            self.return_params["control_Mode"] = "MANUAL_CONTROL_ON"
        elif temp == 4:     
            self.return_params["control_Mode"] = "MANUAL_CONTROL_OFF"

        self.return_params["total_net_recharge"] =          serialize.deserialize_int32(bytes[31:35])/100.00
        self.return_params["current_net_recharge"] =        serialize.deserialize_int32(bytes[51:55])/100.00    
        self.return_params["DG_energy_consumed"] =          serialize.deserialize_uint32(bytes[55:59])/100.00
        self.return_params["EG_energy_consumed"] =          serialize.deserialize_uint32(bytes[59:63])/100.00
        self.return_params["DG_energy_amount_deducted"] =   serialize.deserialize_uint32(bytes[63:67])/100.00        
        self.return_params["EG_energy_amount_deducted"] =   serialize.deserialize_uint32(bytes[67:71])/100.00        
        self.return_params["current_running_price"] =       serialize.deserialize_uint16(bytes[71:73])/100.00
        # if len(payload) > 77:
        # self.return_params["cummulative_FDCost"] =   serialize.deserialize_uint32(bytes[77:81])/100.00
        self.return_params["Meter_Serial_Number"] =   serialize.deserialize_uint24(bytes[73:76])
        version = serialize.deserialize_uint16(bytes[76:78])
        self.return_params["live_version"] = version % 10000

        version = version/10000
        if(version == 0):
            self.return_params["hw_version"] = "3.3 PCB"
        elif (version == 1):
            self.return_params["hw_version"] = "3.3I PCB"
        elif (version == 2):
            self.return_params["hw_version"] = "WIFI PCB"
        elif (version == 3):
            self.return_params["hw_version"] = "4.1 PCB"
        elif (version == 4):
            self.return_params["hw_version"] = "6.0 PCB"
        else:
            self.return_params["hw_version"] = "unknown"

        # if len(payload) > 87:
        self.return_params["cumm_total_real_energy_exp"] = (serialize.deserialize_int32(bytes[78:82]))*10.0
        self.return_params["cumm_total_apparent_energy_exp"] = (serialize.deserialize_int32(bytes[82:86]))*10.0
        if payload[86]==0:
            self.return_params["billType"] = "kVAh"

          
    
    def get_packet_bundle(self):
        """
        Prints out the stored information in the dictionary.
        Useful along with print statements.
        ex: print EcopDataStreamPacket()
        :param :none
        :return :none
        """
        return ("Meter Type                    : {}\n"
                "Prepaid Bill Type             : {}\n"
                "Date & time                   : {}\n"
                "Firmware version              : {}\n"
                "Hardware version              : {}\n"
                "Phase Voltage                 : {} V\n"
                "Phase Current                 : {} A\n"
                "Neutral current               : {} A\n"
                "Avg Pf                        : {}\n"
                "Cumm Active Energy Imp        : {} WH\n"
                "Cumm Active Energy Exp        : {} WH\n"
                "Cumm Apparent Energy Imp      : {} VAh\n"
                "Cumm Apparent Energy Exp      : {} VAh\n"
                "Cumm Reactive Energy          : {} VArh\n"
                "Active Power                  : {} W\n"
                "Apparent Power                : {} VA\n"   
                "Reactive Power                : {} VAr\n"
                "Frequency                     : {} Hz\n"
                "Credits Left                  : {} credits\n"
                "Live Tampers                  : {}\n"
                "No Of Current Related Events  : {}\n"
                "No Of Power Related Events    : {}\n"
                "No Of Others Related Events   : {}\n"
                "No Of Voltage Related Events  : {}\n"
                "Data Valid                    : {}\n"
                "Active MD Change Flag         : {}\n"
                "Apparent MD Change Flag       : {}\n"
                "Relay Status                  : {}\n"
                "Activated Tariff Group        : {}\n"
                "Prepaid Status                : {}\n"
                "Account Status                : {}\n"
                "Relay Control Mode            : {}\n"
                "Total Net Recharge            : {} Rs\n"
                "Current Net Recharge          : {} Rs\n"
                "DG Energy Consumed            : {} {}\n"
                "EG Energy Consumed            : {} {}\n"                     
                "DG Energy Deducted Amount     : {} Rs\n"                     
                "EG Energy Deducted Amount     : {} Rs\n"                     
                "Current Running Price         : {} Rs\n"
                "Cummulative Total FD Cost     : {} Rs\n"
                "Meter Serial Number           : {}   ")\
                .format(self.return_params["meter_type"],
                        self.return_params["billType"],
                        self.return_params["date_time"],
                        self.return_params["live_version"],
                        self.return_params["hw_version"],
                        self.return_params["voltage"],
                        self.return_params["phase_current"],
                        self.return_params["neutral_current"],
                        self.return_params["avg_pf"],
                        self.return_params["cumm_total_real_energy"],
                        self.return_params["cumm_total_real_energy_exp"],
                        self.return_params["cumm_total_apparent_energy"],
                        self.return_params["cumm_total_apparent_energy_exp"],
                        self.return_params["cumm_total_reactive_energy"],
                        self.return_params["total_real_power"],
                        self.return_params["total_apparent_power"],
                        self.return_params["reactive_power"],
                        self.return_params["avg_frequency"],
                        self.return_params["credits_left"],
                        self.return_params["live_tamper_flags"],
                        self.return_params["current_events"],
                        self.return_params["power_events"],
                        self.return_params["others_events"],
                        self.return_params["voltage_events"],
                        self.return_params["data_valid"],
                        self.return_params["kw_md_flag"],
                        self.return_params["kva_md_flag"],
                        self.return_params["relay_state"],
                        self.return_params["current_tariff_grp"],
                        self.return_params["prepaid_status"],
                        self.return_params["account_status"],
                        self.return_params["control_Mode"],
                        self.return_params["total_net_recharge"],
                        self.return_params["current_net_recharge"],
                        self.return_params["DG_energy_consumed"],self.return_params["billType"],
                        self.return_params["EG_energy_consumed"],self.return_params["billType"],
                        self.return_params["DG_energy_amount_deducted"],
                        self.return_params["EG_energy_amount_deducted"],
                        self.return_params["current_running_price"],
                        self.return_params["cummulative_FDCost"],
                        self.return_params["Meter_Serial_Number"])

if __name__ == "__main__":
    data = bytearray([100, 236, 210, 144, 4, 162, 41, 171, 27, 98, 148, 98, 201, 98, 157, 2, 237, 0, 7, 5, 63, 0, 0, 3, 223, 3, 94, 3, 231, 3, 228, 19, 135, 2, 14, 0, 0, 0, 0, 0, 0, 144, 238, 0, 0, 146, 123, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 108, 0, 2, 192, 16, 0, 25, 3, 133, 0, 0, 0, 9, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 100, 236, 210, 144])
    print (len(data))
    bdl = DCUBundlePacket()
    bdl.deserialize_packet_bundle(data)
    print (bdl.get_packet_bundle())