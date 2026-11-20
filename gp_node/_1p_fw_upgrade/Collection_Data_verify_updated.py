# import os
# import urlparse
import paho.mqtt.client as paho
import datetime 
import binascii
import time
# import crc16
import struct

CMD_ID_NAMES = {
10000 : 'BOARD_RESET',
10001 : 'GATEWAY',
10002 : 'ROUTER',
10005 : 'RC_FACTORY_DEFAULT',
10009 : 'RELAY_AUTO_CONTROL',
10010 : 'RELAY_MANUAL_CONTROL',
10011 : 'TURN_RELAY_OFF',
10012 : 'TURN_RELAY_ON',
10040 : 'RELAY_STATE',
10043 : 'FACTORY_INIT_1',
10130 : 'FACTORY_INIT_2',
52404 : 'CLEAR_ENE_REG',
43124 : 'CALIB_UNLOCK',
51018 : 'GET_BILLING_INFO',
51019 : 'GET_BILLING_BY_INDEX',
52000 : 'IMAGE_TRANSFER_TAP_OLD',
51027 : 'INITIATE_FW_UPGRADE',
20000 : 'GET_NETWORK',
20002 : 'GET_ADDRESS',
20003 : 'GET_CHANNEL',
20008 : 'GET_TIME',
20016 : 'GET_LIVE_TAMPERS',
20020 : 'GET_POWER_LIMIT',
20037 : 'GET_NUM_BLOCK_LOAD_PROFILE',
20038 : 'GET_BLOCK_LOAD_PROFILE_PARAMS',
20039 : 'GET_LIVE_VERSION',
20040 : 'GET_EXT_VERSION',
20056 : 'GET_MD_AVG_PERIOD',
20060 : 'GET_BLOCK_LOAD_PROFILE_INTERVAL',
20111 : 'GET_BLOCK_LOAD_PROFILE_BY_INDEX',
20141 : 'GET_EVENT_RECORD_BY_INDEX',
20142 : 'GET_NUM_EVENT_RECORD',
20146 : 'GET_DAILY_LOAD_PROFILE_BY_INDEX',
20147 : 'GET_NUM_DAILY_LOAD_PROFILE',
20148 : 'GET_BILLING_TIMESTAMP',
20149 : 'GET_1P_METERING_DATA',
52057 : 'GET_1P_METERING_DATA2',
20150 : 'GET_SYNCSTREAM_BUNDLE',
20151 : 'GET_SYNCSTREAM_INTERVAL',
20152 : 'GET_METER_SERIAL_NO',
30000 : 'SET_ADDRESS',
30003 : 'SET_NETWORK',
30004 : 'SET_CHANNEL',
30008 : 'SET_POWER_LIMIT',
30016 : 'SET_BLOCK_LOAD_PROFILE_PARAMS',
30021 : 'SET_MD_AVG_PERIOD',
30030 : 'SET_BILLING_TIMESTAMP',
30031 : 'SET_SYNCSTREAM_INTERVAL',
30032 : 'SET_DCU_PUSH_INTERVAL',
51024 : 'GET_FETCH_BILLING_BY_INDEX',
43116 : 'GET_PREPAID_INFO',
43120 : 'ASSIGN',
43121 : 'DEASSIGN',
43122 : 'ENABLE_DG_TARIFF',
43123 : 'ENABLE_EG_TARIFF',
43114 : 'GET_GROUP1_INFO',
43115 : 'GET_GROUP2_INFO',
50004 : 'SET_METER_SERIAL_NO',
51026 : 'MEM_EEPROM_READ',
43118 : 'SET_TARIFF_PARAMS',
44112 : 'IP_SET_TIME',
52015 : 'SET_DG_POWER_LIMIT',
52016 : 'GET_DG_POWER_LIMIT',
52017 : 'SET_LOCK_DOWN_PERIOD',
52018 : 'SET_DEFAULT_LOCK_DOWN_PERIOD',
52019 : 'GET_LOCK_DOWN_PERIOD',
52020 : 'SET_POWER_LIMITER_STATUS',
52021 : 'GET_POWER_LIMITER_STATUS',
52022 : 'SET_POWER_LIMITER_ON_TIME',
52023 : 'SET_POWER_LIMITER_OFF_TIME',
52024 : 'GET_POWER_LIMITER_ON_TIME',
52025 : 'GET_POWER_LIMITER_OFF_TIME',
50006 : 'MEM_EEPROM_WRITE',
63636 : 'EEPROM_ENE_DEBUG',
52302 : 'SET_IPV6_ADDRESS',
52301 : 'GET_IPV6_ADDRESS',
52303 : 'RELAY_MODE',
11000 : 'RELAY_STATUS',
11020 : 'PH_CALIB_INIT_CALIB_RESET',
11021 : 'PH_CALIB_INIT',
11022 : 'NE_CALIB_INIT',
52026 : 'GET_POWER_LIMIT_PARAMS',
52027 : 'SET_POWER_LIMIT_PARAMS',
52028 : 'SET_OVERCURRENT_LIMIT',
52029 : 'GET_OVERCURRENT_LIMIT',
52030 : 'GET_POWER_EVENT_LOGS',
52031 : 'GET_REF_TIME',
52032 : 'FACTORY_INIT_3',
52033 : 'SET_REF_TIME',
52034 : 'SET_FD_TARIFF',
52035 : 'GET_HW_VERSION',
52036 : 'GET_HEALTH_STATUS',
52037 : 'GET_POWERDOWN_TIME',
52038 : 'SET_POWERDOWN_TIME',
52039 : 'CLEAR_EVENT_BY_RECORD',
52040 : 'GET_TOD_BILLING_BY_INDEX',
52041 : 'GET_BILLING_DATA_BY_INDEX',
52042 : 'SET_NM_CONTROL',
52043 : 'GET_NM_CONTROL',
52044 : 'SET_METERING_MODE',
52045 : 'GET_METERING_MODE',
52046 : 'GET_LCD_DIAGNOSE',
52047 : 'GET_BATT_LOG',
52048 : 'CLEAR_BATT_LOG',
52049 : 'BOOT_LOGS',
52050 : 'GET_SUN_SET_TIME',
52051 : 'GET_SUN_RISE_TIME',
52052 : 'SET_SUN_LOCATION',
52053 : 'GET_SUN_LOCATION',
52054 : 'SET_SUN_OFFSET',
52055 : 'GET_SUN_OFFSET',
52056 : 'INITIATE_UI_UPGRADE',
52058 : 'GET_ALARM_STATUS',
52059 : 'SET_ALARM_STATUS',
52060 : 'SET_CALIB_LED2',
52061 : 'GET_CALIB_LED2',
52062 : 'SET_EVENT_PTIME',
52063 : 'GET_EVENT_PTIME',
52064 : 'GET_CALIB_STATUS',
52065 : 'GET_NAMEPLATE',
52066 : 'SET_PREPAID_BILLTYPE',
52067 : 'GET_PREPAID_BILLTYPE',
52068 : 'SET_BATT_CALIB',
52069 : 'GET_NM_ENE_BY_INDEX',
52070 : 'GET_ENE_PARAMS_BY_INDEX',
52071 : 'GET_METERING_DATA_DEBUG',
52072 : 'GET_BATT_VOLTAGE_PARAMS',
52073 : 'GET_GP_BATT_EVENT_LOGS',
52074 : 'GET_NXP_SAMPLES_LOGS',
52075 : 'GET_NUM_NXP_SAMPLES',
52076 : 'CLEAR_NXP_SAMPLES',
52084 : 'GET_NUM_ASSIGN_DEASSGN_LOG',
52085 : 'GET_ASSIGN_DEASSIGN_LOG_BY_INDEX',
52086 : 'GET_BLOCK_LOAD_PROFILE_BY_ENE',
52089 : 'GET_NUM_BLOCK_LOAD_BY_DATETIME',
52090 : 'GET_NUM_DAILY_LOAD_BY_DATETIME',
52091 : 'SET_PUSH_ADDRESS',
52092 : 'GET_PUSH_ADDRESS',
52093 : 'SET_PUSH_SERVICE',
52094 : 'GET_PUSH_SERVICE',
52095 : 'SET_LAST_GASP_CONTROL',
52096 : 'GET_LAST_GASP_CONTROL',
52097 : 'DEBUG_GPRS_CONTROL',
52098 : 'GPRS_HEALTH_STATUS',
53000 : 'IMAGE_TRANSFER_TAP',
53001 : 'SET_GPRS_CREDENTIAL',
53002 : 'GET_GPRS_CREDENTIAL',
53003 : 'SET_GPRS_BROKER',
53004 : 'GET_GPRS_BROKER',
53005 : 'GET_GPRS_IP',
53006 : 'SET_GPRS_ACT_PROTOCOL',
53007 : 'GET_GPRS_ACT_PROTOCOL',
53009 : 'SET_BUNDLE_INTERVAL',
53010 : 'GET_BUNDLE_INTERVAL',
53011 : 'SET_TAP_CMDEXE_TOPIC',
53012 : 'SET_TAP_COLLECTION_TOPIC',
53013 : 'SET_TAP_PUSH_TOPIC',
53014 : 'GET_TAP_TOPICS',
53015 : 'SET_DLMS_PULL_TOPIC',
53016 : 'SET_DLMS_PUSH_TOPIC',
53017 : 'GET_DLMS_TOPICS',
53018 : 'GET_NUM_RECHARGE_LOGS',
53019 : 'GET_RECHARGE_LOG_BY_INDEX',
53020 : 'GET_NUM_GSM_LOGS',
53021 : 'GET_GSM_LOGS_BY_INDEX',
53022 : 'SET_GSM_SIM_TOGGLE',
53023 : 'SET_GSM_APN',
53024 : 'SET_NM_WAKEUPTIME',
53025 : 'GET_NM_WAKEUPTIME',
53026 : 'GET_SELF_DIAGNOSTIC',
53027 : 'GET_DUALSRC_TYPE',
53028 : 'SET_DUALSRC_TYPE',
53029 : 'SET_GPRS_RESET_CNT',
53030 : 'GET_GPRS_RESET_CNT',
53031 : 'GET_SYNCSTREAM_BUNDLE_ENTRIES',
53032 : 'GET_SYNCSTREAM_BUNDLE_BY_INDEX',
53033 : 'GET_SYNCSTREAM_BUNDLE_ENTRIES_TS',
53034 : 'GET_SYNCSTREAM_BUNDLE_NEXT_ENTRY_TS',
53035 : 'GET_PREPAID_INFO_DATA',
53036 : 'SET_CUSTOMER_ID',
53037 : 'GET_CUSTOMER_ID',
53038 : 'GET_NUM_RECHARGE_PARA_LOGS',
53039 : 'GET_RECHARGE_PARA_LOG_BY_INDEX',
53040 : 'SET_PAY_MODE',
53041 : 'GET_PAY_MODE',
53042 : 'SET_LAST_TOKEN_REC_AMT',
53043 : 'GET_LAST_TOKEN_REC_AMT',
53044 : 'SET_LAST_TOKEN_REC_TIME',
53045 : 'GET_LAST_TOKEN_REC_TIME',
53046 : 'SET_CUR_BAL_AMT',
53047 : 'GET_CUR_BAL_AMT',
53048 : 'SET_CUR_BAL_TIME',
53049 : 'GET_CUR_BAL_TIME',
53050 : 'SET_TOT_LAST_REC_AMT',
53051 : 'GET_TOT_LAST_REC_AMT',
53052 : 'SET_PREPAID_CONTROL_MODE',
53053 : 'GET_PREPAID_CONTROL_MODE',
53054 : 'SET_MANUFACTURING_YEAR',
53055 : 'GET_MANUFACTURING_YEAR',
53056 : 'SET_CURRENT_RATING',
53057 : 'GET_CURRENT_RATING',
53060 : 'GET_GAS_METERING_DATA',
53061 : 'GET_GAS_METERING_ACK',
53062 : 'SET_GAS_TARIFF',
53063 : 'GET_GAS_TARIFF',
53064 : 'SET_GAS_RECHARGE',
53065 : 'GET_GAS_NUM_RECHARGE',
53066 : 'GET_GAS_RECHARGE',
53067 : 'GET_NUM_GAS_DAILY_ENTRY',
53068 : 'GET_GAS_DAILY_ENTRY_BY_INDEX',
53069 : 'GET_NUM_GAS_EVENTS_ENTRY',
53070 : 'GET_GAS_EVENT_ENTRY_BY_INDEX',
53071 : 'GET_GAS_RELAY_STATUS',
53072 : 'SET_CONSUMED_GAS_VALUE',
53073 : 'SET_DAILY_DEBUG_TIME',
53081 : 'SET_AUTO_PREPAID_MODE',
53082 : 'GET_AUTO_PREPAID_MODE',
53083 : 'SET_BL_RANDOM_DELAY',
53084 : 'GET_BL_RANDOM_DELAY',
60606 : 'SET_PULSE',
33333 : 'SET_DEBUG_PRINT',
33334 : 'GET_DEBUG_PRINT',
33333 : 'PRINT_ENABLE',
59997 : 'SET_MQTT_TOPICS',
59995 : 'GET_MQTT_TOPICS',
60008 : 'DCU_BOOT_LOGS',
59918 : 'DCU_FACTORY_INIT_1',
59919 : 'DCU_RESET',
59913 : 'GET_DCU_TIME',
59912 : 'SET_DCU_TIME',
60010 : 'GET_DCU_GSM_LOG_BY_INDEX',
60011 : 'GET_DCU_NUM_GSM_LOGS',
60012 : 'CLEAR_GSM_LOG',
59931 : 'GET_DCU_LIVE_VERSION',
60013 : 'GET_DCU_NUM_EB_DG_SWITCH_LOGS',
60014 : 'GET_DCU_EB_DG_SWITCH_LOG_BY_INDEX',
60015 : 'CLEAR_EB_DG_SWITCH_LOG',
60016 : 'GET_DCU_NUM_TEST_MODULE_LOGS',
60017 : 'GET_DCU_TEST_MODULE_LOG_BY_INDEX',
60018 : 'CLEAR_TEST_MODULE_LOG',
59967 : 'GET_DG_EB_METERS',
60021 : 'SET_EB_METER_INDEXWISE',
60022 : 'SET_DG_METER_INDEXWISE',
60019 : 'SET_DCU_DEBUG_PRINT',
60020 : 'SET_DCU_DEBUG_PRINT_GPRS',
60023 : 'GET_DCU_ACTIVE_MODULE',
60000 : 'SWITCH_SIM',
60007 : 'DCU_RESET_GPRS',
50372 : 'METER_WP_DIAG_PACKET',
59912 : 'SET_TIME_VDCU',
59913 : 'GET_TIME_VDCU',
59914 : 'GET_NUM_CMDS_VDCU',
59915 : 'GET_CMD_BY_INDEX_VDCU',
59916 : 'GET_NUM_LOGS_VDCU',
59917 : 'GET_LOG_BY_INDEX_VDCU',
59918 : 'FACTORY_INIT_VDCU',
59919 : 'RESET_VDCU',
59920 : 'ADD_CMD_VDCU',
59921 : 'DEL_CMD_VDCU',
59922 : 'SET_BDC_CMD_INTERVAL_VDCU',
59923 : 'SET_ONLINE_DATA_INTERVAL_VDCU',
59924 : 'SET_OFFLINE_DATA_INTERVAL_VDCU',
59925 : 'GET_PARAMS_VDCU',
59926 : 'SET_RC_CONFIG_VDCU',
59927 : 'GET_RC_CONFIG_VDCU',
59928 : 'GET_TOTAL_PACKETS_SENT',
59929 : 'RESET_PACKETS_SENT',
59930 : 'GET_DCU_HEALTH',
59931 : 'GET_DCU_LIVE_VERSION',
59932 : 'GET_DCU_EXTERNAL_VERSION',
59933 : 'SET_SENDING_BDC_CMD_VDCU',
59934 : 'SET_SENDING_SEQ_CMD_VDCU',
59935 : 'SET_PUSH_ONLINE_DATA_VDCU',
59936 : 'SET_PUSH_OFFLINE_DATA_VDCU',
59937 : 'SET_SAVE_OFFLINE_DATA_VDCU',
59938 : 'ADD_METER_LOG_VDCU',
59939 : 'GET_NUM_METER_LOGS_VDCU',
59940 : 'GET_METER_LOG_BY_INDEX_VDCU',
59941 : 'ERASE_METER_LOGS_VDCU',
59942 : 'ERASE_COMMAND_LOGS_VDCU',
59943 : 'ERASE_OFFLINE_LOGS_VDCU',
59944 : 'MSP_INTERNET_STATUS_VDCU',
59945 : 'SET_SEQ_CMD_INTERVAL_VDCU',
59946 : 'ALLOW_RESET_INTERNET',
59947 : 'ALLOW_RESET_GATEWAY',
59948 : 'GET_LAST_POWER_OFF_TIME_VDCU',
59949 : 'SET_RESET_INTERNET_THRESHOLD_VDCU',
59950 : 'SET_RESET_GATEWAY_THRESHOLD_VDCU',
59951 : 'SET_UPDATE_HEALTH_THRESHOLD_VDCU',
59952 : 'SET_STORE_OFFLINE_VDCU',
59953 : 'WRITE_FLASH_MAGIC_NUM_VDCU',
59954 : 'FACTORY_RESET_LOGS_IGNORED_VDCU',
59955 : 'SET_CR_PARAMS_INTERVAL_VDCU',
59956 : 'SET_CT_RATIO_VDCU',
59962 : 'SET_EB_METER',
59963 : 'SET_DG_METER',
59964 : 'GET_EB_METER',
59965 : 'GET_DG_METER',
59966 : 'SET_DG_EB_METERS',
59967 : 'GET_DG_EB_METERS',
59968 : 'SET_DCU_ADDRESS',
59969 : 'GET_DCU_ADDRESS',
59970 : 'DUAL_SOURCE_ENABLE',
59971 : 'DUAL_SOURCE_DISABLE',
59972 : 'DCU_ON_DG',
59973 : 'DCU_ON_EB',
59974 : 'GET_FLASH_SIZE',
59975 : 'SET_EG_DG_SWITCHING_INTERVAL',
59976 : 'GET_EG_DG_SWITCHING_INTERVAL',
59977 : 'SET_BOTH_EG_DG_NOT_WORKING_INTERVAL',
59978 : 'GET_BOTH_EG_DG_NOT_WORKING_INTERVAL',
59979 : 'SEND_CMD_EVENT_TO_RF',
59980 : 'SET_INTERNET_DONGLE_STATUS',
59981 : 'ESP_LOOP_BACK',
59982 : 'GET_NUM_OF_POWER_ON_OFF_ENTRIES',
59983 : 'GET_LATEST_N_POWER_ON_OFF_ENTRIES',
59984 : 'GET_POWER_ON_OFF_ENTRIES_BW_INDEX',
59985 : 'GET_NUM_OF_FACTORY_RESET_ENTRIES',
59986 : 'GET_LATEST_N_FACTORY_RESET_ENTRIES',
59987 : 'GET_FACTORY_RESET_ENTRIES_BW_INDEX',
59988 : 'CLEAR_POWER_ON_OFF_LOGS',
59989 : 'CLEAR_FACTORY_RESET_LOGS',
59990 : 'GET_DEBUG_LOG_NUM_ENTRIES',
59991 : 'GET_DEBUG_LOG_BY_INDEX',
59992 : 'GET_HEALTH_LOGS_BY_INDEX',
59993 : 'GET_CR_PARAMS_LOG_BY_INDEX',
59994 : 'SET_DCU_NUM',
59995 : 'GET_MQTT_CONFIG_MEMORY',
59996 : 'RESET_DEFAULT_MQTT_CONFIG',
59997 : 'SET_NEO_MQTT_TOPICS',
59998 : 'SET_BATTERY_ON_OFF_SEC',
59999 : 'GET_PARAMS_VDCU_2',
60000 : 'SWITCH_SIM',
60001 : 'POWER_EVENT_PUSH_DATA',
60002 : 'SIM_SWITCH_PUSH_DATA',
60003 : 'GET_MAINS_BAT_LOG_BY_INDEX',
60004 : 'GET_NUM_MANIS_BAT_ENTRY',
60005 : 'GET_SIM_SWITCH_ENTRY_BY_INDEX',
60006 : 'GET_SIM_SWITCH_NUM_ENTRIES',
60007 : 'RESET_NEOBOARD',
60008 : 'BOOT_DEBUG_LOGS',
60009 : 'ERASE_OFFLINE_DATAINDEX_VDCU',
60019 : 'SET_DCU_DEBUG_PRINT',
60020 : 'SET_DCU_DEBUG_AT_COMMAND',
60031 : 'DCU_DAIG_EVENT',
}


