import datetime
from gp_node.utils.serialize import deserialize_uint16
from gp_node.utils.serialize import deserialize_uint8
from gp_node.utils.serialize import deserialize_uint32

import gp_node.utils.serialize as serialize

class TodConfigurationPacket(object):
    def __init__(self):
        self.start_time_1 = 0
        self.duration_1 = 0
        self.price_1 = 0
        self.start_time_2 = 0
        self.duration_2 = 0
        self.price_2 = 0

    def __str__(self):
        return ("start_time_1 : {}\n"
                "duration_1 : {} minutes\n"
                "price_1 : {} paisa/KWh\n"
                "start_time_2 : {} \n"
                "duration_2 : {} minutes \n"
                "price_2 : {} Paisa/KWh\n")\
                .format(self.start_time_1,
                        self.duration_1,
                        self.price_1,
                        self.start_time_2,
                        self.duration_2,
                        self.price_2)

    def deserialize(self,payload):
        tot_Sec = (deserialize_uint32(payload[0:4],"reverse"))
        self.start_time_1 = datetime.timedelta(seconds=tot_Sec)
        self.duration_1 = deserialize_uint16(payload[4:6],"reverse")
        self.price_1 = deserialize_uint16(payload[6:8],"reverse")
        tot_Sec1 = deserialize_uint32(payload[8:12],"reverse")
        self.start_time_2 = datetime.timedelta(seconds=tot_Sec1)
        self.duration_2 = deserialize_uint16(payload[12:14],"reverse")
        self.price_2 = deserialize_uint16(payload[14:16],"reverse")


    def serialize(self):
        payload = bytearray()
        print (self.start_time_1)
        print (self.start_time_2)
        payload.extend(serialize.serialize_uint32(self.start_time_1,"reverse"))
        payload.extend(serialize.serialize_uint16(self.duration_1,"reverse"))
        payload.extend(serialize.serialize_uint16(self.price_1,"reverse"))
        payload.extend(serialize.serialize_uint32(self.start_time_2,"reverse"))
        payload.extend(serialize.serialize_uint16(self.duration_2,"reverse"))
        payload.extend(serialize.serialize_uint16(self.price_2,"reverse"))  
        return payload
