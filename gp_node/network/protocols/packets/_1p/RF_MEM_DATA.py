import datetime
import gp_node.utils.serialize as serialize
import time
from gp_node.utils.serialize import deserialize_int16
from gp_node.utils.serialize import deserialize_int32
from gp_node.utils.serialize import deserialize_uint32
from gp_node.utils import TamperFlag

class  RFMemData(object):

    def __init__(self):
        """
        The constructor instantiates a default dictionary to store the ecop data
        """
        self.final_state = []
        self.final_result = "False"
        self.return_params = {
                 "RF_CHANNEL":0
                ,"RF_POWER":0
                ,"RF_DATA_RATE":0
                ,"Protocol_Mode":0
                ,"RSSI_Acceptance_level":0
                ,"RSSI_Clear_Channel_Assessment_level":0
                ,"HIAM_Time":0
                ,"IMA_Time":0
                ,"Connect_Check_Time":0
                ,"Max_Jump_Level":0
                ,"Max_Jump_Count":0
                ,"Max_Packet_Latency":0
                ,"RF_Transmit_Retry_Limit":0
                ,"Serial_Port_Time_Out":0
                # ,"Parameter":0
                ,"Device_Type":0
                ,"Excellent_RSSI_Level":0
                ,"GPIO_0_Configuration":0
                ,"GPIO_1_Configuration":0
                ,"GPIO_2_Configuration":0
                ,"GPIO_3_Configuration":0
                ,"GPIO_4_Configuration":0
                ,"GPIO_5_Configuration":0
                ,"GPIO_6_Configuration":0
                ,"GPIO_7_Configuration":0
                ,"GPIO_0_trig":0
                ,"GPIO_1_trig":0
                ,"GPIO_2_trig":0
                ,"GPIO_3_trig":0
                ,"GPIO_4_trig":0
                ,"GPIO_5_trig":0
                ,"GPIO_6_trig":0
                ,"GPIO_7_trig":0
                ,"Input_Debounce":0
                ,"GPIO_0_Analogue_High_trig_High_byte":0
                ,"GPIO_0_Analogue_High_Trig_Low_byte":0
                ,"GPIO_0_Analogue_Low_Trig_High_byte":0
                ,"GPIO_0_Analogue_Low_Trig_Low_byte":0
                ,"GPIO_0_Analogue_Sampling_Interval":0
                ,"GPIO_1_Analogue_High_trig_High_byte":0
                ,"GPIO_1_Analogue_High_trig_Low_byte":0
                ,"GPIO_1_Analogue_Low_trig_High_byte":0
                ,"GPIO_1_Analogue_Low_trig_Low_byte":0
                ,"GPIO_1_Analogue_Sampling_Interval":0
                ,"CTS_hold_time":0
                ,"Locator_Enable":0
                ,"UID0":0
                ,"UID1":0
                ,"UID2":0
                ,"UID3":0
                ,"SID0":0
                ,"SID1":0
                ,"SID2":0
                ,"SID3":0
                ,"UART_Baud_Rate":0
                ,"UART_Bits":0
                ,"UART_Parity":0
                ,"UART_Stop_Bits":0
                # ,"Reserved":0
                ,"UART_Flow_Control":0
                ,"Serial_Buffer_Full_Margin":0
                ,"PART_Number":0
                ,"Fill_Byte1":0
                ,"HW_Revision":0
                ,"Fill_Byte2":0
                ,"FW_Revision":0
                ,"Security_Level":0
                # ,"Reserved":0
                ,"Max_Packet_Latency_Time_Base":0
                ,"IMA_time_base":0
                ,"End_Device_Wait_for_Command":0
                ,"End_Device_Wakeup_Enable":0
                ,"Configuration_Mode_Entry_Control":0
                ,"Indicators_On":0
                ,"Receive_Neighbour_Messages":0
                ,"Command_Acknowledge":0
                # ,"Reserved":0
                ,"Sleep_or_RTS":0
                ,"IMA_On_Connect":0
                ,"PWM_Default":0
                ,"Pulse_Counter_Mode":0
                ,"Pulse_Counter_Debounce":0
                ,"Connection_Change_Margin":0
                ,"Clustered_Node_Device_Limit":0
                ,"Clustered_Node_RSSI":0
                ,"Detect_Network_Busy":0
                ,"RF_Jamming_Detect":0
                ,"RF_Jamming_Alarm_Port":0
                ,"Feedback_Port":0
                ,"Feedback_Enable":0
                ,"IMA_Message_Data_Field_Contents":0
                ,"IMA_Message_Address_Field_Contents":0
                ,"Trig_Hold":0
                ,"End_Device_Awake_Port":0
                ,"Configuration_Lock_Override":0
                # ,"Reserved":0
                ,"Group_Table":0
                ,"Accept_New_Command_Time_Out":0
                ,"Command_Retry":0
                ,"MAC_RndTime2Mask":0
                ,"MAC_RndTime1Mask":0
                # ,"Reserved":0
                # ,"Reserved":0
                }


    def RF_mem_data(self):
        """
        Prints out the stored information in the dictionary.
        Useful along with print statements.
        ex: print EcopDataStreamPacket()
        :param :none
        :return :none
        """
        
        print ("network:= ",self.return_params["SID0"])
        print ("channel:= ",self.return_params["RF_CHANNEL"])

        return ("RF CHANNEL                                : {},{} \n" 
                "RF POWER                                  : {},{} \n" 
                "RF DATA RATE                              : {},{} \n" 
                "Protocol Mode                             : {},{} \n" 
                "RSSI Acceptance level                     : {},{} \n"
                "RSSI Clear Channel Assessment level       : {},{} \n"
                "HIAM Time                                 : {},{} \n"
                "IMA Time                                  : {},{} \n"
                "Connect Check Time                        : {},{} \n"
                "Max Jump Level                            : {},{} \n"
                "Max Jump Count                            : {},{} \n"
                "Max Packet Latency                        : {},{} \n"
                "RF Transmit Retry Limit                   : {},{} \n"
                "Serial Port Time Out                      : {},{} \n"
                # "Parameter                                 : {},{} \n"
                "Device Type                               : {},{} \n"
                "Excellent RSSI Level                      : {},{} \n" 
                "GPIO 0 Configuration                      : {},{} \n" 
                "GPIO 1 Configuration                      : {},{} \n" 
                "GPIO 2 Configuration                      : {},{} \n" 
                "GPIO 3 Configuration                      : {},{} \n" 
                "GPIO 4 Configuration                      : {},{} \n" 
                "GPIO 5 Configuration                      : {},{} \n" 
                "GPIO 6 Configuration                      : {},{} \n" 
                "GPIO 7 Configuration                      : {},{} \n" 
                "GPIO 0 trig                               : {},{} \n"
                "GPIO 1 trig                               : {},{} \n"
                "GPIO 2 trig                               : {},{} \n"   
                "GPIO 3 trig                               : {},{} \n"
                "GPIO 4 trig                               : {},{} \n"
                "GPIO 5 trig                               : {},{} \n"
                "GPIO 6 trig                               : {},{} \n"
                "GPIO 7 trig                               : {},{} \n"
                "Input De-bounce                           : {},{} \n" 
                "GPIO 0   Analogue High trig High byte     : {},{} \n"
                "GPIO 0   Analogue High Trig Low byte      : {},{} \n"
                "GPIO 0   Analogue Low Trig High byte      : {},{} \n"
                "GPIO 0 Analogue Low Trig Low byte         : {},{} \n"
                "GPIO 0 Analogue Sampling Interval         : {},{} \n"
                "GPIO 1  Analogue High trig High byte      : {},{} \n"
                "GPIO 1  Analogue  High trig Low byte      : {},{} \n"
                "GPIO 1 Analogue  Low trig High byte       : {},{} \n"
                "GPIO 1  Analogue  Low trig Low byte       : {},{} \n"
                "GPIO 1 Analogue Sampling Interval         : {},{} \n"
                "CTS hold time                             : {},{} \n"
                "Locator_Enable                            : {},{} \n"
                "UNIQUE_ID0 (UID0)                         : {},{} \n"
                "UNIQUE_ID1 (UID1)                         : {},{} \n"
                "UNIQUE_ID2 (UID2)                         : {},{} \n"
                "UNIQUE_ID3 (UID3)                         : {},{} \n"
                "SYSTEM_ID0 (SID0)                         : {},{} \n"
                "SYSTEM_ID1 (SID1)                         : {},{} \n"
                "SYSTEM_ID2 (SID2)                         : {},{} \n"
                "SYSTEM_ID3 (SID3)                         : {},{} \n"
                "UART Baud Rate                            : {},{} \n"
                "UART Bits                                 : {},{} \n"
                "UART Parity                               : {},{} \n"
                "UART Stop Bits                            : {},{} \n"
                # "Reserved                                   :{} \n"
                "UART Flow Control                         : {},{} \n"
                "Serial Buffer Full Margin                 : {},{} \n"
                "PART Number                               : {},{} \n"
                "Fill  Byte                                : {},{} \n"
                "HW Revision                               : {},{} \n"
                "Fill Byte                                 : {},{} \n" 
                "FW Revision                               : {},{} \n" 
                "Security Level                            : {},{} \n" 
                # "Reserved                                   :{} \n" 
                "Max Packet Latency Time Base              : {},{} \n"                                                                                 
                "IMA time base                             : {},{} \n"
                "End Device Wait for Command               : {},{} \n"
                "End Device Wakeup Enable                  : {},{} \n"
                "Configuration Mode Entry Control          : {},{} \n"
                "Indicators On                             : {},{} \n"
                "Receive Neighbour Messages                : {},{} \n"
                "Command Acknowledge                       : {},{} \n"
                # "Acknowledge                                :{} \n"
                # "Reserved                                   :{} \n"
                "Sleep or RTS                              : {},{} \n"
                "IMA On Connect                            : {},{} \n"
                "PWM Default                               : {},{} \n"
                "Pulse Counter Mode                        : {},{} \n"
                "Pulse Counter Debounce                    : {},{} \n"
                "Connection Change Margin                  : {},{} \n"
                "Clustered Node Device Limit               : {},{} \n"
                "Clustered Node RSSI                       : {},{} \n"
                "Detect Network Busy                       : {},{} \n"
                "RF Jamming Detect                         : {},{} \n"
                "RF Jamming Alarm Port                     : {},{} \n"
                "Feedback Port                             : {},{} \n"
                "Feedback Enable                           : {},{} \n"
                "IMA Message Data Field Contents           : {},{} \n" 
                "IMA Message Address Field Contents        : {},{} \n" 
                "Trig Hold                                 : {},{} \n" 
                "End Device Awake Port                     : {},{} \n"
                "Configuration Lock Override               : {},{} \n"
                # "Reserved                                   :{} \n"
                "Group Table                               : {},{} \n"
                "Accept New Command Time Out               : {},{} \n"
                # "Command Time Out                           :{} \n"
                "Command Retry                             : {},{} \n"
                "MAC RndTime2Mask                          : {},{} \n"
                "MAC RndTime1Mask                          : {},{} \n"
                # "Reserved                                   :{} \n"
                # "Reserved                                   :{} \n"
 
               )\
                .format(self.return_params["RF_CHANNEL"],self.final_state[0],
                self.return_params["RF_POWER"],self.final_state[1],
                self.return_params["RF_DATA_RATE"],self.final_state[2],
                self.return_params["Protocol_Mode"],self.final_state[3],
                self.return_params["RSSI_Acceptance_level"],self.final_state[4],
                self.return_params["RSSI_Clear_Channel_Assessment_level"],self.final_state[5],
                self.return_params["HIAM_Time"],self.final_state[6],
                self.return_params["IMA_Time"],self.final_state[7],
                self.return_params["Connect_Check_Time"],self.final_state[8],
                self.return_params["Max_Jump_Level"],self.final_state[9],
                self.return_params["Max_Jump_Count"],self.final_state[10],
                self.return_params["Max_Packet_Latency"],self.final_state[11],
                self.return_params["RF_Transmit_Retry_Limit"],self.final_state[12],
                self.return_params["Serial_Port_Time_Out"],self.final_state[13],
                # self.return_params["Parameter"],self.final_state[14],
                self.return_params["Device_Type"],self.final_state[14],
                self.return_params["Excellent_RSSI_Level"],self.final_state[15],
                self.return_params["GPIO_0_Configuration"],self.final_state[16],
                self.return_params["GPIO_1_Configuration"],self.final_state[17],
                self.return_params["GPIO_2_Configuration"],self.final_state[18],
                self.return_params["GPIO_3_Configuration"],self.final_state[19],
                self.return_params["GPIO_4_Configuration"],self.final_state[20],
                self.return_params["GPIO_5_Configuration"],self.final_state[21],
                self.return_params["GPIO_6_Configuration"],self.final_state[22],
                self.return_params["GPIO_7_Configuration"],self.final_state[23],
                self.return_params["GPIO_0_trig"],self.final_state[24],
                self.return_params["GPIO_1_trig"],self.final_state[25],
                self.return_params["GPIO_2_trig"],self.final_state[26],
                self.return_params["GPIO_3_trig"],self.final_state[27],
                self.return_params["GPIO_4_trig"],self.final_state[28],
                self.return_params["GPIO_5_trig"],self.final_state[29],
                self.return_params["GPIO_6_trig"],self.final_state[30],
                self.return_params["GPIO_7_trig"],self.final_state[31],
                self.return_params["Input_Debounce"],self.final_state[32],
                self.return_params["GPIO_0_Analogue_High_trig_High_byte"],self.final_state[33],
                self.return_params["GPIO_0_Analogue_High_Trig_Low_byte"],self.final_state[34],
                self.return_params["GPIO_0_Analogue_Low_Trig_High_byte"],self.final_state[35],
                self.return_params["GPIO_0_Analogue_Low_Trig_Low_byte"],self.final_state[36],
                self.return_params["GPIO_0_Analogue_Sampling_Interval"],self.final_state[37],
                self.return_params["GPIO_1_Analogue_High_trig_High_byte"],self.final_state[38],
                self.return_params["GPIO_1_Analogue_High_trig_Low_byte"],self.final_state[39],
                self.return_params["GPIO_1_Analogue_Low_trig_High_byte"],self.final_state[40],
                self.return_params["GPIO_1_Analogue_Low_trig_Low_byte"],self.final_state[41],
                self.return_params["GPIO_1_Analogue_Sampling_Interval"],self.final_state[42],
                self.return_params["CTS_hold_time"],self.final_state[43],
                self.return_params["Locator_Enable"],self.final_state[44],
                self.return_params["UID0"],self.final_state[45],
                self.return_params["UID1"],self.final_state[46],
                self.return_params["UID2"],self.final_state[47],
                self.return_params["UID3"],self.final_state[48],
                self.return_params["SID0"],self.final_state[49],
                self.return_params["SID1"],self.final_state[50],
                self.return_params["SID2"],self.final_state[51],
                self.return_params["SID3"],self.final_state[52],
                self.return_params["UART_Baud_Rate"],self.final_state[53],
                self.return_params["UART_Bits"],self.final_state[54],
                self.return_params["UART_Parity"],self.final_state[55],
                self.return_params["UART_Stop_Bits"],self.final_state[56],
                # self.return_params["Reserved"],
                self.return_params["UART_Flow_Control"],self.final_state[58],
                self.return_params["Serial_Buffer_Full_Margin"],self.final_state[59],
                self.return_params["PART_Number"],self.final_state[60],
                self.return_params["Fill_Byte1"],self.final_state[69],
                self.return_params["HW_Revision"],self.final_state[70],
                self.return_params["Fill_Byte2"],self.final_state[74],
                self.return_params["FW_Revision"],self.final_state[75],
                self.return_params["Security_Level"],self.final_state[81],
                # self.return_params["Reserved"],
                # self.return_params["Reserved"],
                self.return_params["Max_Packet_Latency_Time_Base"],self.final_state[84],
                self.return_params["IMA_time_base"],self.final_state[85],
                self.return_params["End_Device_Wait_for_Command"],self.final_state[86],
                self.return_params["End_Device_Wakeup_Enable"],self.final_state[87],
                self.return_params["Configuration_Mode_Entry_Control"],self.final_state[88],
                self.return_params["Indicators_On"],self.final_state[89],
                self.return_params["Receive_Neighbour_Messages"],self.final_state[90],
                self.return_params["Command_Acknowledge"],self.final_state[91],
                # self.return_params["Reserved"],
                self.return_params["Sleep_or_RTS"],self.final_state[93],
                self.return_params["IMA_On_Connect"],self.final_state[94],
                self.return_params["PWM_Default"],self.final_state[95],
                self.return_params["Pulse_Counter_Mode"],self.final_state[96],
                self.return_params["Pulse_Counter_Debounce"],self.final_state[97],
                self.return_params["Connection_Change_Margin"],self.final_state[98],
                self.return_params["Clustered_Node_Device_Limit"],self.final_state[99],
                self.return_params["Clustered_Node_RSSI"],self.final_state[100],
                self.return_params["Detect_Network_Busy"],self.final_state[101],
                self.return_params["RF_Jamming_Detect"],self.final_state[102],
                self.return_params["RF_Jamming_Alarm_Port"],self.final_state[103],
                self.return_params["Feedback_Port"],self.final_state[104],
                self.return_params["Feedback_Enable"],self.final_state[105],
                self.return_params["IMA_Message_Data_Field_Contents"],self.final_state[106],
                self.return_params["IMA_Message_Address_Field_Contents"],self.final_state[107],
                self.return_params["Trig_Hold"],self.final_state[108],
                self.return_params["End_Device_Awake_Port"],self.final_state[109],
                self.return_params["Configuration_Lock_Override"],self.final_state[110],
                # self.return_params["Reserved"],
                self.return_params["Group_Table"],self.final_state[113],
                self.return_params["Accept_New_Command_Time_Out"],self.final_state[121],
                self.return_params["Command_Retry"],self.final_state[122],
                self.return_params["MAC_RndTime2Mask"],self.final_state[123],
                self.return_params["MAC_RndTime1Mask"],self.final_state[124],
                # self.return_params["Reserved"]
                        )

    def deserialize_packet_RFMemDate(self,payload):
        """
        Deserializes the input payload and populates the data to the default
        dictionary.This API needs to be used to retrieve information from the 
        reply bytestream.
        :param payload:input bytestream
        :return :none
        """
        # bytes = bytearray()
        # bytes = payload
        # state_list = []
        #print "Deserializing"
        if (len(payload)==127):
            pass
        else:
            j=0
            extra_data=[]
            for i in range(len(payload),128):
                extra_data.append(j)
                i=i+1
            values=bytearray(extra_data)
            payload=payload+values    
        bytes = bytearray()
        bytes = payload
        state_list = []
        if (bytes[0] == 4):
            state_list.append("Defult")
        elif (0 < bytes[0] < 16 ):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["RF_CHANNEL"] = bytes[0] 

        if (bytes[1] == 5):
            state_list.append("Defult")
        elif (0 < bytes[1] < 5 ):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["RF_POWER"] = bytes[1]    

        if (bytes[2] == 5):
            state_list.append("Defult")
        elif (0 < bytes[2] < 7 or bytes[2]==8 ):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["RF_DATA_RATE"] = bytes[2] 

        if (bytes[3] == 1):
            state_list.append("Defult")
        elif (bytes[3]==0):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Protocol_Mode"] = bytes[3] 

        if (bytes[4] == 255):
            state_list.append("Defult")
        elif (159 < bytes[4] < 211 ):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["RSSI_Acceptance_level"] = bytes[4]   

        if (bytes[5] == 140):
            state_list.append("Defult")
        elif (99 < bytes[5] < 211 ):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["RSSI_Clear_Channel_Assessment_level"] = bytes[5]

        if (bytes[6] == 255):
            state_list.append("Defult")
        elif (0 < bytes[6] < 9 ):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["HIAM_Time"] = bytes[6]   

        if (bytes[7] == 255 or bytes[7] == 10):
            state_list.append("Defult")
        elif (0 < bytes[7] < 255 ):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["IMA_Time"] = bytes[7]   

        if (bytes[8] == 255):
            state_list.append("Defult")
        elif (0 < bytes[8] < 255 ):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Connect_Check_Time"] = bytes[8]

        if (bytes[9] == 20):
            state_list.append("Defult")
        elif (0 < bytes[9] < 256 ):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Max_Jump_Level"] = bytes[9] 

        if (bytes[10] == 30):
            state_list.append("Defult")
        elif (0 < bytes[10] < 256 ):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Max_Jump_Count"] = bytes[10] 

        if (bytes[11] == 5):
            state_list.append("Defult")
        elif (0 < bytes[11] < 256 ):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Max_Packet_Latency"] = bytes[11]

        if (bytes[12] == 100):
            state_list.append("Defult")
        elif (0 < bytes[12] < 256 ):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["RF_Transmit_Retry_Limit"] = bytes[12] 

        if (bytes[13] == 20):
            state_list.append("Defult")
        elif (0 < bytes[13] < 256 ):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Serial_Port_Time_Out"] = bytes[13] 

        if (bytes[14] == 2):
            state_list.append("Defult")
        elif (0 < bytes[14] < 3 ):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Device_Type"] = bytes[14] 

        if (bytes[15] == 150):
            state_list.append("Defult")
        elif (0 <= bytes[15] < 256 ):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Excellent_RSSI_Level"] = bytes[15] 

        if (bytes[16] == 1):
            state_list.append("Defult")
        elif (0 <= bytes[16] < 3 or bytes[16]==4):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_0_Configuration"] = bytes[16] 

        if (bytes[17] == 1):
            state_list.append("Defult")
        elif (0 <= bytes[17] < 3 or bytes[17]==4):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_1_Configuration"] = bytes[17] 

        if (bytes[18] == 1):
            state_list.append("Defult")
        elif (0 <= bytes[18] < 2 or bytes[18]==4):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_2_Configuration"] = bytes[18] 

        if (bytes[19] == 1):
            state_list.append("Defult")
        elif (0 <= bytes[19] < 2 or bytes[19]==4):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_3_Configuration"] = bytes[19] 

        if (bytes[20] == 1):
            state_list.append("Defult")
        elif (0 <= bytes[20] < 2 or bytes[20]==4):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_4_Configuration"] = bytes[20] 

        if (bytes[21] == 1):
            state_list.append("Defult")
        elif (0 <= bytes[21] < 2 or bytes[21]==4):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_5_Configuration"] = bytes[21] 
        print ("in desiralize")

        if (bytes[22] == 1):
            state_list.append("Defult")
        elif (0 <= bytes[22] < 2 or bytes[22]==4):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_6_Configuration"] = bytes[22] 

        if (bytes[23] == 1):
            state_list.append("Defult")
        elif (3 <= bytes[23] < 5 or bytes[23]==0):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_7_Configuration"] = bytes[23] 
        j=0
        for i in range(24,32):
            
            if (bytes[i] == 0):
                state_list.append("Defult")
            elif (1 <= bytes[i] < 4):
                state_list.append("Config")
            else:
                state_list.append("Corrupt")
            Gpi_value = "GPIO_"+str(j)+"_trig"  
            self.return_params[Gpi_value] = bytes[i]  
            j = j+1

        if (bytes[32] == 10):
            state_list.append("Defult")
        elif (0 <= bytes[32] < 256):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Input_Debounce"] = bytes[32] 

        if (bytes[33] == 7):
            state_list.append("Defult")
        elif (0 <= bytes[33] < 8):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_0_Analogue_High_trig_High_byte"] = bytes[33]  

        if (bytes[34] == 255):
            state_list.append("Defult")
        elif (0 <= bytes[34] < 256):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_0_Analogue_High_Trig_Low_byte"] = bytes[34] 

        if (bytes[35] == 0):
            state_list.append("Defult")
        elif (0 <= bytes[35] < 8):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_0_Analogue_Low_Trig_High_byte"] = bytes[35]  

        if (bytes[36] == 0):
            state_list.append("Defult")
        elif (0 <= bytes[36] < 256):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_0_Analogue_Low_Trig_Low_byte"] = bytes[36]

        if (bytes[37] == 100):
            state_list.append("Defult")
        elif (0 <= bytes[37] < 256):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_0_Analogue_Sampling_Interval"] = bytes[37]

        if (bytes[38] == 7):
            state_list.append("Defult")
        elif (0 <= bytes[38] < 8):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_1_Analogue_High_trig_High_byte"] = bytes[38]  

        if (bytes[39] == 255):
            state_list.append("Defult")
        elif (0 <= bytes[39] < 256):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_1_Analogue_High_Trig_Low_byte"] = bytes[39] 

        if (bytes[40] == 0):
            state_list.append("Defult")
        elif (0 <= bytes[40] < 8):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_1_Analogue_Low_Trig_High_byte"] = bytes[40]  

        if (bytes[41] == 0):
            state_list.append("Defult")
        elif (0 <= bytes[41] < 256):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_1_Analogue_Low_Trig_Low_byte"] = bytes[41]

        if (bytes[42] == 100):
            state_list.append("Defult")
        elif (0 <= bytes[42] < 256):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["GPIO_1_Analogue_Sampling_Interval"] = bytes[42] 

        if (bytes[43] == 6):
            state_list.append("Defult")
        elif (0 < bytes[43] < 256):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["CTS_hold_time"] = bytes[43]

        if (bytes[44] == 0):
            state_list.append("Defult")
        elif (bytes[44] == 1):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Locator_Enable"] = bytes[44]

        j=0
        for i in range(45,49):
            
            if (i == 45):
                if (bytes[i] == 1):
                    state_list.append("Defult")
                else:
                    state_list.append("Config")
            elif (bytes[i] == 0):
                state_list.append("Defult")
            elif (0 <= bytes[i] < 256):
                state_list.append("Config")
            else:
                state_list.append("Corrupt")
            Re_value = "UID"+str(j)  
            self.return_params[Re_value] = bytes[i]  
            j = j+1

        j = 0
        for i in range(49,53):
            
            if (i == 49):
                if (bytes[i] == 1):
                    state_list.append("Defult")
                else:
                    state_list.append("Config")
            elif (bytes[i] == 0):
                state_list.append("Defult")
            elif (0 <= bytes[i] < 256):
                state_list.append("Config")
            else:
                state_list.append("Corrupt")
            Sid_value = "SID"+str(j)  
            # print "Sid_value",Sid_value,type(Sid_value)
            self.return_params[Sid_value] = bytes[i]
            # print "return_params[Re_value]=",self.return_params[Sid_value],"address=",i
            j = j+1  
        # print "return_params[Re_value]=",self.return_params["SID0"]
        # print "return_params[Re_value]=",self.return_params["SID1"]     

        if (bytes[53] == 5):
            state_list.append("Defult")
            self.return_params["UART_Baud_Rate"] = 19200
        elif (1 <= bytes[53] < 12):
            state_list.append("Config")
            self.return_params["UART_Baud_Rate"] = bytes[53]
        else:
            state_list.append("Corrupt")
            self.return_params["UART_Baud_Rate"] = bytes[53]
         

        if (bytes[54] == 8):
            state_list.append("Defult")
        elif (bytes[54] == 9):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["UART_Bits"] = bytes[54] 

        if (bytes[55] == 0):
            state_list.append("Defult")
        elif (bytes[55] == 1):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["UART_Parity"] = bytes[55] 

        if (bytes[56] == 1):
            state_list.append("Defult")
        elif (bytes[56] == 2):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["UART_Stop_Bits"] = bytes[56] 

        state_list.append("Reserved")
        # self.return_params["Reserved"] = bytes[57] 

        if (bytes[58] == 1):
            state_list.append("Defult")
        elif (1 < bytes[58] < 128):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["UART_Flow_Control"] = bytes[58]

        if (bytes[59] == 18):
            state_list.append("Defult")
        elif (1 <= bytes[59] < 101):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Serial_Buffer_Full_Margin"] = bytes[59]

        for i in range(60,69):
            state_list.append("NOT config")
            self.return_params["PART_Number"] = bytes[i] 

        if (bytes[69] == 44 or bytes[74] == 44):
            state_list.append("Defult")
        else:
            state_list.append("Corrupt")
        self.return_params["Fill_Byte1"] = bytes[69]   

        for i in range(70,74):
            if (0 <= bytes[i] < 10):
                state_list.append("NOT Config")
            else:
                state_list.append("Corrupt")
            self.return_params["HW_Revision"] = bytes[i]  

        if (bytes[74] == 44 or bytes[76] == 44):
            state_list.append("Defult")
        else:
            state_list.append("Corrupt")
        self.return_params["Fill_Byte2"] = bytes[74] 

        for i in range(75,81):
            if (0 <= bytes[i] < 10):
                state_list.append("NOT Config")
            else:
                state_list.append("Corrupt")
            self.return_params["FW_Revision"] = bytes[i]   

        if (bytes[81] == 0):
            state_list.append("Defult")
        elif (1 <= bytes[81] < 3):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Security_Level"] = bytes[81]   

        state_list.append("Reserved")
        # self.return_params["Reserved"] = bytes[82]    
        state_list.append("Reserved")
        # self.return_params["Reserved"] = bytes[83]  

        if (bytes[84] == 1):
            state_list.append("Defult")
        elif (bytes[84] == 0):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Max_Packet_Latency_Time_Base"] = bytes[84]  

        if (bytes[85] == 6):
            state_list.append("Defult")
        elif (1 <= bytes[85] < 256):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["IMA_time_base"] = bytes[85]  

        if (bytes[86] == 0):
            state_list.append("Defult")
        elif (1 <= bytes[86] < 256):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["End_Device_Wait_for_Command"] = bytes[86]  

        if (bytes[87] == 8):
            state_list.append("Defult")
        elif (0 <= bytes[87] < 144):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["End_Device_Wakeup_Enable"] = bytes[87]  

        if (bytes[88] == 0):
            state_list.append("Defult")
        elif (1 <= bytes[88] < 4):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Configuration_Mode_Entry_Control"] = bytes[88] 

        if (bytes[89] == 255):
            state_list.append("Defult")
        elif (0 <= bytes[89] < 255):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Indicators_On"] = bytes[89]

        for i in range(90,95):
            if (i == 91):
                if (bytes[i] == 1):
                    state_list.append("Defult")
            elif (i == 92):  
                state_list.append("Reserved")
                pass
                
            elif (bytes[i] == 0):
                state_list.append("Defult")
            elif (0 <= bytes[i] < 2):
                state_list.append("Config")
            else:
                state_list.append("Corrupt")
            for j in range(90,95):
                if (j==90):
                    self.return_params["Receive_Neighbour_Messages"] = bytes[j]
                elif (j==91):
                    self.return_params["Command_Acknowledge"] = bytes[j]
                elif (j==93):
                    self.return_params["Sleep_or_RTS"] = bytes[j]
                elif (j==94):
                    self.return_params["IMA_On_Connect"] = bytes[j]   
                # elif (j==92):
                #     self.return_params["Reserved"] = bytes[j]   
        if (bytes[95] == 0):
            state_list.append("Defult")
        elif (0 <= bytes[95] < 101):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["PWM_Default"] = bytes[95]

        if (bytes[96] == 0):
            state_list.append("Defult")
        elif (bytes[96] == 1 or bytes[96] == 3):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Pulse_Counter_Mode"] = bytes[96]

        if (bytes[97] == 0):
            state_list.append("Defult")
        elif (0 <= bytes[97] < 256):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Pulse_Counter_Debounce"] = bytes[97]

        if (bytes[98] == 12):
            state_list.append("Defult")
        elif (0 <= bytes[98] < 256):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Connection_Change_Margin"] = bytes[98]

        if (bytes[99] == 10):
            state_list.append("Defult")
        elif (5 <= bytes[99] < 101):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Clustered_Node_Device_Limit"] = bytes[99]

        if (bytes[100] == 60):
            state_list.append("Defult")
        elif (40 <= bytes[100] < 101):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Clustered_Node_RSSI"] = bytes[100]

        if (bytes[101] == 0):
            state_list.append("Defult")
        elif (0 <= bytes[101] < 3):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Detect_Network_Busy"] = bytes[101]

        if (bytes[102] == 0):
            state_list.append("Defult")
        elif (0 <= bytes[102] < 101):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["RF_Jamming_Detect"] = bytes[102]

        if (bytes[103] == 255):
            state_list.append("Defult")
        elif (0 <= bytes[103] < 8):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["RF_Jamming_Alarm_Port"] = bytes[103]

        if (bytes[104] == 255):
            state_list.append("Defult")
        elif (0 <= bytes[104] < 8):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Feedback_Port"] = bytes[104]

        if (bytes[105] == 0):
            state_list.append("Defult")
        elif (bytes[105] == 2):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Feedback_Enable"] = bytes[105]

        if (bytes[106] == 0):
            state_list.append("Defult")
        elif (0 <= bytes[106] < 7):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["IMA_Message_Data_Field_Contents"] = bytes[106]

        if (bytes[107] == 2):
            state_list.append("Defult")
        elif (0 <= bytes[107] < 5):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["IMA_Message_Address_Field_Contents"] = bytes[107]

        if (bytes[108] == 0):
            state_list.append("Defult")
        elif (0 <= bytes[108] < 256):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Trig_Hold"] = bytes[108]

        if (bytes[109] == 255):
            state_list.append("Defult")
        elif (0 <= bytes[109] < 7):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["End_Device_Awake_Port"] = bytes[109]

        if (bytes[110] == 0):
            state_list.append("Defult")
        elif (bytes[110] == 1):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Configuration_Lock_Override"] = bytes[110]

        state_list.append("Reserved")
        # self.return_params["Reserved"] = bytes[111]    
        state_list.append("Reserved")
        # self.return_params["Reserved"] = bytes[112]  
        for i in range(113,121):
            if (bytes[i] == 0):
                state_list.append("Defult")
            elif (0 <= bytes[i] < 256):
                state_list.append("Config")
            else:
                state_list.append("Corrupt")
            self.return_params["Group_Table"] = bytes[i]  
        if (bytes[121] == 10):
            state_list.append("Defult")
        elif (0 <= bytes[121] < 256):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Accept_New_Command_Time_Out"] = bytes[121]

        if (bytes[122] == 4):
            state_list.append("Defult")
        elif (0 <= bytes[122] < 128):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["Command_Retry"] = bytes[122]    

        if (bytes[123] == 63 or bytes[123] == 31):
            state_list.append("Defult")
        elif (bytes[123] == 127 or bytes[123] == 15 or bytes[123] == 7 or bytes[123] == 3 or bytes[123] == 255):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["MAC_RndTime2Mask"] = bytes[123]

        if (bytes[124] == 15):
            state_list.append("Defult")
        elif (bytes[124] == 127 or bytes[124] == 61 or bytes[124] == 7 or bytes[124] == 3 or bytes[124] == 31):
            state_list.append("Config")
        else:
            state_list.append("Corrupt")
        self.return_params["MAC_RndTime1Mask"] = bytes[124]

        # state_list.append("Reserved")
        # self.return_params["Reserved"] = bytes[125]    
        # state_list.append("Reserved")
        # self.return_params["Reserved"] = bytes[126]  
        # state_list.append("Reserved")
        # self.return_params["Reserved"] = bytes[127] 
        # print "desiralize over"
        # for i in range(len(state_list)):
        #     print "state list",i,state_list[i],"\n"
        # print "state list",state_list,len(state_list)
        # print "return_params[Re_value]=",self.return_params["SID0"]
        # print "return_params[Re_value]=",self.return_params["SID1"]
        a = "Corrupt"
        b = "Config"
        if a in state_list:
            print ("IN corrupt")
            self.final_result = "Corrupt"

        elif b in state_list: 
            print ("IN Config")
            self.final_result = "Config"

        else:
            print ("IN Defult")
            self.final_result = "Defult"

        self.final_state = state_list