Total_Rx_dcu_packet_count   = 0
Total_Rx_meter_packet_count = 0

dcu_listed = input("Enter DCU No : ")
dcu_listed = str(dcu_listed)

# Define event callbacks
def on_connect(client, mosq, obj, rc):
    print("rc: ", rc)


def on_message(mosq, obj, msg):

    global Total_Rx_dcu_packet_count
    global Total_Rx_meter_packet_count


    data = bytearray(msg.payload)
    data_len = len(data)
    try:
        dcu_number = (data[data_len-4]<<24)+(data[data_len-3]<<16)+(data[data_len-2]<<8)+(data[data_len-1])
    except:
        dcu_number = 0
        pass

    try:
        if (dcu_number == int(dcu_listed)):

            timestamp = datetime.datetime.now()
            print ()
            print ("-----------------------------------------New Data-----------------------------------------")
            Total_Rx_dcu_packet_count += 1
            dcu_responsed = str(data[1])+"."+ str(data[2])+"."+ str(data[3])+"."+ str(data[4])
            cmd_id = (data[6]<<8)+(data[7])

            print ("DCU_DATA << " + str(datetime.datetime.now().replace(microsecond=0)) )
            print ("dcu_number: ", dcu_number)
            print ("topic: ",msg.topic )
            print ("Total dcu packet count: ", Total_Rx_dcu_packet_count)
            print ("Total meter packet count: ", Total_Rx_meter_packet_count)
            print ("Packet Len", data_len)
            hex_values = ' '.join(format(byte, '02X') for byte in data)
            print(hex_values)

            dcu_list = []
            dcu_list.append(CMD_ID_NAMES[cmd_id])
            dcu_list.append(dcu_responsed)
            print ("Dcu list: ", dcu_list)
            del dcu_list[:]

        elif ("RECT" in data):

            # data = bytearray([0xAA,0x05,0x00,0xE6,0xCD,0x01,0x27,0x1B,0xCA,0x13,0x04,0x06,0xEB,0x03,0x00,0x00,0x00,0x00,0xB0,0x05,0x00,0x00,0xC3,0x69,0x52,0x45,0x43,0x54,0xAA,0xFF,0xFF,0xFF,0xFF,0xC4,0xC4,0xC4,0xC4,0x04,0x04,0x53,0x57,0x4D,0x00,0x00,0x3B,0x00,0x00,0x00,0x6A,0xE4,0x79,0x00,0x12,0x00,0x00,0x00,0x00,0xFD,0xFF,0x02,0xC4,0x20,0x91,0x8D,0x0C,0x00,0x00,0x3A,0x0E,0x04,0xF3,0x00,0x0E,0x00,0x10,0x00,0x91,0x00,0x13,0x00,0x80,0x00,0x1A,0x00,0x00,0x00,0x00,0x06,0x9C,0x2B,0x1C,0xA2,0xE4,0x79,0x05,0xE5,0x2F,0x00,0x00,0x00,0x00,0x18,0x20,0x18,0x35,0x4B,0x1D,0x4B,0x28,0x10,0x28,0x1E,0x00,0x00,0x00,0x00,0x00,0x00,0x02,0x00,0x00,0x00,0x00,0x80,0x3E,0x00,0x00,0xC3,0x69,0x52,0x45,0x43,0x54])
            dcu_number = (data[data_len-8]<<24)+(data[data_len-7]<<16)+(data[data_len-6]<<8)+(data[data_len-5])
            if (dcu_number == int(dcu_listed)):

                timestamp = datetime.datetime.now()
                meter_list = []
                index = 0
                no_of_meter_responds_in_buf = 0
                while (index < data_len):
                    if (data[index] == 0xAA):
                        meter_responsed = str(data[index+1])+"."+ str(data[index+2])+"."+ str(data[index+3])+"."+ str(data[index+4])
                        cmd_id = (data[index+6]<<8)+(data[index+7])
                        packet_list = []
                        packet_list.append(CMD_ID_NAMES[cmd_id])
                        packet_list.append(meter_responsed)
                        meter_list.append(packet_list)

                        no_of_meter_responds_in_buf += 1
                        index += data[11]+10
                    else:
                        index += 1
                Total_Rx_meter_packet_count += no_of_meter_responds_in_buf
                print ("-----------------------------------------New Data-----------------------------------------")
                print ()
                print ( "BUFFER RECIEVED << " + str(datetime.datetime.now().replace(microsecond=0)) )
                print ( "dcu_number: ", dcu_number)
                print ( "topic: ",msg.topic )
                print ("Total dcu packet count: ", Total_Rx_dcu_packet_count)
                print ("Total meter packet count: ", Total_Rx_meter_packet_count)
                print ("No of meter responds in this buffer ", no_of_meter_responds_in_buf)
                print ("Packet Len", data_len)
                hex_values = ' '.join(format(byte, '02X') for byte in data)
                print(hex_values)
                print ("meter list: ", meter_list)
                del meter_list[:]
    except Exception as err:
            print ("Error: ", err)
    


    # print "------------------------------------------Data End--------------------------------------------------------------------------------------------------------------------------"


