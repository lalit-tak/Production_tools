import serial
import time
import tkinter as tk
from tkinter import messagebox

def open_serial_port(port_name, baudrate=9600):
    try:
        comport='com'+port_name
        ser = serial.Serial(comport, baudrate)
        return ser
    except serial.SerialException as e:
        print("Error opening serial port: {}".format(e))
        return None


def send_data(serial_obj, data1):
    """
    Sends data over the serial port.
    """
    try:
        send_data=bytearray()
        len_hex_bytes=len(data1)
        for i in range(0,len_hex_bytes):
            send_data.append((data1[i]))
        serial_obj.write(send_data)
        print ("the data sent is :",send_data)
    except serial.SerialException as e:
        print("Error sending data: {}".format(e))

def receive_data(serial_obj):
    """
    Receives data from the serial port.
    Returns the received data if successful, else returns None.
    """
    # received_data=[]
    # try:
    #     if serial_obj.inWaiting():
    #         received_data.append(serial_obj.read(exp_len))
    #     y = []
    #     for x in range(0,len(received_data)):
    #         y.append(received_data[x])
    #     print(y)
    #     print "the received data is :",y
    #     return y
    # except serial.SerialException as e:
    #     print("Error receiving data: {}".format(e))
    #     return None


    received_data = []
    try:
        while serial_obj.inWaiting():
            received_data.append(serial_obj.read())
        y = ''.join(received_data)  # Concatenate received data
        print("The received data is:", y)
        return y
    except serial.SerialException as e:
        print("Error receiving data: {}".format(e))
        return None

    # received_data = []
    # try:
    #     if serial_obj.inWaiting():
    #         received_data.append(serial_obj.read(exp_len))
    #         y = ''.join(received_data)  # Concatenate received data
    #         print("The received data is:", y)
        #     if "OK" in y:
        #         print "pass"
        #         return "Pass", y
        #     else:
        #         return "Fail", y
        # else:
    #         return y
    # except serial.SerialException as e:
    #     print("Error receiving data: {}".format(e))
    #     return "Fail", None
def send_and_receive(serial_obj, data_to_send, expected_response,waittime):
    """
    Sends data over the serial port and receives the response.
    Returns 'Pass' if response matches the expected_response, else returns 'Fail'.
    """
    send_data(serial_obj, data_to_send)
    time.sleep(waittime)
    response = receive_data(serial_obj)

    if expected_response:
        if expected_response in response:
            return 'Pass'
        else:
            return 'Fail'
    else:

        if 'OK' in response:
            return 'Pass'
        else:
            return 'Fail'


def send_and_receive1(serial_obj, data_to_send, expected_response, waittime=1):
    """
    Sends data over the serial port, waits for a response, and checks if the expected response is contained in it.
    Returns 'Pass' if expected response is found within the received data and if the CSQ value is within the specified range,
    else returns 'Fail'.
    """
    send_data(serial_obj, data_to_send)
    time.sleep(waittime)
    response = receive_data(serial_obj)

    if expected_response in response:
        csq_index = response.find("+CSQ:")  # Find the index of "+CSQ:"
        if csq_index != -1:
            csq_value = response[csq_index+6:csq_index+8] 
            print (csq_value) # Extract CSQ value
            try:
                csq_value = int(csq_value)
                if 20 < csq_value < 32:  # Check if CSQ value is within range
                    return 'Pass'
            except ValueError:
                pass  # Ignore if CSQ value cannot be converted to int

    return 'Fail'

def send_and_receive2(serial_obj, data_to_send, expected_response, waittime=1):
    """
    Sends data over the serial port, waits for a response, and checks if the expected response is contained in it.
    Returns 'Pass' if expected response is found within the received data and if the CSQ value is within the specified range,
    else returns 'Fail'.
    """
    send_data(serial_obj, data_to_send)
    time.sleep(waittime)
    response = receive_data(serial_obj)

    if expected_response in response:
        csq_index = response.find("+CGREG:")  # Find the index of "+CSQ:"
        if csq_index != -1:
            csq_value = response[csq_index+10:csq_index+11] 
            print (csq_value) # Extract CSQ value
            try:
                csq_value = int(csq_value)
                if csq_value == 1 :  # Check if CSQ value is within range
                    return 'Pass'
            except ValueError:
                pass  # Ignore if CSQ value cannot be converted to int

    return 'Fail'


