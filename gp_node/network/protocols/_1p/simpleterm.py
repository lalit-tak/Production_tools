import time
import datetime
"""
Implements master side of Simpleterm protocol
"""
import binascii
from gp_node.network.protocols.common.tap import TAPError, TAPHandler, TAPError
from gp_node.network.protocols.common.protocol import ProtocolMaster, ProtocolError
from gp_node.network.protocols.packets._1p.daily_deduction_params import DailyDeductionParams
from gp_node.network.protocols.packets._1p.load_survey_params import LoadSurveyParams
from gp_node.network.protocols.packets._1p.tamper_record_packet import TamperRecordPacket
from gp_node.network.protocols.packets._1p.bundle import Bundle
from gp_node.network.protocols.packets._1p.daily_load_profile_packet import DailyLoadProfilePacket
from gp_node.network.protocols.packets._1p.log_packet import LogPacket
from gp_node.network.protocols.packets._1p.prepaid_account_packet import PrepaidAccountPacket
from gp_node.network.protocols.packets._1p.slab_packet import SlabConfigurationPacket
from gp_node.network.protocols.packets._1p.accounting_state_packet import AccountingStatePacket
from gp_node.network.protocols.packets._1p.fixed_deduction_packet import FixedDeductionPacket
from gp_node.network.protocols.packets._1p.maximum_demand_packet import MaximumDemandPacket
from gp_node.network.protocols.packets._1p.energy_history_packet import EnergyHistoryPacket
from gp_node.network.protocols.packets._1p.event_record_packet import EventRecordPacket, EventRecordNumber
from gp_node.network.protocols.packets._1p.gas_meter_event_packet import GasEventRecordPacket, GasEventRecordNumber
from gp_node.network.protocols.packets._1p.metering_data_packet import MeteringDataPacket
from gp_node.network.protocols.packets._1p.gas_metering_data_packet import GasMeteringDataPacket
from gp_node.network.protocols.packets._1p.gas_metering_data_packet import GasMeteringTariffPacket
from gp_node.network.protocols.packets._1p.syncstream_bundle import SyncstreamBundle
from gp_node.network.protocols.packets._1p.bundle_1p import DCUBundlePacket
from gp_node.network.protocols.packets._1p.meter_para_1p import IP_MeterPara
from gp_node.network.protocols.packets._1p.relay_para_1p import IP_RelayPara
from gp_node.network.protocols.packets._1p.tariff_packet import TariffPacket
from gp_node.network.protocols.packets._1p.RF_MEM_DATA import RFMemData
from gp_node.network.protocols._1p.command_mapping_container import commandMappingContainer
import gp_node.utils.serialize as serialize
from gp_node.network.protocols.packets._1p.billing_md_packet import BillingMdPacket
from gp_node.network.protocols.packets.energy_cop.ecop_data_stream_packet import EcopDataStreamPacket
from gp_node.network.protocols.common.string_mapping_container import stringMappingContainer
from gp_node.network.protocols.packets._1p.tod_packet import TodConfigurationPacket
from gp_node.network.protocols.packets._1p.power_limit_tod_packet import PowerLimitTodPacket
from gp_node.network.protocols.packets._1p.power_limit_tod_packet import PowerLimitParamsPacket
from gp_node.network.protocols._3p.string_mapping_container import stringMappingContainer_3P # patch
from gp_node.network.protocols.common.data_type_container import INT8, UINT8, UINT32 ,UINT16,INT32, UINT64,\
    BYTE_ARRAY, ECOP_PACKET,TAMPER_RECORD_PACKET, DAILY_DEDUCTION_PARAMS,DATA_ARRAY, RESPONSE_PACKET,\
    BUNDLE, LOG_PACKET, TARIFF_PACKET,LOAD_SURVEY_PARAMS, MAXIMUM_DEMAND_PACKET,EVENT_RECORD_TOTAL_PACKET,\
    PREPAID_ACCOUNT_PACKET, SLAB_CONFIGURATION_PACKET, ACCOUNTING_STATE_PACKET, FIXED_DEDUCTION_PACKET,\
    ENERGY_HISTORY_PACKET, EVENT_RECORD_PACKET, DAILY_LOAD_PROFILE_PACKET,METERING_DATA_PACKET,\
    SYNCSTREAM_BUNDLE, GET_TIME_LEFT, PREPAID_ACCOUNT_PACKET_3P, SLAB_CONFIGURATION_PACKET_3P,ACCOUNTING_STATE_PACKET_3P,\
    FIXED_DEDUCTION_PACKET_3P, SURVEY_PACKET_3P, EVENT_RECORD_PACKET_3P,LOAD_SURVEY_PARAMS_3P,\
    METERING_DATA_PARAMS_3P, DAILY_PROFILE_3P, BILLING_PARAMS_3P, BILLING_LOG_PACKET_3P,\
    BILLING_HISTORY_PACKET_3P, SYS_PARAMS_1_PACKET_3P, BUNDLE_1P, DLMS_DBG_PACKET_3P,UINT32_BE,TOD_CONFIGURATION_PACKET,\
    GET_TOD_POWER_LIMIT,BILLING_MD_PACKET,RELAY_STATUS_1P, GET_PARAMS_POWER_LIMIT,POWER_EVENT_RECORD,BYTE_ARRAY_IPV6,\
    DCU_TOPICS,GAS_METERING_DATA_PACKET,GAS_METERING_TARIFF_PACKET,GAS_METERING_TARIFF,GAS_EVENT_PACKET,GAS_NUM_EVENT_PACKET

