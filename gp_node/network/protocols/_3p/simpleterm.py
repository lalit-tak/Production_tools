import time
from gp_node.utils import Address
import datetime
import getpass
"""
Implements master side of Simpleterm protocol
"""
# import binascii
from gp_node.network.protocols.common.tap import TAPError, TAPHandler
from gp_node.network.protocols.common.protocol import ProtocolMaster, ProtocolError
# from packets.daily_deduction_params import DailyDeductionParams
from gp_node.network.protocols.packets._3p.load_survey_params_3p import LoadSurveyParams3P
from gp_node.network.protocols.packets._3p.load_survey_packet_3p import LoadSurveyPacket3P
from gp_node.network.protocols.packets._3p.event_record_3p import EventRecordPacket3P,EventRecordNumber3P
from gp_node.network.protocols.packets._3p.metering_data_params_3p import MeteringDataParams3P
from gp_node.network.protocols.packets._3p.billing_params_3p import BillingParams3P
from gp_node.network.protocols.packets._3p.prepaid_account_packet_3p import PrepaidAccountPacket3P
from gp_node.network.protocols.packets._3p.slab_packet_3p import SlabConfigurationPacket3P
from gp_node.network.protocols.packets._3p.accounting_state_packet_3p import AccountingStatePacket3P
from gp_node.network.protocols.packets._3p.fixed_deduction_packet_3p import FixedDeductionPacket3P
from gp_node.network.protocols._3p.command_mapping_container import commandMappingContainer_3P
import gp_node.utils.serialize as serialize
from gp_node.network.protocols.packets._3p.crc_bundle_3p import CrcDataPacket3P
from gp_node.network.protocols.common.data_type_container import INT8, UINT32 ,INT32, UINT64,\
    BYTE_ARRAY, ECOP_PACKET,TAMPER_RECORD_PACKET, DAILY_DEDUCTION_PARAMS,\
    BUNDLE, LOG_PACKET, LOAD_SURVEY_PARAMS, MAXIMUM_DEMAND_PACKET,EVENT_RECORD_TOTAL_PACKET,\
    PREPAID_ACCOUNT_PACKET, SLAB_CONFIGURATION_PACKET, ACCOUNTING_STATE_PACKET, FIXED_DEDUCTION_PACKET,\
    ENERGY_HISTORY_PACKET, EVENT_RECORD_PACKET, DAILY_LOAD_PROFILE_PACKET,METERING_DATA_PACKET,\
    SYNCSTREAM_BUNDLE, PREPAID_ACCOUNT_PACKET_3P, SLAB_CONFIGURATION_PACKET_3P,ACCOUNTING_STATE_PACKET_3P,\
    FIXED_DEDUCTION_PACKET_3P, SURVEY_PACKET_3P, EVENT_RECORD_PACKET_3P,LOAD_SURVEY_PARAMS_3P,\
    METERING_DATA_PARAMS_3P, DAILY_PROFILE_3P, BILLING_PARAMS_3P, BILLING_LOG_PACKET_3P,\
    BILLING_HISTORY_PACKET_3P, SYS_PARAMS_1_PACKET_3P, DLMS_DBG_PACKET_3P,BUNDLE_3P,CRC_BUNDLE_3P,SYS_PARAMS_3P,\
    UINT32_BE

#from gp_node.network.protocols._3p.string_mapping_container import stringMappingContainer_3P
from gp_node.network.protocols._3p.string_mapping_container import stringMappingContainer_3P
from gp_node.network.protocols.packets._3p.bundle_3p import MeteringDataParamsBundle3P
from gp_node.network.protocols.packets._3p.sys_params_3p import SystemsCommands3P

SET_PARAM_HEADER_SIZE = 2

DCU_INTERVALS=59925

class SimpletermError_3P(ProtocolError):
    """
    error codes:

    GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH: raised when number of bytes in reply to a get_param query\
            does not contain expected number of bytes
    """
    GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH = 1