def send_and_receive3(serial_obj, data_to_send, expected_response, waittime=1):
    """
    Sends data over the serial port, waits for a response, and checks if the expected response is contained in it.
    Returns 'Pass' if expected response is found within the received data and if the CSQ value is within the specified range,
    else returns 'Fail'.
    """
    send_data(serial_obj, data_to_send)
    time.sleep(waittime)
    response = receive_data(serial_obj)

    if expected_response in response:
        csq_index = response.find("+CGDCONT:")  # Find the index of "+CSQ:"
        if csq_index != -1:
            csq_value = response[csq_index+30:csq_index+31] 
            print (csq_value) # Extract CSQ value
            try:
                csq_value = int(csq_value)
                if csq_value == 2 :  # Check if CSQ value is within range
                    return 'Pass'
            except ValueError:
                pass  # Ignore if CSQ value cannot be converted to int

    return 'Fail'


def send_and_receive4(serial_obj, data_to_send, expected_response, waittime=1):
    """
    Sends data over the serial port, waits for a response, and checks if the expected response is contained in it.
    Returns 'Pass' if expected response is found within the received data and if the CSQ value is within the specified range,
    else returns 'Fail'.
    """
    send_data(serial_obj, data_to_send)
    time.sleep(waittime)
    response = receive_data(serial_obj)

    if (expected_response) and "FOTA START" in response:
        # Find the index of "+CSQ:"
        # Check if CSQ value is within range
        return 'Pass'
        # except ValueError:
    else:       # pass  # Ignore if CSQ value cannot be converted to int

        return 'Fail'


def send_and_receive5(serial_obj, data_to_send, expected_response, waittime=1):
    """
    Sends data over the serial port, waits for a response, and checks if the expected response is contained in it.
    Returns 'Pass' if expected response is found within the received data and if the CSQ value is within the specified range,
    else returns 'Fail'.
    """
    send_data(serial_obj, data_to_send)
    time.sleep(waittime)
    response = receive_data(serial_obj)

    if expected_response in response:
        csq_index = response.find("+IVSN:")  # Find the index of "+CSQ:"
        if csq_index != -1:
            csq_value = response[csq_index+29:csq_index+32] 
            print (csq_value) # Extract CSQ value
            try:
                csq_value = int(csq_value)
                if csq_value == 5 :  # Check if CSQ value is within range
                    return 'Pass'
            except ValueError:
                pass  # Ignore if CSQ value cannot be converted to int

    return 'Fail'

