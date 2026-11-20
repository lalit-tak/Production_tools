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

tmp = input("Enter DCU No : ")
pub_topic = pub_topic + str(tmp)
meter_number = int(tmp)

print ("DCU No        : ", meter_number)
print ("Publish Topic : ", pub_topic)

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
        print ( [hex(f) for f in bytearray(msg.payload)] )
        ser.write(data)
        print ( "Send to node-shell >>" )
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
                print ( "Subscribe to : vdcuDataPushingTPWM" )
                mqttc.subscribe("vdcuDataPushingTPWM", 1)
                # mqttc.subscribe([("ipcl/vdcuDataPushingTPWM", 1),("ipcl/vdcuRCTPWM", 1),("vdcuDignosticStat", 1)])
            else:
                print ( "Subscribe to : gpgprsRCMD" )
                mqttc.subscribe("gpgprsRCMD", 1)

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
                    print ( [hex(f) for f in tmp_buf] )
                rc = mqttc.loop()
                if(len(tmp_buf) > 0):
                    mqttc.publish(pub_topic, tmp_buf)
                    print ( "Send to meter on mqtt:",pub_topic,">>" )
                # publish(mqttc)
            print ( "rc: ", rc )
        except Exception as err:
            print ( "Error" + str(err) )
            pass
        time.sleep(1)

run()