SET_PARAM_HEADER_SIZE = 2

class SimpletermError(ProtocolError):
    """
    error codes:

    GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH: raised when number of bytes in reply to a get_param query\
            does not contain expected number of bytes
    """
    GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH = 1



class SimpletermMaster:


    """
    """

    def __init__(self, PortId, my_address, my_tap_handler):

        self.SLAVE_PORT = 4
        self.REC_SLAVE_ID = int(PortId)
        self.MASTER_PORT = 4
        self.my_address = my_address
        self.my_tap_handler = my_tap_handler

    def execute_command(self, slave_address, command_number):
        """
        Sends the command_string argument as it is
        to the underlying TAP layer & returns the reply from the TAP layer 
        as it is. This function is a very thin layer on top of TAP.

        :param str command_number: The mapped command number of the parameter which is being asked for.\
            Such as 10025 for "lock_state", 10031 for "fd_reset" etc.
        :returns: The bytearray as returned by the underlying TAP layer
        """
        src_addr_value = self.my_address.dump_to_integer()
        src_addr_value = (src_addr_value & 0xFF0000FF) + ((command_number<<8)&0x00FFFF00)
        self.my_address.load_from_integer(src_addr_value)

        command = bytearray()
        command.extend(serialize.serialize_uint16(command_number))
        command.append(0)
        self.my_tap_handler.send_packet(self.my_address, slave_address, 
                                        self.SLAVE_PORT, self.MASTER_PORT, command.strip())

        try:
            packet = self.my_tap_handler.get_packet_from(slave_address, self.REC_SLAVE_ID, self.my_address)
        except TAPError as e:
            raise SimpletermError(SimpletermError.TAP_ERROR, e)
        for key,val in stringMappingContainer.items():
            if key == serialize.deserialize_uint16(packet.data,"reverse"):
                return val
            elif key == serialize.deserialize_uint16(packet.data):
                return val


    def get_param(self, slave_address, param_number, param_type, additional_param = 0,isReturn=False):
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
        # print 'param_typefirst',param_type

        src_addr_value = self.my_address.dump_to_integer()
        src_addr_value = (src_addr_value & 0xFF0000FF) + ((param_number<<8)&0x00FFFF00)
        self.my_address.load_from_integer(src_addr_value)

        cmd = bytearray()
        cmd.extend(serialize.serialize_uint16(param_number))

        self.my_tap_handler.send_packet(self.my_address, slave_address, self.MASTER_PORT, self.SLAVE_PORT, cmd)
        try:
            tap_packet = self.my_tap_handler.get_packet_from(slave_address, self.REC_SLAVE_ID, self.my_address)
        except TAPError as e:
            raise SimpletermError(SimpletermError.TAP_ERROR, tap_error=e)
        # print "data is",tap_packet.data
        if param_type == BYTE_ARRAY:
            return tap_packet.data

        if param_type == UINT32:
            if len(tap_packet.data) >= 4:
                return serialize.deserialize_uint32(tap_packet.data)
            else:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)

        if param_type == UINT16:
            if len(tap_packet.data) >= 2:
                return serialize.deserialize_uint16(tap_packet.data)
            else:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)

        if param_type == INT32:
            if len(tap_packet.data) >= 4:
                return serialize.deserialize_int32(tap_packet.data)
            else:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
        
        if param_type == BILLING_MD_PACKET:
            entry = BillingMdPacket() 
            if param_number == commandMappingContainer.GET_BILLING_INFO:
                try:
                    entry.deserialize_billing_info(tap_packet.data)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH,
                                          tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return entry
                return entry.get_billing_info_packet()
            elif param_number == commandMappingContainer.GET_INSTANTANEOUS_DEMAND:
                try:
                    entry.deserialize_get_instantaneous_demand(tap_packet.data)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH,
                                          tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return entry
                return entry.get_instantaneous_demand_packet()

        if param_type == INT8:
            if len(tap_packet.data) >= 1:
                return serialize.deserialize_int8(tap_packet.data)
            else:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
        
        if param_type == UINT8:
            if len(tap_packet.data) >= 1:
                return serialize.deserialize_uint8(tap_packet.data,'reverse')
            else:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)

        if param_type == BYTE_ARRAY_IPV6:
            temp_str = ''
            if len(tap_packet.data) >38:
                for x in xrange(0,len(tap_packet.data)):
                    temp_str += chr(tap_packet.data[x])
                return temp_str
            else:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)     

        if param_type == TAMPER_RECORD_PACKET:
            if param_number == commandMappingContainer.GET_EARTH_TAMPER_RECORD:
                tamper_type = "earth"
            elif param_number == commandMappingContainer.GET_REV_TAMPER_RECORD:
                tamper_type = "rev"
            elif param_number == commandMappingContainer.GET_NM_TAMPER_RECORD:
                tamper_type = "nm"
            elif param_number == commandMappingContainer.GET_ND_TAMPER_RECORD:
                tamper_type = "nd"
            elif param_number == commandMappingContainer.GET_COVER_TAMPER_RECORD:
                tamper_type = "cover"
            elif param_number == commandMappingContainer.GET_MAG_TAMPER_RECORD:
                tamper_type = "mag"
            trp = TamperRecordPacket(tamper_type)
            try:
                trp.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return trp

        if param_type == DAILY_DEDUCTION_PARAMS:
            ddp = DailyDeductionParams()
            try:
                ddp.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return ddp

        if param_type == LOAD_SURVEY_PARAMS:
            lsp = LoadSurveyParams()
            try:
                lsp.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return lsp

        if param_type == BUNDLE:
            entry = Bundle()
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry

        if param_type == DAILY_LOAD_PROFILE_PACKET:
            entry = DailyLoadProfilePacket()
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry

        if param_type == LOG_PACKET:
            entry = LogPacket()
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry

        if param_type == PREPAID_ACCOUNT_PACKET:
            entry = PrepaidAccountPacket() 
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry

        if param_type == SLAB_CONFIGURATION_PACKET:
            entry = SlabConfigurationPacket()
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry

        if param_type == ACCOUNTING_STATE_PACKET:
            entry = AccountingStatePacket() 
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry

        if param_type == GET_TOD_POWER_LIMIT:
            entry = PowerLimitTodPacket() 
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry

        if param_type == GET_PARAMS_POWER_LIMIT:
            entry = PowerLimitParamsPacket() 
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry

        if param_type == TOD_CONFIGURATION_PACKET:
            entry = TodConfigurationPacket() 
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry




        if param_type == FIXED_DEDUCTION_PACKET:
            entry = FixedDeductionPacket()
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry

        if param_type == MAXIMUM_DEMAND_PACKET:
            if param_number == commandMappingContainer.GET_PAST_ACTIVE_MD_1 or param_number == commandMappingContainer.GET_PAST_REACTIVE_MD_1 or param_number == commandMappingContainer.GET_PAST_APPARENT_MD_1:
                MD_month = 1
            elif param_number == commandMappingContainer.GET_PAST_ACTIVE_MD_2 or param_number == commandMappingContainer.GET_PAST_REACTIVE_MD_2 or param_number == commandMappingContainer.GET_PAST_APPARENT_MD_2:
                MD_month = 2
            elif param_number == commandMappingContainer.GET_PAST_ACTIVE_MD_3 or param_number == commandMappingContainer.GET_PAST_REACTIVE_MD_3 or param_number == commandMappingContainer.GET_PAST_APPARENT_MD_3:
                MD_month = 3
            elif param_number == commandMappingContainer.GET_PAST_ACTIVE_MD_4 or param_number == commandMappingContainer.GET_PAST_REACTIVE_MD_4 or param_number == commandMappingContainer.GET_PAST_APPARENT_MD_4:
                MD_month = 4
            elif param_number == commandMappingContainer.GET_PAST_ACTIVE_MD_5 or param_number == commandMappingContainer.GET_PAST_REACTIVE_MD_5 or param_number == commandMappingContainer.GET_PAST_APPARENT_MD_5:
                MD_month = 5
            elif param_number == commandMappingContainer.GET_PAST_ACTIVE_MD_6 or param_number == commandMappingContainer.GET_PAST_REACTIVE_MD_6 or param_number == commandMappingContainer.GET_PAST_APPARENT_MD_6:
                MD_month = 6
            elif param_number == commandMappingContainer.GET_CURRENT_ACTIVE_MD or param_number == commandMappingContainer.GET_CURRENT_REACTIVE_MD or param_number == commandMappingContainer.GET_CURRENT_APPARENT_MD:
                MD_month = 7
            entry = MaximumDemandPacket(MD_month)
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry


        if param_type == ECOP_PACKET:
            entry = EcopDataStreamPacket()
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry

        if param_type == ENERGY_HISTORY_PACKET:
            if param_number == commandMappingContainer.GET_ACTIVE_ENERGY_HISTORY_1 or param_number == commandMappingContainer.GET_REACTIVE_LEAD_ENERGY_HISTORY_1 or param_number == commandMappingContainer.GET_REACTIVE_LAG_ENERGY_HISTORY_1 or param_number == commandMappingContainer.GET_APPARENT_ENERGY_HISTORY_1:
                month = 1
            elif param_number == commandMappingContainer.GET_ACTIVE_ENERGY_HISTORY_2 or param_number == commandMappingContainer.GET_REACTIVE_LEAD_ENERGY_HISTORY_2 or param_number == commandMappingContainer.GET_REACTIVE_LAG_ENERGY_HISTORY_2 or param_number == commandMappingContainer.GET_APPARENT_ENERGY_HISTORY_2:
                month = 2
            elif param_number == commandMappingContainer.GET_ACTIVE_ENERGY_HISTORY_3 or param_number == commandMappingContainer.GET_REACTIVE_LEAD_ENERGY_HISTORY_3 or param_number == commandMappingContainer.GET_REACTIVE_LAG_ENERGY_HISTORY_3 or param_number == commandMappingContainer.GET_APPARENT_ENERGY_HISTORY_3:
                month = 3
            elif param_number == commandMappingContainer.GET_ACTIVE_ENERGY_HISTORY_4 or param_number == commandMappingContainer.GET_REACTIVE_LEAD_ENERGY_HISTORY_4 or param_number == commandMappingContainer.GET_REACTIVE_LAG_ENERGY_HISTORY_4 or param_number == commandMappingContainer.GET_APPARENT_ENERGY_HISTORY_4:
                month = 4
            elif param_number == commandMappingContainer.GET_ACTIVE_ENERGY_HISTORY_5 or param_number == commandMappingContainer.GET_REACTIVE_LEAD_ENERGY_HISTORY_5 or param_number == commandMappingContainer.GET_REACTIVE_LAG_ENERGY_HISTORY_5 or param_number == commandMappingContainer.GET_APPARENT_ENERGY_HISTORY_5:
                month = 5
            elif param_number == commandMappingContainer.GET_ACTIVE_ENERGY_HISTORY_6 or param_number == commandMappingContainer.GET_REACTIVE_LEAD_ENERGY_HISTORY_6 or param_number == commandMappingContainer.GET_REACTIVE_LAG_ENERGY_HISTORY_6 or param_number == commandMappingContainer.GET_APPARENT_ENERGY_HISTORY_6:
                month = 6
            elif param_number == commandMappingContainer.GET_ACTIVE_ENERGY_HISTORY_7 or param_number == commandMappingContainer.GET_REACTIVE_LEAD_ENERGY_HISTORY_7 or param_number == commandMappingContainer.GET_REACTIVE_LAG_ENERGY_HISTORY_7 or param_number == commandMappingContainer.GET_APPARENT_ENERGY_HISTORY_7:
                month = 7
            entry = EnergyHistoryPacket(month)
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry

        if param_type == EVENT_RECORD_PACKET:
            entry = EventRecordPacket()
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry

        if param_type == POWER_EVENT_RECORD:
            # entry = EventRecordPacket()
            # try:
            #     entry.deserializex(tap_packet.data)
            # except IndexError:
            #     raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            # return entry
            try:

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
                                        157 :'EVT_FIRMWARE_UPGRADE_OCCURENCE',
                                        158 :'EVT_LOAD_LIMIT_SET',
                                        159 :'EVT_LOAD_LIMIT_ENABLE',
                                        160 :'EVT_LOAD_LIMIT_DISABLE',
                                        166 :'EVT_MD_RESET_OCCURENCE',
                                        # Other Related
                                        201 :'EVT_MAGNETIC_TAMPER_OCCURENCE',
                                        202 :'EVT_MAGNETIC_TAMPER_RESTORATION',
                                        203 :'EVT_ND_TAMPER_OCCURENCE',
                                        204 :'EVT_ND_TAMPER_RESTORATION',
                                        207 :'EVT_NM_TAMPER_OCCURENCE',
                                        208 :'EVT_NM_TAMPER_RESTORATION',
                                        213 :'EVT_CHANGE_TO_FORWARD_MODE',
                                        214 :'EVT_CHANGE_TO_IMP_EXP_MODE',
                                        215 :'EVT_OVERLOAD_OCCURENCE',
                                        216 :'EVT_OVERLOAD_RESTORATION',
                                        # Non-Rollover Related
                                        251:'EVT_COVER_OPEN_OCCURENCE',
                                        # Control Related
                                        301 :'EVT_LOAD_SWITCH_DISCONNECTED',
                                        302 :'EVT_LOAD_SWITCH_CONNECTED',
                                        #Grampower Custom Related Events
                                        10008:'EVT_OVER_POWER_OCCURENCE',
                                        10009:'EVT_OVER_POWER_RESTORATION',
                                        # Invalid Event for errors
                                        512:'INVALID_EVT'}

                buf = bytearray()
                buf = tap_packet.data
                dt = datetime.datetime(1970, 1, 1, 0, 0, 0)

                index=0
                length = len(buf)

                if(length ==0):
                    return "No entry found !!!"

                while length > 0:
                    evtId = buf[index]

                    unix_time = ((buf[index+4]<<24)+(buf[index+3]<<16)+(buf[index+2]<<8) +buf[index+1])
                    unix_time_zero = datetime.datetime(1970, 1, 1)
                    dt = unix_time_zero + datetime.timedelta(0, unix_time)

                    print ("Index : "+str(index/5)+"    TimeStamp : "+str(dt)+"    Event : "+VALID_EVENT_NAMES[evtId])
                    index+=5
                    length-=5
                return "Log fetch done !!!"
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return tap_packet   

        if param_type == EVENT_RECORD_TOTAL_PACKET:
            entry = EventRecordNumber()
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry    

        if param_type == GAS_NUM_EVENT_PACKET:
            entry = GasEventRecordNumber()
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry

        if param_type == METERING_DATA_PACKET:
            entry = MeteringDataPacket()
            if param_number == commandMappingContainer.GET_1P_METERING_DATA:
                try:
                    entry.deserialize(tap_packet.data)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
                return entry
            elif param_number == commandMappingContainer.GET_METERING_DATA_DEBUG:
                try:
                    entry.deserialize_nxp_ene_debug(tap_packet.data)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return entry
                return entry.get_nxp_ene_debug_packet()
            elif param_number == commandMappingContainer.GET_1P_METERING_DATA2:
                try:
                    entry.deserialize_metering_data_2(tap_packet.data)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return entry
                return entry.get_metering_data_2()

        if param_type == GAS_METERING_DATA_PACKET:
            entry = GasMeteringDataPacket()
            if param_number == commandMappingContainer.GET_GAS_METERING_DATA:
                try:
                    entry.deserializeMeteringPacket(tap_packet.data)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return entry
                return entry.getMeteringPacket()

        # if param_type == GAS_METERING_TARIFF:
        #     entry = GasMeteringTariffPacket()
        #     if param_number == commandMappingContainer.GET_GAS_TARIFF:
        #         try:
        #             entry.deserializeMeteringTariffPacket(tap_packet.data)
        #         except IndexError:
        #             raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
        #         if (additional_param == commandMappingContainer.PARSE_ONLY):
        #             return entry
        #         return entry.getMeteringTariffPacket()


        if param_type == SYNCSTREAM_BUNDLE:
            entry = SyncstreamBundle()
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return entry

        if param_type == BUNDLE_1P:
            bdl = DCUBundlePacket()
            try:
                bdl.deserialize_packet_bundle(tap_packet.data)                    
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            # return bdl.get_packet_dictionary_bundle()  
            if (additional_param == commandMappingContainer.PARSE_ONLY):
                return bdl
            return bdl.get_packet_bundle()
        if param_type == DATA_ARRAY:
            bdl = IP_MeterPara()
            try:
                bdl.deserialize_packet_bundle(tap_packet.data)                    
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            if (additional_param == commandMappingContainer.PARSE_ONLY):
                return bdl
            return bdl.get_packet_bundle() 
        if param_type == RELAY_STATUS_1P:
            bdl = IP_RelayPara()
            if (param_number == commandMappingContainer.GET_GAS_RELAY_STATUS):
                try:
                    bdl.deserialize_gas_packet(tap_packet.data)                    
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return bdl
                return bdl.get_gas_packet() 
            else:
                try:
                    bdl.deserialize_packet_bundle(tap_packet.data)                    
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return bdl
                return bdl.get_packet_bundle() 
            
        if param_type == TARIFF_PACKET:
            
            entry = TariffPacket() 
            if param_number == commandMappingContainer.GET_PREPAID_INFO:
                
                try:
                    entry.deserializePrepaidInfo(tap_packet.data)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return entry
                return entry.getPacketPrepaidInfo()
            elif param_number == commandMappingContainer.GET_PREPAID_INFO_DATA:
                try:
                    entry.deserializePrepaidLogs(tap_packet.data)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return entry
                return entry.getPacketPrepaidLogs()    
            else:                
                entry = TariffPacket() 
                try:
                    entry.deserializeTariffGroupInfo(tap_packet.data)                    
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return entry
                return entry.getTariffGroupInfo()

        # print 'param_typelast',param_type
        if param_type == DCU_TOPICS:
            offset = 0
            offsetHostName = offset+64
            offsetUsername = offsetHostName+32
            offsetPass = offsetUsername + 32
            offsetDataCollection = offsetPass +32
            offsetDatapush = offsetDataCollection + 32
            offsetDataResponse = offsetDatapush + 32
            offsetConfigOffreason = offsetDataResponse + 2
            offsetPort = offsetConfigOffreason + 4
            offsetDcuNumber = offsetPort + 4
            
            if (isReturn == True):
                reply_dict={}
                reply_dict['Mqtt HostName']=str(tap_packet.data[offset:offsetHostName])
                reply_dict['Mqtt Username']=str(tap_packet.data[offsetHostName:offsetUsername])
                reply_dict['Mqtt Password']=str(tap_packet.data[offsetUsername:offsetPass])
                reply_dict['Data Collection Topic']=str(tap_packet.data[offsetPass:offsetDataCollection])
                reply_dict['Data Pushing Topic']=str(tap_packet.data[offsetDataCollection:offsetDatapush])
                reply_dict['Remote Command Topic']=str(tap_packet.data[offsetDatapush:offsetDataResponse])
                reply_dict['nMqtt Port']=str(serialize.deserialize_uint32(tap_packet.data[offsetConfigOffreason:offsetPort], order="reverse"))
                reply_dict['Dcu Number']=str(serialize.deserialize_uint32(tap_packet.data[offsetPort:offsetDcuNumber], order="reverse"))
                return reply_dict

            reply="Mqtt HostName            :"+str(tap_packet.data[offset:offsetHostName])+\
            "\nMqtt Username            :"+str(tap_packet.data[offsetHostName:offsetUsername])+\
            "\nMqtt Password            :"+str(tap_packet.data[offsetUsername:offsetPass])+\
            "\nData Collection Topic    :"+str(tap_packet.data[offsetPass:offsetDataCollection])+\
            "\nData Pushing Topic       :"+str(tap_packet.data[offsetDataCollection:offsetDatapush])+\
            "\nRemote Command Topic     :"+str(tap_packet.data[offsetDatapush:offsetDataResponse])+\
            "\nMqtt Port                :"+str(serialize.deserialize_uint32(tap_packet.data[offsetConfigOffreason:offsetPort], order="reverse"))+\
            "\nDcu Number               :"+ str(serialize.deserialize_uint32(tap_packet.data[offsetPort:offsetDcuNumber], order="reverse"))
            return reply        

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
        src_addr_value = self.my_address.dump_to_integer()
        src_addr_value = (src_addr_value & 0xFF0000FF) + ((param_number<<8)&0x00FFFF00)
        self.my_address.load_from_integer(src_addr_value)

        cmd = bytearray()
        cmd.extend(serialize.serialize_uint16(param_number))
        while len(cmd) < SET_PARAM_HEADER_SIZE:
            cmd.append('\x00')

        if param_type == UINT32:
            #print "value being serialized :",value
            cmd.extend(serialize.serialize_uint32(value))
        if param_type == UINT16:
            cmd.extend(serialize.serialize_uint16(value))
        if param_type == INT32:
            cmd.extend(serialize.serialize_int32(value))
        if param_type == INT8:
            cmd.extend(serialize.serialize_int8(value))
        if param_type == UINT8:
            cmd.extend(serialize.serialize_uint8(value))  
        if param_type == DAILY_DEDUCTION_PARAMS:
            cmd.extend(value.serialize())
        if param_type == LOAD_SURVEY_PARAMS:
            cmd.extend(value.serialize())
        if param_type == SLAB_CONFIGURATION_PACKET:
            cmd.extend(value.serialize())
        if param_type == FIXED_DEDUCTION_PACKET:
            cmd.extend(value.serialize())
        if param_type == MAXIMUM_DEMAND_PACKET:
            cmd.extend(value.serialize())
        if param_type == TOD_CONFIGURATION_PACKET:
            cmd.extend(value.serialize())
        if param_type == TARIFF_PACKET:
            cmd.extend(value.serialize())
        if param_type == GET_TOD_POWER_LIMIT:
            cmd.extend(value.serialize())
        if param_type == GAS_METERING_TARIFF_PACKET:
            cmd.extend(value.serializeMeteringTariffPacket())
        if param_type == GAS_METERING_TARIFF:
            cmd.extend(value.serializeMeteringTariff())
        if param_type == BYTE_ARRAY:
            length_ = len(value)
            cmd.extend(value[0:length_])
            
        self.my_tap_handler.send_packet(self.my_address, slave_address, self.MASTER_PORT, self.SLAVE_PORT, cmd)
        try:
            tap_packet = self.my_tap_handler.get_packet_from(slave_address, self.REC_SLAVE_ID, self.my_address)
        except TAPError as e:
            raise SimpletermError(SimpletermError.TAP_ERROR, tap_error=e)
        for key,val in stringMappingContainer.items():
            if key == serialize.deserialize_uint16(tap_packet.data,"reverse"):
                return val
            elif key == serialize.deserialize_uint16(tap_packet.data):
                return val

    #######################################
    def set_rc_param(self, slave_address, param_number, value, param_type):
        """
        this is a temporary block to handle radiocraft set function
        this needs to be integrated in set paramsss function
        """

        src_addr_value = self.my_address.dump_to_integer()
        src_addr_value = (src_addr_value & 0xFF0000FF) + ((param_number<<8)&0x00FFFF00)
        self.my_address.load_from_integer(src_addr_value)

        cmd = bytearray()
        cmd.extend(serialize.serialize_uint16(param_number))
        while len(cmd) < SET_PARAM_HEADER_SIZE:
            cmd.append('\x00')

        if param_type == UINT32:
            cmd.extend(serialize.serialize_uint32(value))
        if param_type == INT32:
            cmd.extend(serialize.serialize_int32(value))
        if param_type == INT8:
            cmd.extend(serialize.serialize_int8(value))
        if param_type == BYTE_ARRAY:
            cmd.extend(value[0:8])

        self.my_tap_handler.send_packet(self.my_address, slave_address, self.MASTER_PORT, self.SLAVE_PORT, cmd)
        try:
            tap_packet = self.my_tap_handler.get_packet_from(slave_address, self.REC_SLAVE_ID, self.my_address)
        except TAPError as e:
            raise SimpletermError(SimpletermError.TAP_ERROR, tap_error=e)
        else:
            #print "i M in KEy , Value"
            for key,val in stringMappingContainer_3P.items():
                if key == serialize.deserialize_uint16(tap_packet.data, "reverse"):
                    return val

                elif key == serialize.deserialize_uint16(tap_packet.data):
                    return val    


    ##########################################
    def set_and_get_param(self, slave_address, param_number, set_param, set_param_type, get_param_type, additional_param = 0):
        """
        This is a temporary block to handle radiocraft get and set function
        this needs to be integrated in set and get params function
        """
        src_addr_value = self.my_address.dump_to_integer()
        src_addr_value = (src_addr_value & 0xFF0000FF) + ((param_number<<8)&0x00FFFF00)
        self.my_address.load_from_integer(src_addr_value)

        cmd = bytearray()
        cmd.extend(serialize.serialize_uint16(param_number))
        while len(cmd) < SET_PARAM_HEADER_SIZE:
            cmd.append('\x00')

        if set_param_type == UINT32:
            cmd.extend(serialize.serialize_uint32(set_param))
        if set_param_type == INT8:
            cmd.extend(serialize.serialize_uint8(set_param))
        if set_param_type == BYTE_ARRAY:
            cmd.extend(set_param)

        if param_number == commandMappingContainer.IMAGE_TRANSFER_TAP:
            self.my_tap_handler.send_packet(self.my_address, slave_address, self.REC_SLAVE_ID, self.REC_SLAVE_ID, cmd)
        else :
            self.my_tap_handler.send_packet(self.my_address, slave_address, self.MASTER_PORT, self.SLAVE_PORT, cmd)
        #time.sleep(2)
        try:
            tap_packet = self.my_tap_handler.get_packet_from(slave_address, self.REC_SLAVE_ID, self.my_address)
        except TAPError as e:
            raise SimpletermError(SimpletermError.TAP_ERROR, tap_error=e)

        if get_param_type == UINT32:
            if len(tap_packet.data) == 4:
                return serialize.deserialize_uint32(tap_packet.data)
            else:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)

        if get_param_type == UINT16:
            if len(tap_packet.data) == 2:
                return serialize.deserialize_uint16(tap_packet.data,"reverse")
            else:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)

        if get_param_type == UINT8:
            if len(tap_packet.data) == 1:
                return serialize.deserialize_uint8(tap_packet.data)
            else:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)

        if (get_param_type == BUNDLE):
            entry = Bundle()
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            if (additional_param == commandMappingContainer.PRINT_DIRECT):
                return entry.printlog(set_param)
            return entry

        if (get_param_type == DAILY_LOAD_PROFILE_PACKET):
            entry = DailyLoadProfilePacket()
            try:
                entry.deserialize(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            if (additional_param == commandMappingContainer.PRINT_DIRECT):
                return entry.printlog(set_param)
            return entry
            
        if (get_param_type == EVENT_RECORD_PACKET):
            entry = EventRecordPacket()
            try:
                evtsize = ((set_param[0]<<24)+(set_param[1]<<16)+(set_param[2]<<8) +set_param[3])
                entry.deserialize(tap_packet.data,evtsize)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            if (additional_param == commandMappingContainer.PRINT_DIRECT):
                payload = ((set_param[4]<<24)+(set_param[5]<<16)+(set_param[6]<<8) +set_param[7])
                return entry.printlog(payload)
            else:
                return entry

        if (get_param_type == GAS_EVENT_PACKET):
            entry = GasEventRecordPacket()
            try:
                evtsize = ((set_param[4]<<24)+(set_param[5]<<16)+(set_param[6]<<8) +set_param[7])
                return entry.deserializePacket(tap_packet.data,evtsize)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            # if (additional_param == commandMappingContainer.PRINT_DIRECT):
            #     payload = ((set_param[4]<<24)+(set_param[5]<<16)+(set_param[6]<<8) +set_param[7])
            #     return entry.printlog(payload)

        if get_param_type == POWER_EVENT_RECORD:
            try:
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
                            252 :'EVT_SWITCH_WELD_OCCURANCE',
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

                buf = bytearray()
                buf = tap_packet.data
                dt = datetime.datetime(1970, 1, 1, 0, 0, 0)

                index=0
                length = len(buf)

                if(length ==0):
                    return "No entry found !!!"

                while length > 0:
                    evtId = buf[index]

                    unix_time = ((buf[index+4]<<24)+(buf[index+3]<<16)+(buf[index+2]<<8) +buf[index+1])
                    unix_time_zero = datetime.datetime(1970, 1, 1)
                    dt = unix_time_zero + datetime.timedelta(0, unix_time)

                    print ("Index : "+str(set_param*10+index/5)+"    TimeStamp : "+str(dt)+"    Event : "+VALID_EVENT_NAMES[evtId])
                    index+=5
                    length-=5
                return "Log fetch done !!!"
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return tap_packet

        if get_param_type == BILLING_MD_PACKET:
            entry = BillingMdPacket()
            if param_number == commandMappingContainer.GET_BILLING_BY_INDEX:
                try:
                    entry.deserialize_billing_by_index(tap_packet.data)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH,
                                          tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return entry
                return entry.get_billing_by_index_packet()
            elif param_number == commandMappingContainer.GET_FETCH_BILLING_BY_INDEX:
                try:
                    entry.deserialize_billing_by_index(tap_packet.data)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH,
                                          tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return entry
                return entry.get_billing_by_index_packet()
            elif param_number == commandMappingContainer.GET_TOD_BILLING_BY_INDEX:
                try:
                    entry.deserialize_tod_params(tap_packet.data)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH,
                                          tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return entry
                return entry.get_tod_params()
            elif param_number == commandMappingContainer.GET_BILLING_DATA_BY_INDEX:
                try:
                    entry.deserialize_billing_data_params(tap_packet.data)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH,
                                          tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return entry
                return entry.get_billdata_params()
                
        if get_param_type == RESPONSE_PACKET:
            for key,val in stringMappingContainer.items():
                if key == serialize.deserialize_uint16(tap_packet.data,"reverse"):
                    return val

        if get_param_type == BYTE_ARRAY:
            return  tap_packet.data;

        # if get_param_type == BYTE_ARRAY:
        #     if param_number == commandMappingContainer_3P.GET_RC_CONFIG_3P:
        #         entry = RFMemData()
        #         try:
        #             entry.deserialize_packet_RFMemDate(tap_packet.data) 

        #         except IndexError:
        #             raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH,
        #                                       tap_packet=tap_packet)    
        #         return  entry.RF_mem_data()
        #     else:
        #         return  tap_packet.data;


        if get_param_type == METERING_DATA_PACKET:
            entry = MeteringDataPacket()
            if param_number == commandMappingContainer.GET_NM_ENE_BY_INDEX:
                try:
                    entry.deserialize_nm_ene_by_index(tap_packet.data)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH,
                                          tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return entry
                return entry.get_nm_ene_by_index_packet()
            elif param_number == commandMappingContainer.GET_ENE_PARAMS_BY_INDEX:
                try:
                    entry.deserialize_nxp_ene_by_index(tap_packet.data)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH,
                                          tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return entry
                return entry.get_nxp_ene_by_index_packet()
            elif param_number == commandMappingContainer.GET_METERING_DATA_DEBUG:
                try:
                    entry.deserialize_nxp_ene_HRdebug(tap_packet.data)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
                if (additional_param == commandMappingContainer.PARSE_ONLY):
                    return entry
                return entry
                # .get_nxp_ene_debug_packet_hr()

        if get_param_type == TARIFF_PACKET:
            entry = TariffPacket()
            try:
                entry.deserializePrepaidLogs(tap_packet.data)
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            if (additional_param == commandMappingContainer.PARSE_ONLY):
                return entry
            return entry.getPacketPrepaidLogs()

        if get_param_type == GAS_METERING_TARIFF:
            entry = GasMeteringTariffPacket()
            if param_number == commandMappingContainer.GET_GAS_TARIFF:
                try:
                    return entry.deserializeMeteringTariffPacket(tap_packet.data, set_param)
                except IndexError:
                    raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
                # if (additional_param == commandMappingContainer.PARSE_ONLY):
                #     return entry
                # return entry.getMeteringTariffPacket()

        if get_param_type == BUNDLE_1P:
            bdl = DCUBundlePacket()
            try:
                bdl.deserialize_packet_bundle(tap_packet.data)                    
            except IndexError:
                raise SimpletermError(SimpletermError.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            # return bdl.get_packet_dictionary_bundle()  
            if (additional_param == commandMappingContainer.PARSE_ONLY):
                return bdl
            return bdl.get_packet_bundle()

    def set_and_get_rc_param(self, slave_address, command, set_param, set_param_type, get_param_type): 

        src_addr_value = self.my_address.dump_to_integer()
        src_addr_value = (src_addr_value & 0xFF0000FF) + ((command<<8)&0x00FFFF00)
        self.my_address.load_from_integer(src_addr_value)

        cmd = bytearray()
        cmd.extend(serialize.serialize_uint16(command))
        while len(cmd) < SET_PARAM_HEADER_SIZE:
            cmd.append('\x00')
        if set_param_type == UINT32:
            cmd.extend(serialize.serialize_uint32(set_param))
        if set_param_type == BYTE_ARRAY:
            cmd.extend(set_param[0:8])
            for byte in cmd:
                hex(byte)
        self.my_tap_handler.send_packet(self.my_address, slave_address, self.MASTER_PORT, self.SLAVE_PORT, cmd)
        try:
            tap_packet = self.my_tap_handler.get_packet_from(slave_address, self.REC_SLAVE_ID, self.my_address)
        except TAPError as e:
            raise SimpletermError_3P(SimpletermError_3P.TAP_ERROR, tap_error=e)
        if get_param_type == UINT32:
            if len(tap_packet.data) == 4:
                return serialize.deserialize_uint32(tap_packet.data)
            else:
                raise SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
        if get_param_type == UINT32_BE:
            if len(tap_packet.data) == 4:
                return serialize.deserialize_uint32(tap_packet.data, order = "reverse")
            else:
                raise SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
        if get_param_type == BUNDLE_3P:
            bdl = MeteringDataParamsBundle3P()
            try:
                bdl.deserialize_packet_bundle(tap_packet.data)                    
            except IndexError:
                raise SimpletermError_3P(SimpletermError_3P.GET_PARAM_UNEXPECTED_PAYLOAD_LENGTH, tap_packet=tap_packet)
            return bdl.get_packet_bundle()
        
