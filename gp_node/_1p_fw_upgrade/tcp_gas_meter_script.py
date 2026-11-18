import contextlib
import socket
import serial
import time
import crcmod

crc16 = crcmod.predefined.mkPredefinedCrcFun('xmodem')
import datetime
import sys
import gp_node.utils.serialize as serialize

print ("Opened serial COM2 for listening from node-shell")
ser=serial.Serial("COM2", 9600, timeout = 1)

host = "::"
port = 4059

ACK_DONE = 1100
ACK_WITH_TARIFF_PLUS_RECHARGE = 1101
ACK_WAIT_FOR_MIN = 1102

RET_ACT_DIC = {
    1100: "ACK_DONE",
    1101: "ACK_WITH_TARIFF_PLUS_RECHARGE",
    1102: "ACK_WAIT_FOR_MIN"
}


TARIFF_PACKET = {
    "tariff_ackid"          : 0,
    "tariff_activationTS"   : "2024-08-30 00:00:00",
    "tariff_gasPrice"       : 60,    #Paise
    "tariff_topUpLimit"     : 1000,    #Rs
    "tariff_creditLimit"    : 200,     #Rs
    "tariff_emergencyLimit" : -100,    #Rs
    "recharge_token1"       : 11,
    "recharge1"             : 1500,    #Paise
    "recharge_token2"       : 12,
    "recharge2"             : 2500,    #Paise
    "recharge_token3"       : 0,
    "recharge3"             : 0,       #Paise
    "recharge_token4"       : 0,
    "recharge4"             : 0,       #Paise
    "recharge_token5"       : 0,
    "recharge5"             : 0        #Paise
}


@contextlib.contextmanager
def server(host, port):
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, 0)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        print ("binding...")
        s.listen(10)
        yield s
    finally:
        s.close()

def run():


    while True:
        with server(host, port) as s:
            try:
                print ("waiting to connect..")
                conn, addr = s.accept()
                print ("connected to : ", conn, addr)
            except KeyboardInterrupt:
                pass

            while True:

                try:
                    if ser.inWaiting() > 0:
                        tmp_buf=bytearray()
                        while ser.inWaiting() > 0:
                            tmp_buf.extend(ser.read())
                            if ser.inWaiting() == 0:
                                time.sleep(0.1)

                        currentTS = datetime.datetime.now()
                        print(currentTS.strftime("%c"))
                        print ("TCP_OUT>>" , "Len : ", len(tmp_buf), [hex(f) for f in tmp_buf])
                        conn.send(tmp_buf)
                except Exception as err:
                    print ("Error", err)
                    s.close()
                    break
                
                try:
                    conn.settimeout(1.0)
                    msg = conn.recv(256)
                    data=bytearray(msg)
                    print ("TCP_IN<<" , "Len : ", len(data), [hex(f) for f in data])

                    if len(data) == 0:
                        s.close()
                        break

                    # Tap packet construction......................................
                    pckt = bytearray()
                    start_byte = 0
                    while(True):
                        if(data[start_byte] == 0xAA):
                            break
                        else:
                            start_byte += 1

                    for b in range(start_byte, start_byte+11):
                        pckt.append(data[b])
                    pckt_len = data[start_byte+11]

                    meter_serial_pos = start_byte+12+pckt_len+2
                    meter_serial_no = (data[meter_serial_pos]<<24)+(data[meter_serial_pos+1]<<16)+\
                                      (data[meter_serial_pos+2]<<8)+(data[meter_serial_pos+3])
                    print ("meter_serial_no:", meter_serial_no)

                    if (pckt_len >= 4):
                        pckt_len = pckt_len - 4
                    pckt.append(pckt_len)
                    for b in range(start_byte+12,start_byte+12+pckt_len):
                        pckt.append(data[b])

                    #CRC is calculated for even bytes to be in sync with the embedded part
                    #If data bytes is odd.'0' is appended and then CRC is calculated
                    if (len(pckt[1:]) % 2) != 0:
                        pckt.append(0)
                        crc = crc16(str(pckt[1:]))
                        pckt = pckt[:-1]
                    else:
                        crc = crc16(str(pckt[1:]))
                    crc_l = crc/256
                    crc_h = crc%256
                    pckt.append(crc_l)
                    pckt.append(crc_h)

                    # tap packet parsing for gas meter
                    pckt_source_addr = str(pckt[1])+"."+str(pckt[2])+"."+str(pckt[3])+"."+str(pckt[4])
                    pckt_dest_addr   = str(pckt[5])+"."+str(pckt[6])+"."+str(pckt[7])+"."+str(pckt[8])
                    if pckt_dest_addr == "1.207.68.201":
                        pckt_data = bytearray()
                        pckt_data = pckt[12:-2]

                        print ("meter_addr:", pckt_source_addr)
                        print ("push_addr :", pckt_dest_addr)
                        print ("Gas bundle recv ----------------------")
                        print (Gas_bundle_parser(pckt_data))
                        time.sleep(1)

                        ack_payload = Gas_bundle_ack(ACK_WITH_TARIFF_PLUS_RECHARGE)
                        ack_ret = serialize_tap_packet(ack_payload)
                        print ("Return packet >>:", [hex(b) for b in ack_ret])
                        conn.send(ack_ret)
                        time.sleep(1)

                    else:
                        print ( "\nSend to node-shell >>" ),
                        ser.write(pckt)
                        print ( [hex(f) for f in bytearray(pckt)] )
                        time.sleep(1)

                        # ack_payload = Gas_bundle_ack(ACK_DONE)
                        # ack_ret = serialize_tap_packet(ack_payload)
                        # print "Return packet >>:", [hex(b) for b in ack_ret]
                        # conn.send(ack_ret)
                        # time.sleep(1)
                except Exception as err:
                    print ("Error", err, '-',)
                    pass

