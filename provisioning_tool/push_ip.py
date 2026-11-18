from communication import Communication


def set_push_interval(serial_port, com):
    print("\nStarting Set Push Control Mode")
    # logging.info(f"Sending Command To Set Push Control Mode")
    retryCnt = 3
    while (retryCnt):
        try:
            if not com.open():
                return None

            # Frame to send the command to Get Push Control Mode
            body = bytes([
                0xAA, 0x01, 0xD3, 0x1B, 0xC9,
                0xFF, 0xFF, 0xFF, 0xFF,
                0x04, 0x04, 0x06, 0xD3,
                0x1B, 0x00, 0x00, 0x00, 0x3C, 0xE6, 0xCA
            ])

            # Send the data
            com.send_data(body, expected_payload_len=2)
            print("\nCommand sent for Set Push Control Mode")

            # Wait for response
            response = com.read_response(timeout=5)
            print("\nResponse received for Set Push Control Mode: ", response)
            pattern = bytes.fromhex("e8 03")
            print("\nRead response from meter to check Set Push Control Mode")
            if pattern in response:
                print("Default Push Control Mode is Successfully done")
                return True
            else:
                print(f"\nError in Set Push Control Mode, Response{response}")
                # logging.info(f"Error in Set Push Control Mode, Response{response}")
                return False
        except Exception as e:
            print(f"\nPort {serial_port}, Error in Set Push Control Mode: {e}")
            # logging.error(f"Port {serial_port}, Error in Set Push Control Mode: {e}")
    return False

def get_push_interval(serial_port, com):
    print("\nStarting Get Push Control Mode")
    # logging.info(f"Sending Command To Get Push Control Mode")
    retryCnt = 3
    while (retryCnt):
        try:
            if not com.open():
                return None

            # Frame to send the command to Get Push Control Mode
            body = bytes([
                0xAA, 0x01, 0xD3, 0x1A, 0xC9,
                0xFF, 0xFF, 0xFF, 0xFF,
                0x04, 0x04, 0x02, 0xD3, 0x1A, 0xB2, 0x1E
            ])

            # Send the data
            com.send_data(body, expected_payload_len=2)
            print("\nCommand sent for Get Push Control Mode")

            # Wait for response
            response = com.read_response(timeout=5)
            print("\nResponse received for Get Push Control Mode: ", response)
            get_push = int.from_bytes(response[12:16], 'big')

            print("\nRead response from meter to check Get Push Control Mode", get_push)
            if get_push == 60:
                print("Verify Push Control Mode: ",get_push)
                # logging.info(f"Get Push Control Mode is Successfully done")
                return True
            else:
                print(f"\nError in Get Push Control Mode, Response{response}")
                # logging.info(f"Error in Get Push Control Mode, Response{response}")
                return False
        except Exception as e:
            print(f"\nPort {serial_port}, Error in Get Push Control Mode: {e}")
            # logging.error(f"Port {serial_port}, Error in Get Push Control Mode: {e}")
    return False