class SimpletermMaster_3P(ProtocolMaster):

    """
    """
    def __init__(self, PortId, my_address, my_tap_handler):

        self.SLAVE_PORT = 4
        self.REC_SLAVE_ID = int(PortId)
        self.MASTER_PORT = 4
        self.my_address = my_address
        self.my_tap_handler = my_tap_handler

    def monitor_dcu(self,interval):
        st=time.time()
        reply=[]
        counter=0
        while ((time.time()-st)< interval):
            try:
                packets=self.my_tap_handler.get_packet_from("255.255.255.255", self.SLAVE_PORT)
                for packet in packets:
                    print ("\n","*"*20,"\n")
                    print ("Time:",str(datetime.datetime.now()))
                    print ("Source address:",str(packet.src_addr))
                    print ("meter type:",str(packet.src_addr).split(".")[3])
                    print ("for meter:",str(packet.dest_addr))
                    print ("Source port:",str(packet.src_port))
                    print ("Dest port:",str(packet.dest_port))
                    print ("\n","="*20,"\n")
                    tmp_dict={"time":str(datetime.datetime.now()),"src_addr":str(packet.src_addr),"dest_addr":str(packet.dest_addr)}
                    strings="*"*20+"Time:"+str(datetime.datetime.now())+"\nSource address:"+str(packet.src_addr)+\
                    "\nmeter type:"+str(packet.src_addr).split(".")[3]+"\nfor meter:"+str(packet.dest_addr)+"\nSource port:"+str(packet.src_port)+\
                    "\nDest port:"+str(packet.dest_port)+"\n"+"="*20+"\n\n"
                    f=open('/home/'+getpass.getuser()+'/monitor_dcu.log','a+')
                    f.write(strings)
                    f.close()
                    counter+=1
                    reply.append(tmp_dict)
            except Exception as e:
                pass
        return reply

    def execute_command(self, slave_address, command_number):
        """
        Sends the command_string argument as it is
        to the underlying TAP layer & returns the reply from the TAP layer 
        as it is. This function is a very thin layer on top of TAP.
        :param str command_number: The mapped command number of the parameter which is being asked for.\
            Such as 10025 for "lock_state", 10031 for "fd_reset" etc.
        :returns: The bytearray as returned by the underlying TAP layer
        """
        full_data_list = []
        command = bytearray()
        command.extend(serialize.serialize_uint16(command_number))
        command.append('\0')
        self.my_address=Address(address_integer=command_number)

        self.my_address=Address("1.78.72.201")

        self.my_tap_handler.send_packet(self.my_address, slave_address, 
                                        self.SLAVE_PORT, self.MASTER_PORT, command.strip())

        try:
            packet = self.my_tap_handler.get_packet_from(slave_address, self.SLAVE_PORT)
            packet = packet[0]
        except TAPError as e:
            raise SimpletermError_3P(SimpletermError_3P.TAP_ERROR, e)
        else:

            for key, val in stringMappingContainer_3P.items():
                if key == serialize.deserialize_uint16(packet.data):
                    full_data_list.append([val, str(packet.src_addr),int(packet.dest_addr.dump_to_integer())])
            return full_data_list


    def get_param(self, slave_address, param_number, param_type, flash_delay=False, interval=0, isReturn=False):
        """
        This function is used to execute commands such as "get_voltage".
        :param str param_number: The mapped command number of the parameter which is being asked for.\
            Such as 20000 for "network", 20036 for "oldest_survey" etc.
        :param int param_type: Indicates the type of the expected value to be retuned by\
            the client. For example, if param_type is UINT32, then the reply\
            should contain 4 bytes, and the reply would then be deserialized as a UINT32\
        :returns: The deserialized value of the returned type.
        :rtype: depends on param_type.
        :raises: SimpletermError with error code GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH\
            if the length of the reply is not the consistent with the param_type argument
        """
        # print "need to make packet for it isReturn in get first",isReturn
        full_data_list = []
        cmd = bytearray()
        cmd.extend(serialize.serialize_uint16(param_number))
        self.my_address=Address("1.78.72.201")

        self.my_tap_handler.send_packet(self.my_address, slave_address, self.MASTER_PORT, self.SLAVE_PORT, cmd)

        try:
            # print "in try"
            tap_packet = self.my_tap_handler.get_packet_from(slave_address, self.SLAVE_PORT,self.my_address)
        except TAPError as e:
            # print "In except"
            raise SimpletermError_3P(SimpletermError_3P.TAP_ERROR, tap_error=e)

        # Here 3 phase things begin
        '''
        print("Sending Received Things")
        temp_buf =  bytearray()
        temp_buf =  tap_packet.data
        for byte in temp_buf:
            print(hex(byte))
        '''
        # Debugging End here
        # print "temp_buf",type(temp_buf)
        # print "tap_packets",type(tap_packet)
        # print "param_number_in_sim = ",param_number
        for i in range(1):
            # print tap_packet
            entry = ''
            # print "Expected Reply Types::", param_type, "len",len(tap_packet.data)

            if param_type == 29993:
                print ("status::",int(tap_packet.data[0]))



            if(commandMappingContainer_3P.GET_PARAMS_VDCU_2 == param_number):
                data=tap_packet.data
                toRet={}
                #reply_dict['broadcat_interval']=serialize.deserialize_uint16(data[0:2])
                toRet["IMEI NUM = "]=(data[0:15])
                toRet["SIM NUM = "]=data[15:35]
                toRet["APN =  "]=data[35:55]
                sim = ""
                if(0x31 == data[55]):
                    sim = "sim1"
                elif(0x32 == data[55]):
                    sim = "sim2"
                else:
                    sim = "UNKNOWN Sim status"
                toRet["Current Sim = "]=sim
                dcuNum=serialize.deserialize_uint32(data[56:60])
                toRet["Dcu Num = "]=str(dcuNum)
                battVolt = float(serialize.deserialize_uint32(data[60:64]))
                toRet["Battery volt = "]=str(battVolt/1000.0)+" V"
                onTimeBatt = serialize.deserialize_uint32(data[65:69])
                toRet["Battery On Time = "]=datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=onTimeBatt)
                offTimeBatt = serialize.deserialize_uint32(data[69:73])
                toRet["Battery Off Time = "]=datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=offTimeBatt)
                battOffCon = data[73]
                if(battOffCon == 1):
                    battOffCon = "1 hour completed"
                elif(battOffCon == 2):
                    battOffCon = "Low Battery"
                else:
                    battOffCon = "Mains supply"
                toRet["Battery Off condition = "]=battOffCon
                mains = data[64]
                if(mains == 1):
                    mains = "mains"
                else:
                    mains = "Battery"
                toRet["Run State ="]=mains

                for key in toRet.keys():
                            # print key,"\t\t",toRet[key]
                    print ("{:<30} = {}".format(key,toRet[key]))
                return toRet

            elif param_type == DCU_INTERVALS:
                reply_dict={}
                # print [hex(f) for f in tap_packet.data]
                if len(tap_packet.data)> 8:
                    data=tap_packet.data
                    reply_dict['broadcat_interval']=serialize.deserialize_uint16(data[0:2])
                    reply_dict['push_online_interval']=serialize.deserialize_uint16(data[2:4])
                    reply_dict['push_offline_interval']=serialize.deserialize_uint16(data[4:6])
                    reply_dict['seq_interval']=serialize.deserialize_uint16(data[6:8])
                    reply_dict['offline_store_interval']=serialize.deserialize_uint16(data[8:10])

                    reply_dict['pushed_offline_data_index']=serialize.deserialize_uint32(data[10:14])

                    reply_dict['current_meter_index']=serialize.deserialize_uint16(data[14:16])
                    # print reply_dict
                    reply_dict['current_command_index']=serialize.deserialize_uint16(data[16:18])


                    reply_dict['gateway_reset_interval']=serialize.deserialize_uint16(data[18:20])

                    reply_dict['internet_reset_interval']=serialize.deserialize_uint16(data[20:22])
                    reply_dict['update_health_threshold_interval']=serialize.deserialize_uint16(data[22:24])


                    reply_dict['total_offline_entries']=serialize.deserialize_uint32(data[24:28])
                    reply_dict['total_command_entries']=serialize.deserialize_uint32(data[28:32])
                    reply_dict['total_meter_entries']=serialize.deserialize_uint32(data[32:36])
                    reply_dict['total_Pushed_data_count']=serialize.deserialize_uint32(data[36:40])
                    t=serialize.deserialize_uint32(data[40:44])
                    reply_dict["dcu_time"]  = str(datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=t))
                    reply_dict['broadcat_enabled']=bool(serialize.deserialize_uint8(data[44:45]))
                    reply_dict['sequencial_enabled']=bool(serialize.deserialize_uint8(data[45:46]))
                    reply_dict['push_online_enabled']=bool(serialize.deserialize_uint8(data[46:47]))

                    reply_dict['push_offline_enabled']=bool(serialize.deserialize_uint8(data[47:48]))
                    reply_dict['save_offline_enabled']=bool(serialize.deserialize_uint8(data[48:49]))
                    reply_dict['retries']=serialize.deserialize_uint8(data[49:50])
                    reply_dict['inetrnet_available']=bool(serialize.deserialize_uint8(data[50:51]))
                    if len(data)>41:
                        reply_dict['dongle_reset_enabled']=bool(serialize.deserialize_uint8(data[51:52]))
                        reply_dict['gateway_reset_enabled']=bool(serialize.deserialize_uint8(data[52:53]))
                        reply_dict['Flash_status']=bool(serialize.deserialize_uint8(data[53:54]))
                        reply_dict['Battery_status']=bool(serialize.deserialize_uint8(data[54:55]))
                    if len(data)>55:
                        reply_dict['DG_CT_Ratio']=(serialize.deserialize_uint16(data[55:57]))
                        reply_dict['EB_CT_Ratio']=(serialize.deserialize_uint16(data[57:59]))
                    if len(data)>59:
                        reply_dict['Flash_Size']=int(data[59])
                        reply_dict['dg_meter'] = str(Address(address_integer = serialize.deserialize_uint32(data[60:64],"reverse")))
                        reply_dict['eb_meter'] = str(Address(address_integer = serialize.deserialize_uint32(data[64:68],"reverse")))
                        working_mode=data[68]
                        if working_mode==0:
                            reply_dict['working_mode']="DG"
                        elif working_mode==1:
                            reply_dict['working_mode']="MAINS"
                        reply_dict['prepaid_enabled']=data[69]
                    if len(data)>70:
                       reply_dict['EB_DG_DEFAULT_SWITCH_INTERVAL']=(serialize.deserialize_uint16(data[70:72]))
                       reply_dict['EB_DG_AUTO_SWITCH_TIMER']=(serialize.deserialize_uint16(data[72:74]))/10
                    if len(data)>74:
                       reply_dict['EB_DG_NO_DATA_TIMER']=(serialize.deserialize_uint16(data[74:76]))/10
                    if len(data)>76:
                       flash_dict={0:'FLASH_INVALID',1:'FLASH_VALID_BUT_READ_PENDING',2:'FLASH_READ_DONE',3:'FLASH_CORRUPTED'}
                       reply_dict['DCU FLASH STATUS ']=flash_dict[data[76]]

                    if len(data)>77:
                        reply_dict['CRC_Failed_Occurance']=serialize.deserialize_uint32(data[77:81])
                    if len(data)>81:
                        reply_dict['health_log_count']=serialize.deserialize_uint32(data[81:85])
                        reply_dict['CR_log_count']=serialize.deserialize_uint32(data[85:89])
                    if len(data)>89:
                        reply_dict['signal_strength']=serialize.deserialize_uint8(data[89:90])
                        # print serialize.deserialize_uint8(data[90:91])
                        offlineReason=serialize.deserialize_uint8(data[90:91])
                        offlineReasonStat = ""
                        if(offlineReason == 0):
                            offlineReason = "GSM_ONLINE"
                        elif(offlineReason == (offlineReason and 0x01)):
                            offlineReasonStat += "NO_MQTT_CONN  "
                        elif(offlineReason == (offlineReason and 0x02)):
                            offlineReasonStat += "NETWORK_UNREGESTERED  "
                        elif(offlineReason == (offlineReason and 0x04)):
                            offlineReasonStat += "SIM_NOT_FOUND  "
                        elif(offlineReason == (offlineReason and 0x08)):
                            offlineReasonStat += "RSSI_LEVEL_DISCONNECTION  "
                        else:
                            offlineReason = "UNKNOWN"
                        reply_dict['offline_reason']=offlineReasonStat 

                        reply_dict['mqttNumEntries']=serialize.deserialize_uint8(data[91:92])
                        mqttDefaultConfigReason = serialize.deserialize_uint16(data[92:94])
                        if(mqttDefaultConfigReason == 1):
                            mqttDefaultConfigReason = "MQTT_AUTO_FACTORY_FLASH"
                        elif(mqttDefaultConfigReason == 2):
                            mqttDefaultConfigReason = "MQTT_MANUAL_FACTORY"
                        elif(mqttDefaultConfigReason == 4):
                            mqttDefaultConfigReason = "MQTT_AUTO_FACTORY_CRC"
                        reply_dict['mqttDefaultConfigReason'] = mqttDefaultConfigReason
                        reply_dict['DCU_NUMBER'] = serialize.deserialize_uint32(data[94:98])
                        Mains_Bat_Mode = "mains"
                        if(data[98]== 0):
                            Mains_Bat_Mode = "battery"
                        reply_dict['Mains_Bat_Mode']=Mains_Bat_Mode
                        sim = "sim1"
                        if(data[99] == 0x32):
                            sim="sim2"
                        elif(data[99]==0x31):
                            sim="sim1"
                        else:
                            sim="sim not found"
                        reply_dict['sim status']=sim




                if len(tap_packet.data) == 8:
                    data=tap_packet.data
                    reply_dict['broadcat_interval']=serialize.deserialize_uint16(data[0:2])
                    reply_dict['push_online']=serialize.deserialize_uint16(data[2:4])
                    reply_dict['push_offline']=serialize.deserialize_uint16(data[4:6])
                    reply_dict['seq_interval']=serialize.deserialize_uint16(data[6:8])

                elif len(tap_packet.data) == 6:
                    data=tap_packet.data
                    reply_dict['broadcat_interval']=serialize.deserialize_uint16(data[0:2])
                    reply_dict['push_online']=serialize.deserialize_uint16(data[2:4])
                    reply_dict['push_offline']=serialize.deserialize_uint16(data[4:6])

                # else:
                #     print SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)

                print ('isReturn',isReturn)
                if (isReturn == True):
                    entry = reply_dict

                else:
                    entry = 'ok'
                    for key in reply_dict.keys():
                        print (key," : ",reply_dict[key])


            if param_type == UINT64:
                if len(tap_packet.data) == 8:
                    print (' '.join(format(n, '02X') for n in tap_packet.data))
                    entry = serialize.deserialize_uint64(tap_packet.data)
                else:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))

            if param_type == UINT32:
                if len(tap_packet.data) == 4:
                    entry = serialize.deserialize_uint32(tap_packet.data)
                else:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))

            if param_type == INT32:
                if len(tap_packet.data) == 4:
                    entry = serialize.deserialize_int32(tap_packet.data)
                else:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))

            if param_type == INT8:
                if len(tap_packet.data) == 1:
                    entry = serialize.deserialize_int8(tap_packet.data)
                else:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
            if param_type == DAILY_DEDUCTION_PARAMS:
                ddp = DailyDeductionParams()
                try:
                    ddp.deserialize(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = ddp
            if param_type == LOAD_SURVEY_PARAMS_3P:
                lsp = LoadSurveyParams3P()
                try:
                    lsp.deserialize(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = lsp

            if param_type == METERING_DATA_PARAMS_3P:
                mdp = MeteringDataParams3P()
                if param_number == commandMappingContainer_3P.GET_METERING_DATA_ENERGY_3P:
                    try:
                        mdp.deserialize_p2(tap_packet.data)
                    except IndexError:
                        print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                    entry = mdp.get_packet_p2()
                elif param_number == commandMappingContainer_3P.GET_METERING_DATA_IP_3P:
                    try:
                        mdp.deserialize_p1(tap_packet.data)
                    except IndexError:
                        print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                    entry = mdp.get_packet_p1()

                elif param_number == commandMappingContainer_3P.GET_METERING_DATA_RESOULTION_3P:
                    try:
                        mdp.deserialize_p3(tap_packet.data)
                    except IndexError:
                        print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                    entry = mdp.get_packet_p3()

                elif param_number == commandMappingContainer_3P.GET_METERING_DATA_RESERVED_3P:
                    try:
                        mdp.deserialize_p4(tap_packet.data)
                    except IndexError:
                        print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                    entry = mdp.get_packet_p4()

            if param_type == PREPAID_ACCOUNT_PACKET_3P:
                entry = PrepaidAccountPacket3P()
                try:
                    entry.deserialize(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = entry

            if param_type == SLAB_CONFIGURATION_PACKET_3P:
                entry = SlabConfigurationPacket3P()
                try:
                    entry.deserialize(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = entry

            if param_type == ACCOUNTING_STATE_PACKET_3P:
                entry = AccountingStatePacket3P()
                try:
                    entry.deserialize(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = entry

            if param_type == FIXED_DEDUCTION_PACKET_3P:
                entry = FixedDeductionPacket3P()
                try:
                    entry.deserialize(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = entry

            if param_type == SURVEY_PACKET_3P:
                entry = LoadSurveyPacket3P()
                try:
                    entry.deserialize(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = entry

            if param_type == EVENT_RECORD_PACKET_3P:
                entry = EventRecordPacket3P()
                try:
                    entry.deserialize(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = entry
            if param_type == EVENT_RECORD_TOTAL_PACKET:
                entry = EventRecordNumber3P()
                try:
                    entry.deserialize(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = entry

            if param_type == BILLING_PARAMS_3P:
                entry = BillingParams3P()
                try:
                    entry.deserialize_billing_params(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = entry.get_billing_params_packet()

            if param_type == SYS_PARAMS_1_PACKET_3P:
                entry = BillingParams3P()
                try:
                    entry.deserialize_sys_params(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = entry.get_sys_packet()

            if param_type == SYS_PARAMS_3P:
                entry = SystemsCommands3P()
                if param_number == commandMappingContainer_3P.GET_SYS_PARAMS_DATA_3P:
                    try:
                        entry.deserialize_sys_params_data(tap_packet.data)
                    except IndexError:
                        print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                    entry = entry.get_sys_params_data()
                elif param_number == commandMappingContainer_3P.GET_SYS_PARAMS_PROFILE_3P:
                    try:
                        entry.deserialize_sys_params_profile(tap_packet.data)
                    except IndexError:
                        print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                    entry = entry.get_sys_params_profile()

            if param_type == DLMS_DBG_PACKET_3P:
                entry = BillingParams3P()
                try:
                    entry.deserialize_dlms_params(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = entry.get_dlms_debug_packet()
            # print "Address:", str(tap_packet.src_addr)
            # print "Entry:", entry
            if entry != '':
                full_data_list.append([entry, str(tap_packet.src_addr),int(tap_packet.dest_addr.dump_to_integer())])
        return full_data_list

    def set_param(self, slave_address, param_number, value, param_type):
        """
        This function is used execute commands like "set_power_limit".
        To create the correct payload for TAP layer, this function appends the param_number
        (which is the mapped command number for a command such as "set power_limit").
        It then also appends the serialized bytearray of the "value" argument
        Thus, the payload looks like "30008 {serialized_value}"
        :param str param_number: The mapped command number of the parameter which is being asked for.\
            Such as 30000 for "address", 30010 for "unlock" etc.
        :param int param_type: Tells how the "value" argument should be serialized\
            to create the TAP payload
        :param value: type of "value" can be variable. It can be an int or DailyDeductionParams etc.\
            This value is serialized and appended to the TAP payload
        """
        cmd = bytearray()
        cmd.extend(serialize.serialize_uint16(param_number))
        while len(cmd) < SET_PARAM_HEADER_SIZE:
            cmd.append('\x00')

        if param_type == UINT32:
            cmd.extend(serialize.serialize_uint32(value))

        if param_type == 59922:
            cmd.extend(serialize.serialize_uint16(value))

        if param_type == 59923:
            cmd.extend(serialize.serialize_uint8(value))

        if param_type == INT32:
            cmd.extend(serialize.serialize_int32(value))
        if param_type == INT8:
            cmd.extend(serialize.serialize_int8(value))
        if param_type == DAILY_DEDUCTION_PARAMS:
            cmd.extend(value.serialize())
        if param_type == LOAD_SURVEY_PARAMS:
            cmd.extend(value.serialize())
        if param_type == LOAD_SURVEY_PARAMS_3P:
            cmd.extend(value.serialize())
        if param_type == SLAB_CONFIGURATION_PACKET_3P:
            cmd.extend(value.serialize())
        if param_type == FIXED_DEDUCTION_PACKET_3P:
            cmd.extend(value.serialize())
        if param_type == 98989:
            cmd.extend(value)
        if param_type == MAXIMUM_DEMAND_PACKET:
            cmd.extend(value.serialize())
        if param_type == BYTE_ARRAY:
            cmd.extend(value[0:8])

        # self.my_address=Address(address_integer=param_number)
        self.my_address=Address("1.78.72.201")

        self.my_tap_handler.send_packet(self.my_address, slave_address, self.MASTER_PORT, self.SLAVE_PORT, cmd)
        try:
            tap_packets = self.my_tap_handler.get_packet_from(slave_address, self.SLAVE_PORT)
        except TAPError as e:
            print ("SimpletermError_3P:")
            # raise SimpletermError_3P(SimpletermError_3P.TAP_ERROR, tap_error=e)
        else:
            full_list = []
            for tap_packet in tap_packets:
                found=False
                for key, val in stringMappingContainer_3P.items():
                    if len(tap_packet.data)==2:
                        if key == serialize.deserialize_uint16(tap_packet.data, "reverse"):
                            full_list.append([val, str(tap_packet.src_addr),int(tap_packet.dest_addr.dump_to_integer())])
                            found=True
            #     if not found:
            #         print "Reply is not mapped in string mappingcontainer  ::",serialize.deserialize_uint16(tap_packet.data, "reverse")
            print (full_list)
            return full_list



    def set_and_get_param(self, slave_address, command, set_param, set_param_type, get_param_type):
        """
        This function is used execute commands like "set_power_limit".
        To create the correct payload for TAP layer, this function appends the param_number
        (which is the mapped command number for a command such as "set power_limit").
        It then also appends the serialized bytearray of the "value" argument
        Thus, the payload looks like "30008 {serialized_value}"
        :param str param_number: The mapped command number of the parameter which is being asked for.\
            Such as 30000 for "address", 30010 for "unlock" etc.
        :param int param_type: Tells how the "value" argument should be serialized\
            to create the TAP payload
        :param value: type of "value" can be variable. It can be an int or DailyDeductionParams etc.\
            This value is serialized and appended to the TAP payload
        """

        cmd = bytearray()
        cmd.extend(serialize.serialize_uint16(command))
        #print "Command :" + str(command)
        while len(cmd) < SET_PARAM_HEADER_SIZE:
            cmd.append('\x00')
        if set_param_type == UINT32:
            cmd.extend(serialize.serialize_uint32(set_param))
        if set_param_type == BYTE_ARRAY:
            cmd.extend(set_param[0:8])
            for byte in cmd:
                hex(byte)

        # self.my_address=Address(address_integer=command)

        self.my_address=Address("1.78.72.201")
        self.my_tap_handler.send_packet(self.my_address, slave_address, self.MASTER_PORT, self.SLAVE_PORT, cmd)
        try:
            tap_packets = self.my_tap_handler.get_packet_from(slave_address, self.SLAVE_PORT)
        except TAPError as e:
            raise SimpletermError_3P(SimpletermError_3P.TAP_ERROR, tap_error=e)
        full_data_list = []
        for tap_packet in tap_packets:
            entry = ''
            if (get_param_type==98989):
                return tap_packet.data
            if (get_param_type == SURVEY_PACKET_3P):
                entry = LoadSurveyPacket3P()
                try:
                    entry.deserialize(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = entry
            if (get_param_type == EVENT_RECORD_PACKET_3P):
                entry = EventRecordPacket3P()
                try:
                    entry.deserialize(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = entry

            if get_param_type == CRC_BUNDLE_3P:
                crc = CrcDataPacket3P()
                try:
                    crc.deserialize_crc_packet1(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = crc.get_crc_packet1()

            if get_param_type == DAILY_PROFILE_3P:
                entry = LoadSurveyPacket3P()
                try:
                    entry.deserialize_daily_profile(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = entry.get_daily_profile_packet()

            if get_param_type == BILLING_LOG_PACKET_3P:
                entry = BillingParams3P()
                try:
                    entry.deserialize_billing_log_packet(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = entry.get_billing_log_packet()

            if get_param_type == BILLING_HISTORY_PACKET_3P:
                entry = BillingParams3P()
                try:
                    entry.deserialize_billing_history_packet(tap_packet.data)
                except IndexError:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))
                entry = entry.get_billing_history_packet()

            if get_param_type == UINT32:
                if len(tap_packet.data) == 4:
                    entry = serialize.deserialize_uint32(tap_packet.data)
                else:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))

            if get_param_type == UINT32_BE:
                if len(tap_packet.data) == 4:
                    entry = serialize.deserialize_uint32(tap_packet.data, order="reverse")
                else:
                    print (SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet))

            if get_param_type == BUNDLE_3P:
                bdl = MeteringDataParamsBundle3P()
                try:
                    bdl.deserialize_packet_bundle(tap_packet.data)
                    entry = bdl.get_packet_bundle()
                except IndexError:
                    print ("Index Error in 3P bundle")
                    pass
            if ((command == commandMappingContainer_3P.GET_MAINS_BAT_LOG_BY_INDEX)):# and (source_type=="VDCU-MSP")):
                toRet ={}
                data = tap_packet.data
                print ([x for x in data])
                mode = "Mains"
                if(0 == data[0]):
                    mode = "Battery"
                toRet["Wokring Mode = "] = mode
                onTimeBatt = serialize.deserialize_uint32(data[1:5])
                toRet["Battery On Time = "]=datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=onTimeBatt)
                offTimeBatt = serialize.deserialize_uint32(data[5:9])
                toRet["Battery Off Time = "]=datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=offTimeBatt)
                battOffCon = data[10]
                if(battOffCon == 1):
                    battOffCon = "Time over1"
                elif(battOffCon == 2):
                    battOffCon = "Low Battery"
                else:
                    battOffCon = "Mains supply"
                toRet["Battery Off cond  ition = "]=battOffCon
                # myTime = ((data[4]<<24)+(data[3]<<16)+(data[2]<<8)+data[1])
                # toRet["Time of Change = "] = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=myTime)
                for key in toRet.keys():
                    # print key,":\t\t",toRet[key]
                    print(f"{key}:\t\t{toRet[key]}")
                entry = toRet
                # return toRet

            if ((command == commandMappingContainer_3P.GET_SIM_SWITCH_ENTRY_BY_INDEX)):# and (source_type=="VDCU-MSP")):
                toRet ={}
                data=tap_packet.data
                sim = "UNKNOWN"
                myTime = ((data[4]<<24)+(data[3]<<16)+(data[2]<<8)+data[1])
                print( [x for x in data])
                if(0x31 == data[0]):
                    sim = "SIM 1"
                elif(0x32 == data[0]):
                    sim = "SIM 2"
                toRet["Sim Status = "] = sim
                toRet["Time of Change = "] = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=myTime)
                for key in toRet.keys():
                    # print key,"\t\t",toRet[key]
                    print(f"{key}:\t\t{toRet[key]}")
                # return toRet
                entry = toRet

            if((command == commandMappingContainer_3P.GET_METER_LOG_BY_INDEX_VDCU)):# and (source_type=="VDCU-MSP")):
                toRet ={}
                data=tap_packet.data
                mtrAddr = str(data[3])+"."+str(data[2])+"."+str(data[1])+"."+str(data[0])
                toRet['Meter Address = ']=mtrAddr
                toRet['Meter type    = ']=str(data[4])
                for key in toRet.keys():
                    print(key,"\t\t",toRet[key])
                # return# toRet
                entry = toRet
                    # raise SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            # print "Entry is:", entry
            if entry != '':
                # print "Address:", str(tap_packet.src_addr)
                # print "Entry:", entry
                full_data_list.append([entry, str(tap_packet.src_addr),int(tap_packet.dest_addr.dump_to_integer())])
        return full_data_list
