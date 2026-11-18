import paho.mqtt.client as paho
import datetime 
import binascii
import time
import crcmod

crc16 = crcmod.predefined.mkPredefinedCrcFun('xmodem')
import struct
import serial

tmp = input("Enter com port No: ")
comx = 'COM'+str(tmp)
print ("Entered com port : ", comx)

try:
    ser=serial.Serial(comx, 9600, timeout=1)
    print ("Serial port :", comx, "Opened !!!")
except Exception as err:
    print ("Error" + str(err))
    time.sleep(3)
    exit()

tmp = input("Enter Meter S.No : ")
pub_topic = 'gp' + str(tmp)
sub_topic = 'gpgprsDLMS'+ str(tmp)

start_flag = 0

# Define event callbacks
def on_connect(client, mosq, obj, rc):
    print ("rc: ", rc)


def on_message(mosq, obj, msg):
    data = bytearray(msg.payload)
    global start_flag
    if start_flag is not 0:
        print ("\n")
        print ("METER << " + str(datetime.datetime.now().replace(microsecond=0)) ),
        print ([hex(f) for f in data] )
        print ("Send to DLMS TOOL >>" )
        try:
            ser.write(data)
        except Exception as err:
            print ("Error" + str(err))
            time.sleep(3)
    print ("recieve count:",start_flag)
    start_flag += 1

def on_subscribe(mosq, obj, mid, granted_qos):
    print ( "Subscribed: ", mid, " ", granted_qos )

def run():
    print ( "Create virtual COM port with Opened com port ..." )
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
            mqttc.subscribe(sub_topic, 1)
            print ("Subscribe to :", sub_topic)
            print ("Publish Topic : ", pub_topic)
            print ("waiting....")
            # Continue the network loop, exit when an error occurs
            rc = 0

            while rc == 0:
                tmp_buf=bytearray()
                if ser.inWaiting() > 0:
                    while ser.inWaiting() > 0:
                        tmp_buf.extend(ser.read())
                    print ("\n")
                    print ( "DLMS TOOL << " + str(datetime.datetime.now().replace(microsecond=0)) ),
                    print ( [hex(f) for f in tmp_buf] )
                rc = mqttc.loop()
                if(len(tmp_buf) > 0):
                    mqttc.publish(pub_topic, tmp_buf)
                    print ( "Send to METER :",pub_topic,">>" )
                # publish(mqttc)
            print ( "rc: ", rc )
        except Exception as err:
            print ( "Error" + str(err) )
            pass
        time.sleep(1)

run()