def serialize_tap_packet(payload):
    pckt = bytearray()
    pckt.append(0xAA)
    pckt.append(0x01)
    pckt.append(0x4E)
    pckt.append(0x47)
    pckt.append(0xC9)
    pckt.append(0xFF)
    pckt.append(0xFF)
    pckt.append(0xFF)
    pckt.append(0xFF)
    pckt.append(0x04)
    pckt.append(0x04)

    data_len = len(payload)
    print ("data_len", data_len)
    pckt.append(data_len)

    #The 2 byte CRC forms the stop byte
    for i in range(0, data_len):
        pckt.append(payload[i])
    
    #CRC is calculated for even bytes to be in sync with the embedded part
    #If data bytes is odd.'0' is appended and then CRC is calculated
    if (len(pckt[1:]) % 2) != 0:
        pckt.append(0)
        crc = crc16(str(pckt[1:]))
        pckt = pckt[:-1]
    else:
        crc = crc16(str(pckt[1:]))
    crc_l = crc/256
    crc_h = crc%256
    pckt.append(crc_l)
    pckt.append(crc_h)

    return pckt

def Gas_bundle_ack(ack_id):
    payload = bytearray()

    TARIFF_PACKET["tariff_ackid"] = ack_id
    print ("ACK_TYPE :", RET_ACT_DIC[ack_id])

    # Change the Activation timestamp
    # -------------------------------------------------
    cal_time = datetime.datetime.strptime(TARIFF_PACKET["tariff_activationTS"], "%Y-%m-%d %H:%M:%S")
    unix_time_zero = datetime.datetime(1970, 1, 1)
    seconds_since_epoch = int((cal_time - unix_time_zero).total_seconds())
    seconds_since_epoch = seconds_since_epoch-(seconds_since_epoch%86400)
    seconds_since_epoch = seconds_since_epoch/86400
    tariff_activationTS = seconds_since_epoch
    print ("tariff_activationTS", seconds_since_epoch)

    # Serialize packet
    # ----------------------------------------------
    GET_GAS_METERING_ACK  = 53061
    payload.extend(serialize.serialize_uint16(GET_GAS_METERING_ACK))
    payload.extend(serialize.serialize_uint16(TARIFF_PACKET["tariff_ackid"]))
    payload.extend(serialize.serialize_uint16(tariff_activationTS, "reverse"))
    payload.extend(serialize.serialize_uint16(TARIFF_PACKET["tariff_gasPrice"], "reverse"))
    payload.extend(serialize.serialize_uint16(TARIFF_PACKET["tariff_topUpLimit"], "reverse"))
    payload.extend(serialize.serialize_int16(TARIFF_PACKET["tariff_creditLimit"], "reverse"))
    payload.extend(serialize.serialize_int16(TARIFF_PACKET["tariff_emergencyLimit"], "reverse"))
    payload.extend(serialize.serialize_uint32(TARIFF_PACKET["recharge_token1"], "reverse"))
    payload.extend(serialize.serialize_int32(TARIFF_PACKET["recharge1"], "reverse"))
    payload.extend(serialize.serialize_uint32(TARIFF_PACKET["recharge_token2"], "reverse"))
    payload.extend(serialize.serialize_int32(TARIFF_PACKET["recharge2"], "reverse"))
    payload.extend(serialize.serialize_uint32(TARIFF_PACKET["recharge_token3"], "reverse"))
    payload.extend(serialize.serialize_int32(TARIFF_PACKET["recharge3"], "reverse"))
    payload.extend(serialize.serialize_uint32(TARIFF_PACKET["recharge_token4"], "reverse"))
    payload.extend(serialize.serialize_int32(TARIFF_PACKET["recharge4"], "reverse"))
    payload.extend(serialize.serialize_uint32(TARIFF_PACKET["recharge_token5"], "reverse"))
    payload.extend(serialize.serialize_int32(TARIFF_PACKET["recharge5"], "reverse"))

    return payload