def on_subscribe(mosq, obj, mid, granted_qos):
    print ("Subscribed: ", mid, " ", granted_qos)


def run():
    print ("starting subscriber")
    while True:
        try:
            mqttc = paho.Client()
            # Assign event callbacks
            mqttc.on_message = on_message
            mqttc.on_connect = on_connect
            mqttc.on_subscribe = on_subscribe
            # Connect
            mqttc.username_pw_set('gpbroker', 'grampower4321@')
            mqttc.connect('broker.grampower.com', '1883')
            # Start subscribe, with QoS level 0
            print ( "Subscribe to : rec/vdcuCollectionTPWM, ipcl/vdcuDataPushingTPWM, ipcl/vdcuRCTPWM, vdcuDiagnosticStat, vdcuDcuDiagStat" )
            mqttc.subscribe([("rec/vdcuCollectionTPWM", 1), ("ipcl/vdcuDataPushingTPWM",1), ("ipcl/vdcuRCTPWM",1), ("vdcuDiagnosticStat",1), ("vdcuDcuDiagStat",1)])
            #mqttc.subscribe(("DebugData", 1))
            # Continue the network loop, exit when an error occurs
            rc = 0
            while rc == 0:
                rc = mqttc.loop()
            print ("rc: ", rc)
        except Exception as err:
            print (str(err))
            pass
        time.sleep(0.3)

run()

