import paho.mqtt.client as paho
import datetime 
import binascii
import time
import crcmod

crc16 = crcmod.predefined.mkPredefinedCrcFun('xmodem')
import struct
import serial

# tmp = input("Enter com port: ")
# comx = str(tmp)
# print ( "Entered com port : ", comx )
comx = 'COM2'
pub_topic = "gp"

meter_list=[]
tmp = input("Enter Meter S.No : ")
pub_topic = pub_topic + str(tmp)
sub_topic = "gpgprsDLMS"+str(tmp)
meter_number = int(tmp)

tmp = input("Enter Meter address : ")
src_addr = [255,255,255,255]
try:
    src_addrx = tmp.split(".")
    src_addr[0] = int(src_addrx[0])
    src_addr[1] = int(src_addrx[1])
    src_addr[2] = int(src_addrx[2])
    src_addr[3] = int(src_addrx[3])
    src_flag = True
    # print [int(b) for b in src_addr]
except Exception as err:
    print ("Default address: 255.255.255.255")
    src_flag = False

print ("Meter Sr.No   : ", meter_number)
print ("Publish Topic : ", pub_topic)
print ("Meter Address : ", src_addr)
# print ("Meter No : ", meter_number, type(meter_number))
# print ("pub_topic: ", pub_topic, type(pub_topic))

try:
    ser=serial.Serial(comx,9600)
    print ("Opened Serial port :", comx)
except Exception as err:
    print ( "Error" + str(err) )
    exit()

# Define event callbacks
def on_connect(client, mosq, obj, rc):
    print ("rc: ", rc )


def on_message(mosq, obj, msg):
    # if(msg.topic == "gp211975"):
    #     timestamp = datetime.datetime.now()
    #     print "\n"
    #     print ( "topic: ",msg.topic ),
    #     print ( "Rx on DCU << " + str(datetime.datetime.now().replace(microsecond=0)) ),
    #     print ( [hex(f) for f in bytearray(msg.payload)] )
    #     return
    data = bytearray(msg.payload)
    data_len = len(data)
    try:
        dcu_number = (data[data_len-4]<<24)+(data[data_len-3]<<16)+(data[data_len-2]<<8)+(data[data_len-1])
    except:
        dcu_number = 0
        pass

    if(dcu_number == int(meter_number)):
        timestamp = datetime.datetime.now()
        print ("\n")
        print ( "dcu_number: ", dcu_number),
        print ( "topic: ",msg.topic ),
        print ( "Tx from DCU << " + str(datetime.datetime.now().replace(microsecond=0)) ),
        hex_values = ' '.join(format(byte, '02X') for byte in bytearray(msg.payload))
        print(hex_values)
        try:
            pckt = bytearray()
            start_byte = 0
            byteF = True
            while( (True == byteF) and (start_byte < data_len) ):
                if(data[start_byte] == 0xAA):
                    byteF = False
                    # print "start_byte found"
                else:
                    start_byte += 1
                    # print "."

            if data_len > (start_byte + 12):
                meter_data_found = True
                meter_responsed = str(data[start_byte+1])+"."+\
                                  str(data[start_byte+2])+"."+\
                                  str(data[start_byte+3])+"."+\
                                  str(data[start_byte+4])

                # if (meter_responsed not in meter_list):
                #     meter_list.append(meter_responsed)

                # print "meter_data_found"
                if src_flag == True:
                    for b in range(4):
                        if src_addr[b] != data[start_byte+b+1]:
                            meter_data_found = False
                            # print "meter_data_found_false"

                if meter_data_found == True:
                    for b in range(start_byte,start_byte+11):
                        pckt.append(data[b])
                    pckt_len = data[start_byte+11]
                    # response_ok = True
                    if (pckt_len >= 4):
                        pckt_len = pckt_len - 4
                        # response_ok = False
                    pckt.append(pckt_len)
                    # if response_ok == False:
                    #     for b in range(start_byte+12,start_byte+12+pckt_len):
                    #         pckt.append(data[b])
                    # else:
                    for b in range(start_byte+12,start_byte+12+pckt_len):
                        pckt.append(data[b])
                        # response_o = "o"
                        # pckt.append(response_o)
                        # response_o = "k"
                        # pckt.append(response_o)
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
                    print ( "\nSend to node-shell >>" ),
                    ser.write(pckt)
                    # print ( [hex(f) for f in bytearray(pckt)] )
                    print ("Meter Address:", meter_responsed)
        except Exception as err:
            print ("Error: ", err)
    elif (dcu_number == 0x52454354): #RECT
        dcu_number = (data[data_len-8]<<24)+(data[data_len-7]<<16)+(data[data_len-6]<<8)+(data[data_len-5])
        if (dcu_number == int(meter_number)):
            timestamp = datetime.datetime.now()
            print ("\n")
            print ( "dcu_number: ", dcu_number),
            print ( "topic: ",msg.topic ),
            print ( "Tx from DCU << " + str(datetime.datetime.now().replace(microsecond=0)) ),
            hex_values = ' '.join(format(byte, '02X') for byte in bytearray(msg.payload))
            print(hex_values)
    else:
        pass
        # print ( "dcu_number: ", dcu_number),
        # print ( "topic: ",msg.topic )