def main(port_name):
    # Open serial port
    ser = open_serial_port(port_name)
    if not ser:
        return

    # Send data and verify response

    retryCnt=5
    while (retryCnt):
        try:
            data_to_send1 = [0x41,0x54,0x0D]
            expected_response = 'OK'
            waittime=3
            result = send_and_receive(ser, data_to_send1, expected_response,waittime)
            print("Test Result: {}".format(result))
            if result=='Pass':
                retryCnt = 0
            else:
                retryCnt = retryCnt-1
        except:
            retryCnt = retryCnt-1


    retryCnt=5
    while (retryCnt):
        try:
            data_to_send2 = [0x41,0x54, 0x2B,0x43,0x50,0x49,0x4E,0x3F,0x0D]
            expected_response = '+CPIN: READY'
            waittime=3
            result = send_and_receive(ser, data_to_send2, expected_response,waittime)
            print("Test Result: {}".format(result))
            if result=='Pass':
                retryCnt = 0
            else:
                retryCnt = retryCnt-1
        except:
            retryCnt = retryCnt-1


    retryCnt=5
    while (retryCnt):
        try:
            data_to_send3 = [0x41,0x54 ,0x2B ,0x43 ,0x53 ,0x51,0x0D]
            expected_response = 'OK'
            waittime=3
            result = send_and_receive1(ser, data_to_send3, expected_response,waittime)
            print("Test Result: {}".format(result))
            if result=='Pass':
                retryCnt = 0
            else:
                retryCnt = retryCnt-1
        except:
            retryCnt = retryCnt-1

    retryCnt=5
    while (retryCnt):
        try:
            data_to_send4 = [0x41,0x54,0x2B ,0x43,0x47,0x52,0x45 ,0x47,0x3F,0x0D]
            expected_response = 'OK'
            waittime=3
            result = send_and_receive2(ser, data_to_send4, expected_response,waittime)
            print("Test Result: {}".format(result))
            if result=='Pass':
                retryCnt = 0
            else:
                retryCnt = retryCnt-1
        except:
            retryCnt = retryCnt-1

    retryCnt=5
    while (retryCnt):
        try:
            data_to_send5 = [0x41,0x54,0x2B,0x58,0x49 ,0x49,0x43,0x3F,0x0D]
            expected_response = 'OK'
            waittime=3
            result = send_and_receive(ser, data_to_send5, expected_response,waittime)
            print("Test Result: {}".format(result))
            if result=='Pass':
                retryCnt = 0
            else:
                retryCnt = retryCnt-1
        except:
            retryCnt = retryCnt-1


    retryCnt=5
    while (retryCnt):
        try:
            data_to_send6 = [0x41 ,0x54 ,0x2B ,0x58 ,0x49 ,0x49 ,0x43 ,0x3D ,0x31,0x0D]
            expected_response = 'OK'
            waittime=3
            result = send_and_receive(ser, data_to_send6, expected_response,waittime)
            print("Test Result: {}".format(result))
            if result=='Pass':
                retryCnt = 0
            else:
                retryCnt = retryCnt-1
        except:
            retryCnt = retryCnt-1

    retryCnt=5
    while (retryCnt):
        try:
            data_to_send7 = [0x41,0x54,0x2B ,0x43 ,0x47 ,0x44 ,0x43 ,0x4F ,0x4E,0x54 ,0x3F,0x0D]
            expected_response = 'OK'
            waittime=3
            result = send_and_receive3(ser, data_to_send7, expected_response,waittime)
            print("Test Result: {}".format(result))
            if result=='Pass':
                retryCnt = 0
            else:
                retryCnt = retryCnt-1
        except:
            retryCnt = retryCnt-1


    retryCnt=5
    while (retryCnt):
        try:
            data_to_send8 = [0x41,0x54,0x2B,0x46,0x54,0x50,0x47,0x45,0x54,0x46,0x3D,0x32,0x34,0x30,0x65,0x3A,0x39,0x38,0x30,0x3A,0x39,0x39,0x30,0x30,0x3A,0x3A,0x65,0x31,0x64,0x3A,0x66,0x38,0x61,0x39,0x2C,0x32,0x31,0x2C,0x30,0x2C,0x66,0x6F,0x74,0x61,0x5F,0x74,0x65,0x73,0x74,0x31,0x2F,0x30,0x30,0x34,0x5F,0x74,0x6F,0x5F,0x47,0x50,0x2D,0x30,0x30,0x35,0x2E,0x70,0x61,0x63,0x6B,0x2C,0x6E,0x65,0x6F,0x77,0x61,0x79,0x5F,0x66,0x74,0x70,0x5F,0x74,0x65,0x73,0x74,0x2C,0x6E,0x65,0x6F,0x77,0x61,0x79,0x61,0x64,0x6D,0x69,0x6E,0x0D]
            expected_response = 'OK'
            waittime=15
            result = send_and_receive4(ser, data_to_send8, expected_response,waittime)
            print("Test Result: {}".format(result))
            if result=='Pass':
                retryCnt = 0
            else:
                retryCnt = retryCnt-1
        except:
            retryCnt = retryCnt-1


    retryCnt=30
    while (retryCnt):
        try:
            data_to_send9 = [0x41,0x54,0x0D]
            expected_response = 'OK'
            waittime=3
            result = send_and_receive(ser, data_to_send9, expected_response,waittime)
            print("Test Result: {}".format(result))
            if result=='Pass':
                retryCnt = 0
            else:
                retryCnt = retryCnt-1
        except:
            retryCnt = retryCnt-1

    retryCnt=5
    while (retryCnt):
        try:
            data_to_send10 = [0x41 ,0x54,0x2B,0x49 ,0x56 ,0x53 ,0x4E ,0x0D]
            expected_response = 'OK'
            waittime=3
            result1 = send_and_receive5(ser, data_to_send10, expected_response,waittime)
            print("Test Result: {}".format(result1))
            if result1=='Pass':
                retryCnt = 0
            else:
                retryCnt = retryCnt-1
        except:
            retryCnt = retryCnt-1
    root = tk.Tk()
    root.withdraw()
    if result1 == 'Pass':
        messagebox.showinfo("Test Result", "Pass")
    else:
        messagebox.showinfo("Test Result", "Fail")


    ser.close()


if __name__ == "__main__":
    while True:
        port_name = str(input("Enter the serial port name (Ex:1,2,3 etc): "))
        main(port_name)
