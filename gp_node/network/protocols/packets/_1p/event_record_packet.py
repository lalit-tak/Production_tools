import datetime
import time 
import gp_node.utils.serialize as serialize

full_event_log = 0

class EventRecordPacket(object):

    VALID_EVENT_NAMES = {   0 :'EVT_NONE',
                            # Current Related
                            69  : 'EVT_EARTH_LOADING_OCCURRENCE',
                            70  : 'EVT_EARTH_LOADING_RESTORATION',
                            67  : 'EVT_OVER_CURRENT_OCCURRENCE',
                            68  : 'EVT_OVER_CURRENT_RESTORATION',
                            51  : 'EVT_REVERSE_OCCURRENCE',
                            52  : 'EVT_REVERSE_RESTORATION',
                            # Voltage Related
                             7  : 'EVT_OVER_VOLTAGE_OCCURRENCE',
                             8  : 'EVT_OVER_VOLTAGE_RESTORATION',
                             9  : 'EVT_LOW_VOLTAGE_OCCURRENCE',
                            10  : 'EVT_LOW_VOLTAGE_RESTORATION',
                            # Power Related
                            101 :'EVT_POWER_FAILURE_OCCURRENCE',
                            102 :'EVT_POWER_FAILURE_RESTORATION',
                            # Transactions Related
                            151 :'EVT_RTC_DATETIME_SET',
                            152 :'EVT_DEMAND_PERIOD_SET',
                            153 :'EVT_PROFILE_PERIOD_SET',
                            154 :'EVT_BILLING_SCHEDULE_SET',
                            155 :'EVT_ACTIVITY_CALANDER_SET',
                            157 :'EVT_FIRMWARE_UPGRADE_OCCURANCE',
                            158 :'EVT_LOAD_LIMIT_SET',
                            159 :'EVT_LOAD_LIMIT_ENABLE',
                            160 :'EVT_LOAD_LIMIT_DISABLE',
                            161 :'EVT_LLS_MR_KEY_CHANGE',
                            162 :'EVT_HLS_US_KEY_CHANGE',
                            163 :'EVT_HLS_FW_KEY_CHANGE',
                            164 :'EVT_GLOBAL_KEY_CHANGE',
                            165 :'EVT_STATUS_WORD_FLAG_CHANGE', 
                            166 :'EVT_MD_RESET_OCCURANCE',
                            # Other Related
                            201 :'EVT_MAGNETIC_TAMPER_OCCURANCE',
                            202 :'EVT_MAGNETIC_TAMPER_RESTORATION',
                            203 :'EVT_ND_TAMPER_OCCURANCE',
                            204 :'EVT_ND_TAMPER_RESTORATION',
                            205 :'EVT_LOW_PF_OCCURENCE',
                            206 :'EVT_LOW_PF_RESTORATION',
                            207 :'EVT_NM_TAMPER_OCCURANCE',
                            208 :'EVT_NM_TAMPER_RESTORATION',
                            209 :'EVT_COMM_MOD_REMOVAL_OCCURANCE',
                            210 :'EVT_COMM_MOD_REMOVAL_RESTORATION',
                            211 :'EVT_CHANGE_TO_POSTPAID',
                            212 :'EVT_CHANGE_TO_PREPAID',
                            213 :'EVT_CHANGE_TO_FORWARD_MODE',
                            214 :'EVT_CHANGE_TO_IMP_EXP_MODE',
                            215 :'EVT_OVERLOAD_OCCURANCE',
                            216 :'EVT_OVERLOAD_RESTORATION',
                            239 :'EVT_FREQ_MALF_OCCURENCE',
                            240 :'EVT_FREQ_MALF_RESTORATION',
                            # Non-Rollover Related
                            251:'EVT_COVER_OPEN_OCCURANCE',
                            252:'EVT_SWITCH_WELD_OCCURANCE',
                            # Control Related
                            301 :'EVT_LOAD_SWITCH_DISCONNECTED',
                            302 :'EVT_LOAD_SWITCH_CONNECTED',
                            303 :'EVT_ACC_EMPTY_SW_DISCON',
                            305 :'EVT_OVERLOAD_SW_DISCON',
                            307 :'EVT_OVERCURRENT_SW_DISCON',
                            #Grampower Custom Related Events
                            1001:'ID_RF_DISCONNECTED',
                            1002:'ID_RF_CONNECTED',
                            1003:'ID_RF_GATEWAY',
                            1004:'ID_RF_CONFIG',
                            1005:'ID_BATT_POWERUP',
                            1006:'ID_BATT_POWERDOWN',
                            1007:'ID_BATT_POWERBATT',
                            10008:'EVT_OVER_POWER_OCCURANCE',
                            10009:'EVT_OVER_POWER_RESTORATION',
                            # Invalid Event for errors
                            512:'INVALID_EVT'}

    def __init__(self):
        """
        The constructor instantiates a default dictionary to store the event record data
        """
        dt = datetime.datetime(1970, 1, 1, 0, 0, 0)
        self.return_params = {"event_code":0,"date_time":dt,
                "current":0.00,"voltage":0.00,
                "power_factor":0.00,"active_energy":0.00, "tamperCnt":0}

    def __str__(self):
        """
        Prints out the stored information in the dictionary.
        Useful along with print statements.
        :param :none
        :return :none
        """
        #if full_event_log > 0 :
        return ("Event Code     : {}\n"
                "Date & Time    : {}\n"
                "Current        : {} A\n"
                "Voltage        : {} V\n"
                "Power Factor   : {}\n"
                "Active Energy  : {} KWh\n"
                "Tamper Count  : {} \n").format(self.return_params["event_code"],
                                                    self.return_params["date_time"],
                                                    self.return_params["current"],
                                                    self.return_params["voltage"],
                                                    self.return_params["power_factor"],
                                                    self.return_params["active_energy"],
                                                    self.return_params["tamperCnt"])
        # else :
        #     return ("Event Code     : {}\n"
        #             "Date & Time    : {}\n").format(self.return_params["event_code"],
        #                                             self.return_params["date_time"])            

    def printlog(self, payload):
        return ("{:<3}{:<5}{:<33}{:<25}{:<15}{:<15}{:<15}{:<15}{}")\
                .format(" ",
                        payload,
                        self.return_params["event_code"],
                        self.return_params["date_time"],
                        self.return_params["current"],
                        self.return_params["voltage"],
                        self.return_params["power_factor"],
                        self.return_params["active_energy"],
                        self.return_params["tamperCnt"])

    def deserialize(self,payload,evtsize):
        """
        Deserializes the input payload and populates the data to the default
        dictionary.This API needs to be used to retrieve information from the 
        reply bytestream.
        :param payload:input bytestream
        :return :none
        """
        buf = payload

        index = ((buf[1]<<8) +buf[0])
        # if index<70 or (index>200 and index<217):
        #     full_event_log = 1
        # else :
        #     full_event_log = 0    
                 
        try:
            self.return_params["event_code"] = self.VALID_EVENT_NAMES[index]
        except:
            self.return_params["event_code"] = self.VALID_EVENT_NAMES[512]

        #if full_event_log > 0 :     
        unix_time = ((buf[5]<<24)+(buf[4]<<16)+(buf[3]<<8) +buf[2])
        self.return_params["date_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(unix_time))
        if (evtsize == 1) or (evtsize == 2) or (evtsize == 7):
            self.return_params["voltage"]       = ((buf[9]<<24)+(buf[8]<<16)+(buf[7]<<8) +buf[6])/1000.0
            self.return_params["current"]       = ((buf[13]<<24)+(buf[12]<<16)+(buf[11]<<8) +buf[10])/1000.0
            self.return_params["power_factor"]  = serialize.deserialize_int32(buf[14:18], "reverse")/1000.0
            self.return_params["active_energy"] = ((buf[21]<<24)+(buf[20]<<16)+(buf[19]<<8) +buf[18])/100.0
            self.return_params["tamperCnt"]     = ((buf[25]<<24)+(buf[24]<<16)+(buf[23]<<8) +buf[22])
        else:
            self.return_params["voltage"]       = "---"
            self.return_params["current"]       = "---"
            self.return_params["power_factor"]  = "---"
            self.return_params["active_energy"] = "---"
            self.return_params["tamperCnt"]     = "---"
       
    def serialize(self, payload):
        print ("not implemented")

    def get_data_dictionary(self):
        """
        Returns the dictionary used to store the ecop data
        """
        return self.return_params

    # def deserializex(self,payload):
    #     """
    #     Deserializes the input payload.This API needs to be used to retrieve information from the 
    #     reply bytestream.
    #     :param payload:input bytestream
    #     :return :none
    #     """
    #     buf = payload

    #     index=0
    #     length = len(buf)

    #     if(length ==0):
    #         return "No entry found !!!"

    #     while length > 0:
    #         evtId = buf[index]

    #         unix_time = ((buf[index+4]<<24)+(buf[index+3]<<16)+(buf[index+2]<<8) +buf[index+1])
    #         unix_time_zero = datetime.datetime(1970, 1, 1)
    #         dt = unix_time_zero + datetime.timedelta(0, unix_time)

    #         print "Index : "+str(index/5)+"    Event : "+self.VALID_EVENT_NAMES[evtId]+"    TimeStamp : "+str(dt)
    #         index+=5
    #         length-=5
    #     return "Log fetch done !!!"
        

class EventRecordNumber(object):
    def __init__(self):
        """
        The constructor instantiates a default dictionary to store the ecop data
        """
        self.return_params = {
                "current_events":0,"voltage_events":0,"power_events":0,
                "transactions_events":0,"other_events":0,
                "non_rollover_events":0,"control_events":0,
                "RF_events":0, "total_events":0}

    def __str__(self):
        """
        Prints out the stored information in the dictionary.
        Useful along with print statements.
        :param :none
        :return :none
        """
        return ("\nNo. of current related events       : {}\n"
                "No. of voltage related Events       : {}\n"
                "No. of power related Events         : {}\n"
                "No. of transaction related events   : {}\n"
                "No. of non rollover events          : {}\n"
                "No. of control related events       : {}\n"
                "No. of other events                 : {}\n"
                "No. of RF related events            : {}\n"
                "Total no. of events                 : {}\n").format(self.return_params["current_events"],
                                                                        self.return_params["voltage_events"],
                                                                        self.return_params["power_events"],
                                                                        self.return_params["transactions_events"],
                                                                        self.return_params["non_rollover_events"],
                                                                        self.return_params["control_events"],
                                                                        self.return_params["other_events"],
                                                                        self.return_params["RF_events"],
                                                                        self.return_params["total_events"])

    def deserialize(self,payload):
        """
        Deserializes the input payload and populates the data to the default
        dictionary.This API needs to be used to retrieve information from the 
        reply bytestream.
        :param payload:input bytestream
        :return :none
        """

        bytes = bytearray()
        bytes = payload
        #print time.asctime(time.localtime(time.time()))
        self.return_params["current_events"]        = serialize.deserialize_uint32(bytes[0:4])
        self.return_params["voltage_events"]        = serialize.deserialize_uint32(bytes[4:8])
        self.return_params["power_events"]          = serialize.deserialize_uint32(bytes[8:12])
        self.return_params["transactions_events"]   = serialize.deserialize_uint32(bytes[12:16])
        self.return_params["non_rollover_events"]   = serialize.deserialize_uint32(bytes[16:20])
        self.return_params["control_events"]        = serialize.deserialize_uint32(bytes[20:24])
        self.return_params["other_events"]          = serialize.deserialize_uint32(bytes[24:28])
        if (len(payload) > 28):
            self.return_params["RF_events"]         = serialize.deserialize_uint32(bytes[28:32])
        else:
            self.return_params["RF_events"]         = 0
        self.return_params["total_events"]          = self.return_params["current_events"]       +\
                                                      self.return_params["voltage_events"]       +\
                                                      self.return_params["power_events"]         +\
                                                      self.return_params["transactions_events"]  +\
                                                      self.return_params["non_rollover_events"]  +\
                                                      self.return_params["control_events"]       +\
                                                      self.return_params["other_events"]         +\
                                                      self.return_params["RF_events"]
        
       
    def serialize(self, payload):
        print ("not implemented")

    def get_data_dictionary(self):
        """
        Returns the dictionary used to store the ecop data
        """
        return self.return_params