def on_subscribe(mosq, obj, mid, granted_qos):
    print ( "Subscribed: ", mid, " ", granted_qos )

def run():
    print ( "Initialization of Script to connect node-shell(COM1) to meter on mqtt ..." )
    # ser=serial.Serial('COM2',9600, timeout = 3)
    while True:
        try:
            mqttc = paho.Client()
            # Assign event callbacks
            mqttc.on_message = on_message
            mqttc.on_connect = on_connect
            mqttc.on_subscribe = on_subscribe
            # Connect
            print ( "connect to username: gpbroker and pass: grampower4321@" )
            mqttc.username_pw_set('gpbroker', 'grampower4321@')
            print ( "connecting...." )
            mqttc.connect('broker.grampower.com', 1883)
            # Start subscribe, with QoS level 0

            if (meter_number > 9999) and (meter_number < 100000):
                print ( "Subscribe to : rec/vdcuCollectionTPWM, ipcl/vdcuDataPushingTPWM, ipcl/vdcuRCTPWM, vdcuDiagnosticStat, vdcuDcuDiagStat" )
                mqttc.subscribe([("rec/vdcuCollectionTPWM", 1), ("ipcl/vdcuDataPushingTPWM",1), ("ipcl/vdcuRCTPWM",1), ("vdcuDiagnosticStat",1), ("vdcuDcuDiagStat",1)])
                # mqttc.subscribe([("alokCollectionTest", 1), ("alokResponseTest",1), ("alokPushingTest",1), ("alokWpDiagTest",1), ("alokDcuDiagTest",1)])
            else:
                print ( "Subscribe to : gpgprsRCMD,",sub_topic )
                mqttc.subscribe([("gpgprsRCMD", 1), (sub_topic, 1)])

            # mqttc.subscribe([("vdcuRCTPWM", 1),("vdcuDataPushingTPWM", 1),("gp211975", 1),("vdcuCollectionTPWM", 1)])
            # Data Collection Topic:vdcuCollectionTPWM
            # Data Pushing Topic:vdcuDataPushingTPWM
            # Remote Command Topic:vdcuRCTPWM
            print ( "waiting...." )
            # Continue the network loop, exit when an error occurs
            rc = 0
            while rc == 0:
                tmp_buf=bytearray()
                if ser.inWaiting() > 0:
                    while ser.inWaiting() > 0:
                        tmp_buf.extend(ser.read())
                    print ( "\nRx from node-shell << " + str(datetime.datetime.now().replace(microsecond=0)) ),
                    # print ( [hex(f) for f in tmp_buf] )
                    hex_values = ' '.join(format(byte, '02X') for byte in tmp_buf)
                    print(hex_values)

                rc = mqttc.loop()
                if(len(tmp_buf) > 0):
                    mqttc.publish(pub_topic, tmp_buf)
                    del meter_list[:]
                    print ( "Send to meter on mqtt:",pub_topic,">>" )
                # publish(mqttc)
            print ( "rc: ", rc )
        except Exception as err:
            print ( "Error" + str(err) )
            pass
        time.sleep(1)

run()

