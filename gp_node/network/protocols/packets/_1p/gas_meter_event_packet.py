import datetime
import time
import gp_node.utils.serialize as serialize

class GasEventRecordPacket(object):

    VALID_EVENT_NAMES = {   0 :'EVT_NONE',
                            # Transactions Related
                            151 :'EVT_RTC_DATETIME_SET',
                            157 :'EVT_FW_UPGRADE_OCCURANCE',
                            167 :'EVT_TARIFF_SCHEDULE_SET',
                            168 :'EVT_TARIFF_ACTIVATED',
                            169 :'EVT_SW_WELD_OCCURANCE',
                            171 :'EVT_BATTERY_CHANGE',
                            # Other Related
                            201 :'EVT_MAGNET_OCCURANCE',
                            202 :'EVT_MAGNET_RESTORATION',
                            209 :'EVT_COMM_MOD_PLUGOUT',
                            210 :'EVT_COMM_MOD_PLUGIN',
                            211 :'EVT_CHANGE_TO_POSTPAID',
                            212 :'EVT_CHANGE_TO_PREPAID',
                            239 :'ID_OCR_LOW_BAT',
                            240 :'ID_RES_LOW_BAT',
                            # Non-Rollover Related
                            251:'EVT_COPEN_OCCURANCE',
                            252:'EVT_COPEN_RESTORATION',
                            # Control Related
                            301 :'EVT_SW_DISCON',
                            302 :'EVT_SW_CON',
                            303 :'EVT_ACC_EMPTY_SW_DISCON',
                            309 :'EVT_MAGNET_SW_DISCON',
                            311 :'EVT_COPEN_SW_DISCON',
                            313 :'EVT_MANUAL_SW_DISCON',
                            315 :'EVT_COMM_REM_SW_DISCON',
                            # Invalid Event for errors
                            513:'INVALID_EVT'}

    def __init__(self):
        """
        The constructor instantiates a default dictionary to store the event record data
        """
        dt = datetime.datetime(1970, 1, 1, 0, 0, 0)
        self.return_params = {"event_code" : "INVALID_EVT",
                              "date_time"  : dt,
                              "curBalance" : 0.00,
                              "consumedGas": 0.00}

    def __str__(self):
        """
        Prints out the stored information in the dictionary.
        Useful along with print statements.
        :param :none
        :return :none
        """
        #if full_event_log > 0 :
        return ("EventCode          : {}\n"
                "DateTime           : {}\n"
                "CurBalance         : {} Rs\n"
                "ConsumedGas        : {} m3\n").format(self.return_params["event_code"],
                                                       self.return_params["date_time"],
                                                       self.return_params["curBalance"],
                                                       self.return_params["consumedGas"])

    def deserializePacket(self,payload, dataindex):
        """
        Deserializes the input payload and populates the data to the default
        dictionary.This API needs to be used to retrieve information from the 
        reply bytestream.
        :param payload:input bytestream
        :return :none
        """
        data = payload
        dataLen = len(data)
        index = 0
        data_index = dataindex * 7
        retVal = ""

        print ("{:<10}{:<23}{:<29}{:<19}{} \n"
               "{:<10}{:<23}{:<29}{:<19}{}").format(
        "Index", "DateTime"           ,"EventId"                  , "Balance (Rs)" ,"ConsumedGas (m3)",
        "------","-------------------","-------------------------","--------------","----------------")
        while(dataLen >= 12):
            eventId = serialize.deserialize_uint16(data[index:index+2],"reverse")
            self.return_params["event_code"]    = self.VALID_EVENT_NAMES[eventId]
            self.return_params["curBalance"]    = serialize.deserialize_int16(data[index+2:index+4],"reverse")/1.0
            timevalue = serialize.deserialize_uint32(data[index+4:index+8],"reverse")
            self.return_params["date_time"]     = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(timevalue))
            self.return_params["consumedGas"]   = serialize.deserialize_uint32(data[index+8:index+12],"reverse")/100.0
            retVal += ("{:<10}{:<23}{:<29}{:<19}{} \n").format(data_index,
                                                        self.return_params["date_time"],
                                                        self.return_params["event_code"],
                                                        self.return_params["curBalance"],
                                                        self.return_params["consumedGas"])
            dataLen = dataLen-12
            index = index+12
            data_index = data_index+1
        return retVal

    def serialize(self, payload):
        print ("not implemented")


class GasEventRecordNumber(object):
    def __init__(self):
        """
        The constructor instantiates a default dictionary to store the ecop data
        """
        self.return_params = {
                "transactions_events":0,"other_events":0,
                "non_rollover_events":0,"control_events":0,
                "total_events":0}

    def __str__(self):
        """
        Prints out the stored information in the dictionary.
        Useful along with print statements.
        :param :none
        :return :none
        """
        return ("No. of transaction related events   : {}\n"
                "No. of non rollover events          : {}\n"
                "No. of control related events       : {}\n"
                "No. of other events                 : {}\n"
                "Total no. of events                 : {}\n").format(self.return_params["transactions_events"],
                                                                     self.return_params["non_rollover_events"],
                                                                     self.return_params["control_events"],
                                                                     self.return_params["other_events"],
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
        self.return_params["transactions_events"]   = serialize.deserialize_uint32(bytes[0:4])
        self.return_params["non_rollover_events"]   = serialize.deserialize_uint32(bytes[4:8])
        self.return_params["control_events"]        = serialize.deserialize_uint32(bytes[8:12])
        self.return_params["other_events"]          = serialize.deserialize_uint32(bytes[12:16])
        self.return_params["total_events"]          = self.return_params["transactions_events"]  +\
                                                      self.return_params["non_rollover_events"]  +\
                                                      self.return_params["control_events"]       +\
                                                      self.return_params["other_events"]


    def serialize(self, payload):
        print("not implemented")

    def get_data_dictionary(self):
        """
        Returns the dictionary used to store the ecop data
        """
        return self.return_params

# if __name__ == "__main__":
#     event = GasEventRecordNumber()
#     buf = bytearray([0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x02,0x00,0x00,0x00,0x03,0x00,0x00,0x00,0x04])
#     event.deserialize(buf)
#     print event

#     event = GasEventRecordPacket()
#     buf = bytearray([0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x00,0x00,0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x00,0x00,0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x00,0x00,0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x00,0x00,0x00])
#     ret = event.deserialize(buf, 1)
#     print ret