def set_periodic_push_ipv6_address(serial_port, com, ipv6_address):
    print("\nStarting Set Periodic Push IPv6 Address")
    # logging.info(f"Sending Command To Set Periodic Push IPv6 Address")
    retryCnt = 3
    while (retryCnt):
        try:
            if not com.open():
                return None

            body = ""
            # Frame to send the command to Set Periodic Push IPv6 Address
            if ipv6_address == "2406:da1a:565:f50d:c7ee:8336:ef46:ffc2,4059":
                body = bytes([
                    0xAA, 0x01, 0xD3, 0x1D, 0xC9, 0xFF, 0xFF, 0xFF, 0xFF,0x04, 0x04, 0x2D, 0xD3, 0x1D,0x32, 0x34, 0x30, 0x36,0x3A, 0x64, 0x61, 0x31, 0x61,0x3A, 0x35, 0x36, 0x35,0x3A, 0x66, 0x35, 0x30, 0x64,0x3A, 0x63, 0x37, 0x65,0x65, 0x3A, 0x38, 0x33, 0x33,0x36, 0x3A, 0x65, 0x66,0x34, 0x36, 0x3A, 0x66, 0x66,0x63, 0x32, 0x2C, 0x34,0x30, 0x35, 0x39, 0x70, 0x70
                    ])

            elif ipv6_address == "2406:da1a:f52:c907:7a85:8dfe:a74d:c7da,4059":
                body = bytes([
                    0xAA, 0x01, 0xD3, 0x1D, 0xC9, 0xFF, 0xFF, 0xFF,0xFF, 0x04, 0x04, 0x2D, 0xD3, 0x1D, 0x32, 0x34, 0x30, 0x36, 0x3A, 0x64, 0x61, 0x31, 0x61, 0x3A, 0x66, 0x35, 0x32, 0x3A, 0x63, 0x39, 0x30, 0x37, 0x3A, 0x37, 0x61, 0x38, 0x35, 0x3A, 0x38, 0x64, 0x66, 0x65, 0x3A, 0x61, 0x37, 0x34, 0x64, 0x3A, 0x63, 0x37, 0x64, 0x61, 0x2C, 0x34, 0x30, 0x35, 0x39, 0xDA, 0xCA
                    ])
            
            elif ipv6_address == "2406:da1a:ccf:9500:eeaa:4c65:58ae:63bb,4059":
                body = bytes([
                    0xAA, 0x01, 0xD3, 0x1D, 0xC9, 0xFF, 0xFF, 0xFF, 0xFF, 0x04, 0x04, 0x2D, 0xD3, 0x1D, 0x32, 0x34, 0x30, 0x36, 0x3A, 0x64, 0x61, 0x31, 0x61, 0x3A, 0x63, 0x63, 0x66, 0x3A, 0x39, 0x35, 0x30, 0x30, 0x3A, 0x65, 0x65, 0x61, 0x61, 0x3A, 0x34, 0x63, 0x36, 0x35, 0x3A, 0x35, 0x38, 0x61, 0x65, 0x3A, 0x36, 0x33, 0x62, 0x62, 0x2C, 0x34, 0x30, 0x35, 0x39, 0x64, 0xE6
                    ])
            
            elif ipv6_address == "2603:c021:4007:a000:db7a:c271:e6f8:c28d,4059":
                body = bytes([
                    0xAA, 0x01, 0xD3, 0x1D, 0xC9, 0xFF, 0xFF, 0xFF, 0xFF, 0x04, 0x04, 0x2E, 0xD3, 0x1D, 0x32, 0x36, 0x30, 0x33, 0x3A, 0x63, 0x30, 0x32, 0x31, 0x3A, 0x34, 0x30, 0x30, 0x37, 0x3A, 0x61, 0x30, 0x30, 0x30, 0x3A, 0x64, 0x62, 0x37, 0x61, 0x3A, 0x63, 0x32, 0x37, 0x31, 0x3A, 0x65, 0x36, 0x66, 0x38, 0x3A, 0x63, 0x32, 0x38, 0x64, 0x2C, 0x34, 0x30, 0x35, 0x39, 0x4E, 0x41
                    ])
            

            # Send the data
            com.send_data(body, expected_payload_len=2)
            print("\nCommand sent for Set Periodic Push IPv6 Address")

            # Wait for response
            response = com.read_response(timeout=5)
            print("\nResponse received for Set Periodic Push IPv6 Address: ", response)
            pattern = bytes.fromhex("e8 03")
            print("\nRead response from meter to check Set Periodic Push IPv6 Address")
            if pattern in response:
                print("Default Periodic Push IPv6 Address is Successfully done")
                return True
            else:
                print(f"\nError in Set Periodic Push IPv6 Address, Response{response}")
                # logging.info(f"Error in Set Periodic Push IPv6 Address, Response{response}")
                return False
        except Exception as e:
            print(f"\nPort {serial_port}, Error in Set Periodic Push IPv6 Address: {e}")
            # logging.error(f"Port {serial_port}, Error in Set Periodic Push IPv6 Address: {e}")
    return False

def get_periodic_push_ipv6_address(serial_port, com, ipv6_address):
    print("\nStarting Get Periodic Push IPv6 Address")
    # logging.info(f"Sending Command To Get Periodic Push IPv6 Address")
    retryCnt = 3
    while (retryCnt):
        try:
            if not com.open():
                return None

            # Frame to send the command to Get Periodic Push IPv6 Address
            body = bytes([
                0xAA, 0x01, 0xD3, 0x1C, 0xC9,
                0xFF, 0xFF, 0xFF, 0xFF,
                0x04, 0x04, 0x02, 0xD3, 0x1C, 0x13, 0x86
            ])

            # Send the data
            com.send_data(body, expected_payload_len=2)
            print("\nCommand sent for Get Periodic Push IPv6 Address")

            # Wait for response
            response = com.read_response(timeout=5)
            print("\nResponse received for Get Periodic Push IPv6 Address: ", response)
            get_push = response[12:56].decode('utf-8').rstrip('\x00')

            print("\nRead response from meter to check Get Periodic Push IPv6 Address", get_push)
            print("\nExpected Periodic Push IPv6 Address: ", ipv6_address)
            if get_push.strip() == ipv6_address:
                print("Verify Periodic Push IPv6 Address: ",get_push)
                # logging.info(f"Get Periodic Push IPv6 Address is Successfully done")
                return True
            else:
                print(f"\nError in Get Periodic Push IPv6 Address, Response{response}")
                # logging.info(f"Error in Get Periodic Push IPv6 Address, Response{response}")
                return False
        except Exception as e:
            print(f"\nPort {serial_port}, Error in Get Periodic Push IPv6 Address: {e}")
            # logging.error(f"Port {serial_port}, Error in Get Periodic Push IPv6 Address: {e}")
    return False




com = Communication("com16")

ipv6_address = "2406:da1a:565:f50d:c7ee:8336:ef46:ffc2,4059"
set_push_interval("com16", com)

# get_push_interval("com16", com)

# set_periodic_push_ipv6_address("com16", com, ipv6_address)

# get_periodic_push_ipv6_address("com16", com, ipv6_address)