def Gas_bundle_parser(payload):


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

    bundle_version            = serialize.deserialize_uint8(buf[0:1])
    meter_serial_number       = serialize.deserialize_uint32(buf[1:5])
    timearr = serialize.deserialize_uint32(buf[5:9])
    meter_timestamp           = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
    current_consumed_gas      = serialize.deserialize_uint24(buf[9:12])/100.0

    timearr = serialize.deserialize_uint16(buf[12:14])*86400
    daily_time1               = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
    daily_consumed_gas1       = serialize.deserialize_uint24(buf[14:17])/100.0
    daily_balance_amount1     = serialize.deserialize_int16(buf[17:19])/1.0

    timearr = serialize.deserialize_uint16(buf[19:21])*86400
    daily_time2               = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
    daily_consumed_gas2       = serialize.deserialize_uint24(buf[21:24])/100.0
    daily_balance_amount2     = serialize.deserialize_int16(buf[24:26])/1.0

    timearr = serialize.deserialize_uint16(buf[26:28])*86400
    daily_time3               = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
    daily_consumed_gas3       = serialize.deserialize_uint24(buf[28:31])/100.0
    daily_balance_amount3     = serialize.deserialize_int16(buf[31:33])/1.0

    timearr = serialize.deserialize_uint16(buf[33:35])*86400
    daily_time4               = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
    daily_consumed_gas4       = serialize.deserialize_uint24(buf[35:38])/100.0
    daily_balance_amount4     = serialize.deserialize_int16(buf[38:40])/1.0

    timearr = serialize.deserialize_uint16(buf[40:42])*86400
    daily_time5               = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
    daily_consumed_gas5       = serialize.deserialize_uint24(buf[42:45])/100.0
    daily_balance_amount5     = serialize.deserialize_int16(buf[45:47])/1.0

    timearr = serialize.deserialize_uint16(buf[47:49])*86400
    daily_time6               = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
    daily_consumed_gas6       = serialize.deserialize_uint24(buf[49:52])/100.0
    daily_balance_amount6     = serialize.deserialize_int16(buf[52:54])/1.0

    timearr = serialize.deserialize_uint16(buf[54:56])*86400
    daily_time7               = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
    daily_consumed_gas7       = serialize.deserialize_uint24(buf[56:59])/100.0
    daily_balance_amount7     = serialize.deserialize_int16(buf[59:61])/1.0

    temp = serialize.deserialize_uint8(buf[61:62])
    if (temp == 0x55):
        prepaid_status        = "PREPAID"
    else:
        prepaid_status        = "POSTPAID"
    prepaid_balance_amount    = serialize.deserialize_int32(buf[62:66])/100.0
    prepaid_net_recharge      = serialize.deserialize_uint32(buf[66:70])/100.0

    timearr = serialize.deserialize_uint16(buf[70:72])*86400
    last_tariff_TS            = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=timearr)
    tariff_gas_price          = serialize.deserialize_uint16(buf[72:74])/100.0

    temp = serialize.deserialize_uint8(buf[74:75])
    if (temp <= 5):
        prepaid_event_sts     = prepaidEvent[temp]

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

    liveTamper                = TamperEvent
    Battary_level             = serialize.deserialize_uint8(buf[76:77])/1.0

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
            .format(    bundle_version,
                        meter_serial_number,
                        meter_timestamp,
                        current_consumed_gas,
                        daily_time1,
                        daily_balance_amount1,
                        daily_consumed_gas1,
                        daily_time2,
                        daily_balance_amount2,
                        daily_consumed_gas2,
                        daily_time3,
                        daily_balance_amount3,
                        daily_consumed_gas3,
                        daily_time4,
                        daily_balance_amount4,
                        daily_consumed_gas4,
                        daily_time5,
                        daily_balance_amount5,
                        daily_consumed_gas5,
                        daily_time6,
                        daily_balance_amount6,
                        daily_consumed_gas6,
                        daily_time7,
                        daily_balance_amount7,
                        daily_consumed_gas7,
                        prepaid_status,
                        prepaid_balance_amount,
                        prepaid_net_recharge,
                        last_tariff_TS,
                        tariff_gas_price,
                        prepaid_event_sts,
                        liveTamper,
                        Battary_level)

if __name__ == "__main__":
    run()