# entry = RFMemData()
# payload=bytearray([0x3, 0x5, 0x5, 0x1, 0xff, 0x8c, 0xff, 0xff, 0xff, 0x14, 0x1e, 0x32, 0x64, 0x14, 0x2, 0x96, 0x1, 0x1, 0x1, 0x1, 0x1, 0x1, 0x1, 0x1, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0xa, 0x7, 0xff, 0x0, 0x0, 0x64, 0x7, 0xff, 0x0, 0x0, 0x64, 0x6, 0x0, 0x2, 0x3, 0x3, 0x3, 0x31, 0x0, 0x0, 0x0, 0x5, 0x8, 0x0, 0x1, 0x0, 0x1, 0x12, 0x52, 0x46, 0x20, 0x54, 0x4d, 0x34, 0x30, 0x37, 0x30, 0x2e, 0x32, 0x2c, 0x31, 0x2e, 0x30, 0x30, 0x2c, 0x31, 0x2e, 0x35, 0x33, 0x0, 0x0, 0x7, 0x1, 0x6, 0x0, 0x8, 0x3, 0xff, 0x0, 0x1, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x12, 0xa, 0x3c, 0x0, 0x0, 0xff, 0xff, 0x0, 0x0, 0x2, 0x0, 0xff, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0xa, 0x4, 0x1f, 0xf, 0x0, 0x0])
# entry.deserialize_packet_RFMemDate(payload)
# print(entry.RF_mem_data())

           


           
                    
              
  
            

     
   





       
    
    

