import argparse
from colorama import Fore
import queue
import logging
from fg23_prov import wirepas_provisioning
import serial
import sys
import time
from fg23_prov.wirepas_provisioning import WirepasProvisioning
# from threading import Thread, Event
from struct import pack, unpack
from enum import Enum
from threading import Thread, Event, Lock
from time import sleep

from yahdlc import (
    FRAME_ACK,
    FRAME_DATA,
    FRAME_NACK,
    FCSError,
    MessageError,
    frame_data,
    get_data,
    get_data_reset,
)


class ExitCodes(Enum):
    SUCCESS = 0
    SENDING_FAILED = 1
    RECEPTION_TIMEOUT = 2
    INVALID_PARAMETERS = 3
    MISSING_PARAMETERS = 4
    HDLC_PACKET_TOO_LARGE = 5
    CALL_TO_MAIN = 6
    SERIAL_ERROR = 7

class MessageType(Enum):
    PROVISIONING_WRITE_REQUEST = 0
    PROVISIONING_WRITE_RESPONSE = 1
    PROVISIONING_READ_REQUEST = 2
    PROVISIONING_READ_RESPONSE = 3
    PROVISIONING_REBOOT_REQUEST = 4
    EXIT_FACTORY_MODE = 5

class TapMessageType(Enum):
    RESET_REQUEST = 0x16
    RESET_RESPONSE = 0x17

PROVISIONING_CHALLENGE = b"WPP\n"
PROVISIONING_CHALLENGE_RESP = b"OK\n"
PROVISIONING_CHALLENGE_PERIOD_S = 0.05  # Every 50 ms
PROVISIONING_RESET_INTERVAL_S = 2.2  # 500ms
PERFORM_ACTIVITY = MessageType.PROVISIONING_WRITE_REQUEST
bad_fcs_count = 0
last_reset_time = 0


class Communication:
    # ... existing attributes ...
    def __init__(self):
        self.ser = serial.Serial()
        self.hdlc_decode = Event()
        self.stop_rx = Event()
        self.serial_lock = Lock()
        self.tx_seq = 0
        self.MAX_TX_ATTEMPT = 3
        self.tx_queue = queue.Queue(self.MAX_TX_ATTEMPT)
        self.rx_challenge_queue = queue.Queue()
        self.rx_ftype_queue = queue.Queue()
        self.tap_reset_response_queue = queue.Queue()
        self.provisioning_success_queue = queue.Queue()
        self.read_parameters_queue = queue.Queue()
        self.tap_filter = False  # <-- move here

        self.SERIAL_BAUDRATE = 9600
        self.ACK_NACK_TIMEOUT_S = 0.500
        self.TAP_RESET_RESPONSE_RECEIVE_TIMEOUT_S = 3
        self.DRY_RUN_RECEIVE_TIMEOUT_S = 2
        self.READ_PARAMETERS_TIMEOUT_S = 3
        self.EMBEDDED_HDLC_BUFFER_MAX_SIZE = 512
        self.timeout = 10

# Filter tap messages to not interfere with the other types of messages
tap_filter = False

def error_print_and_exit(message: str, error_code: ExitCodes):
    logging.error(Fore.RED + message + Fore.RESET)
    print(error_code.value)

def success_print(message):
    logging.info(Fore.GREEN + message + Fore.RESET)

def send_raw_hdlc_data(com: Communication, data: bytes):
    hdlc_frame = frame_data(data, FRAME_DATA, com.tx_seq)

    if len(hdlc_frame) > com.EMBEDDED_HDLC_BUFFER_MAX_SIZE:
        error_print_and_exit(
            "Length of the HDLC packet cannot be processed by the embedded application!",
            ExitCodes.HDLC_PACKET_TOO_LARGE,
        )

    for _ in range(com.MAX_TX_ATTEMPT):
        com.tx_queue.put_nowait(hdlc_frame)

    # Cleaning any remaining items stored in the rx_ftype queue
    with com.rx_ftype_queue.mutex:
        com.rx_ftype_queue.queue.clear()

    ret = False
    try:
        while com.tx_queue.empty() is False:
            packet = com.tx_queue.get()
            logging.debug(f"Sending {len(packet)} bytes long data frame: {packet.hex()} with seq: {com.tx_seq}")
            if not com.ser.is_open:
                logging.error("Port is closed")
                return ret
            else:
                com.ser.write(packet)
            try:
                ftype = com.rx_ftype_queue.get(timeout=com.ACK_NACK_TIMEOUT_S)

            except queue.Empty:
                logging.warning("Timeout detected!")
                continue

            if ftype != FRAME_ACK:
                ret = False
                sleep(0.5)
                com.tx_seq += 1
                com.tx_seq %= 7
                logging.debug(f"Changing sequence to {com.tx_seq}")
                continue
            else:
                with com.tx_queue.mutex:
                    com.tx_queue.queue.clear()
                ret = True

        com.tx_seq += 1
        com.tx_seq %= 7

        return ret

    except serial.SerialException:
        logging.info()
        error_print_and_exit("Serial connection problem!", ExitCodes.SERIAL_ERROR)

def send_factory_mode_message(com: Communication, data: bytes, type: MessageType) -> bool:
    # Generating header
    global bad_fcs_count
    global PERFORM_ACTIVITY
    header = pack("<BB", 0, type.value)
    message = header + data
    bad_fcs_count = 0
    PERFORM_ACTIVITY = type.value

    return send_raw_hdlc_data(com, message)

def parse_message_received(com: Communication, data: bytes):
    global PERFORM_ACTIVITY
    if com.tap_filter:
        logging.debug("Catched by tap filter")
        if data.startswith(bytes([0, TapMessageType.RESET_RESPONSE.value])):
            logging.debug("Received tap reset response: Status = %u", data[2])
            com.tap_reset_response_queue.put(True)
        return
    
    if data == None:
        if PERFORM_ACTIVITY == MessageType.PROVISIONING_WRITE_REQUEST:
            logging.debug(f"Returning error for bad fcs in provisioning write")
            com.provisioning_success_queue.put(False)
        elif PERFORM_ACTIVITY == MessageType.PROVISIONING_READ_REQUEST:
            logging.debug("Returning error for bad fcs in provisioning read")
            com.read_parameters_queue.put(data)
        return

    # parse header
    version, type = unpack("<BB", data[0:2])
    if version != 0:
        logging.warning("Not a valid protocol version")
        return

    # Convert to enum
    try:
        type = MessageType(type)
    except ValueError:
        logging.warning("Unknown message type received")
        return

    # Remove header from received data
    data = data[2:]

    if type == MessageType.PROVISIONING_WRITE_RESPONSE:
        if wirepas_provisioning.is_provisioning_dry_run_successful(data) is True:
            logging.debug("Dry Run Successful! Sending reboot request")
            com.provisioning_success_queue.put(True)
        else:
            logging.debug("Dry Run returned an error! No reboot request sent!")
            com.provisioning_success_queue.put(False)
    elif type == MessageType.PROVISIONING_READ_RESPONSE:
        logging.debug("Read Request Response Received")
        com.read_parameters_queue.put(data)

def rx_callback(com: Communication):
    global bad_fcs_count
    
    read = bytes()
    
    while not com.stop_rx.is_set():
        try:
            # Exit if serial closed
            if com.ser is None or not com.ser.is_open:
                break

            data = com.ser.read(1)

            if not data:
                continue

            read += data
            logging.debug(f"rx_callback read data: {read}")

            if com.hdlc_decode.is_set():
                # HDLC Reading
                try:
                    get_data_reset()
                    data, ftype, seq_no = get_data(read)

                    logging.debug(
                        "Message received: %s %s %s",
                        ftype,
                        data.hex(),
                        seq_no,
                    )

                    com.rx_ftype_queue.put(ftype)

                    if ftype == FRAME_ACK:
                        logging.debug("Ack for seq: %u", seq_no)

                    elif ftype == FRAME_NACK:
                        logging.debug("Nack for seq: %u", seq_no)

                    elif ftype == FRAME_DATA:
                        logging.debug("Message received")

                        # Send ACK
                        if com.ser and com.ser.is_open:
                            com.ser.write(frame_data("", FRAME_ACK, seq_no))

                        parse_message_received(com, data)

                    else:
                        logging.debug(read.hex())
                        logging.debug("Invalid frame")

                    read = bytes()

                except MessageError:
                    pass

                except FCSError:
                    bad_fcs_count += 1
                    logging.warning(f"Bad FCS")
                    logging.debug(f"Bad FCS, read bytes: {read}")
                    read = bytes()
                    # if bad_fcs_count == 10:
                    #     logging.debug(f"Bad FCS Count: {bad_fcs_count} reached")
                    #     parse_message_received(com, None)

            else:
                # Serial Reading (No protocol)
                if PROVISIONING_CHALLENGE_RESP in read:
                    com.rx_challenge_queue.put(True)

        except serial.SerialException:
            logging.debug("Serial port closed, stopping rx thread")
            break

        except Exception as e:
            logging.debug(f"RX thread stopped: {e}")
            break

def wait_for_challenge_response(com: Communication):
    # Disable HDLC Serial Reading
    global last_reset_time
    timeout_s = float(45.0)
    com.hdlc_decode.clear()

    logging.info("Sending Provisioning Challenge...")
    logging.info("Sending Soft Reset sequence and Provisioning Challenge in loop...")

    last_reset_time = 0
    last_challenge_time = 0
    with com.rx_challenge_queue.mutex:
        com.rx_challenge_queue.queue.clear()

    start_time = time.time()

    logging.debug(f"Sending provisioning challenge in wait for challenge respose")
    while com.rx_challenge_queue.empty():
        current_time = time.time()
        com.ser.write(PROVISIONING_CHALLENGE)
        sleep(PROVISIONING_CHALLENGE_PERIOD_S)
        if current_time - start_time > timeout_s:
            error_print_and_exit(
                f"Device did not respond to challenge within {timeout_s} seconds. "
                "Please check device connection and power.",
                ExitCodes.RECEPTION_TIMEOUT,
            )
        if current_time - start_time > timeout_s:
            error_print_and_exit("Timeout waiting for challenge response", ExitCodes.RECEPTION_TIMEOUT)
        

        if current_time - last_reset_time >= PROVISIONING_RESET_INTERVAL_S:
            try:
                # Send reset without waiting for response
                with com.serial_lock:
                    com.hdlc_decode.set()  # Temporarily enable HDLC for reset
                    payload = bytes([0, TapMessageType.RESET_REQUEST.value])
                    logging.debug(f"payload in wait for challenge respose: {payload}")

                    # Clear queues before sending reset
                    with com.rx_ftype_queue.mutex:
                        logging.debug(f"clear rx ftype queue")
                        com.rx_ftype_queue.queue.clear()

                    # Send reset command (don't wait for response)
                    hdlc_frame = frame_data(payload, FRAME_DATA, com.tx_seq)
                    if len(hdlc_frame) <= com.EMBEDDED_HDLC_BUFFER_MAX_SIZE:
                        com.ser.write(hdlc_frame)
                        logging.debug(f"hdlc frame; {hdlc_frame}")
                        logging.debug("Reset command sent")
                        com.tx_seq = (com.tx_seq + 1) % 7

                    com.hdlc_decode.clear()  # Disable HDLC for challenge mode
                logging.debug("Soft reset sequence query sent")
                last_reset_time = current_time
            except serial.SerialException as e:
                error_print_and_exit(
                    f"Serial connection problem during soft reset: {str(e)}",
                    ExitCodes.SERIAL_ERROR,
                )
        
        # Send challenge periodically
        if current_time - last_challenge_time >= PROVISIONING_CHALLENGE_PERIOD_S:
            try:
                with com.serial_lock:
                    com.ser.write(PROVISIONING_CHALLENGE)
                logging.debug("Challenge sent")
                last_challenge_time = current_time
            except serial.SerialException as e:
                error_print_and_exit(
                    f"Serial connection problem during challenge: {str(e)}",
                    ExitCodes.SERIAL_ERROR,
                )

    sleep(0.005)
    with com.rx_challenge_queue.mutex:
        com.rx_challenge_queue.queue.clear()

    # Enable HDLC Serial Reading
    com.hdlc_decode.set()
    logging.info("Received Provisioning Challenge Response!")

def perform_parameters_provisioning(com: Communication, wp_prov: WirepasProvisioning):
    provisioning_packet = wp_prov.get_provisioning_packet()

    logging.info("Sending Provisioning Packet")
    if (
        send_factory_mode_message(com, provisioning_packet, MessageType.PROVISIONING_WRITE_REQUEST)
        is False
    ):
        error_print_and_exit(
            "Sending Provisioning Packet isn't successful!", ExitCodes.SENDING_FAILED
        )

    try:
        validation_run_success = com.provisioning_success_queue.get(
            timeout=com.DRY_RUN_RECEIVE_TIMEOUT_S
        )
    except queue.Empty:
        error_print_and_exit(
            "Provisioning validation run return code not received in the given timeout!",
            ExitCodes.RECEPTION_TIMEOUT,
        )

    if validation_run_success is False:
        error_print_and_exit(
            "Provisioning validation run was not successful!",
            ExitCodes.INVALID_PARAMETERS,
        )

    logging.info("Applying parameters to the NIC")

    if send_factory_mode_message(com, bytes(), MessageType.PROVISIONING_REBOOT_REQUEST) is False:
        error_print_and_exit(
            "Sending Device Reboot Request not successful!", ExitCodes.SENDING_FAILED
        )
        return False
    else:
        return True

def perform_parameters_reading(com: Communication):
    logging.info("Sending request to read NIC Parameters")
    nic_parameters_data = {}
    prov_sucess = False
    if send_factory_mode_message(com, bytes(), MessageType.PROVISIONING_READ_REQUEST) is False:
        error_print_and_exit(
            "Sending Read Parameters Request not successful!", ExitCodes.SENDING_FAILED
        )
        return nic_parameters_data, prov_sucess

    try:
        nic_parameters_data = com.read_parameters_queue.get(
            timeout=com.READ_PARAMETERS_TIMEOUT_S
        )

        nic_parameters_data = wirepas_provisioning.decode_prov_dict(nic_parameters_data)
        logging.debug(f"Nic parametes data: {nic_parameters_data}")
        if nic_parameters_data is None:
            logging.debug(f"No nic parameter data is received so return immediately for retry")
            return {}, False
        wirepas_provisioning.print_provisioning_summary(nic_parameters_data)

        prov_sucess = wirepas_provisioning.get_provisioning_status(nic_parameters_data)
    except queue.Empty:
        error_print_and_exit(
            "Read Parameters response was not received in the given timeout!",
            ExitCodes.RECEPTION_TIMEOUT,
        )
        return {}, False

    if prov_sucess is True:
        success_print("NIC is successfully provisioned!")
    else:
        error_print_and_exit(
            "Missing parameters in the device!", ExitCodes.MISSING_PARAMETERS
        )
    return nic_parameters_data, prov_sucess

def exit_factory_mode(com: Communication):
    logging.info("Sending request to exit factory mode")
    if send_factory_mode_message(com, bytes(), MessageType.EXIT_FACTORY_MODE) is False:
        error_print_and_exit(
            "Sending Exit Factory Mode Packet isn't successful!",
            ExitCodes.SENDING_FAILED,
        )
    # serial_cleanup(com.fm)
    
def serial_initialization(ser_initilizer):
    com = Communication()
    com.ser = ser_initilizer

    rx_thread = Thread(
        target=rx_callback,
        daemon=True,
        args=(com,),
    )
    rx_thread.start()
    return com

def serial_cleanup(com: Communication):
    try:
        logging.info("Stopping RX thread")

        com.stop_rx.set()     # stop rx loop

        sleep(0.1)            # give thread time to exit

        if com.ser and com.ser.is_open:
            logging.info("Closing serial port")
            com.ser.close()

    except Exception as e:
        logging.warning(f"Error while closing serial port: {e}")

def stop_rx_thread_only(com: Communication):
    """Stop the rx thread without closing the serial port."""
    try:
        logging.info("Stopping provisioning RX thread")
        com.stop_rx.set()
        sleep(0.2)  # give thread time to exit
    except Exception as e:
        logging.warning(f"Error stopping rx thread: {e}")

def provision_nic_parameters(com: Communication, args: argparse):
    # global nic_com
    nic_parameters_data = {}
    prov_sucess = False
    logging.info("Starting NIC Provisioning")

    # Check if all parameters are None
    if (
        args.encryption_key is None
        and args.authentication_key is None
        and args.network_address is None
        and args.network_channel is None
        and args.node_address is None
    ):
        logging.error(
            "No parameters specified for provisioning! All parameters are NULL!"
        )
        logging.error("At least one parameter must be specified.")
        sys.exit(ExitCodes.MISSING_PARAMETERS.value)

    wp_prov = WirepasProvisioning(
        args.encryption_key,
        args.authentication_key,
        args.network_address,
        args.network_channel,
        args.node_address,
    )
    prov_status = False
    for i in range(3):
        logging.debug(f"Iteration to provision: {i+1}")
        wait_for_challenge_response(com)
        prov_status = perform_parameters_provisioning(com, wp_prov)
        if prov_status:
            break
        else:
            exit_factory_mode(com)
            sleep(1)


    # Waiting for NIC to reboot before asking the parameters
    logging.info("Waiting for NIC to reboot...")

    for i in range(3):
        logging.debug(f"Iteration to read prameters: {i+1}")
        wait_for_challenge_response(com)
        nic_parameters_data, prov_sucess = perform_parameters_reading(com)
        if prov_sucess:
            break
        else:
            exit_factory_mode(com)
            sleep(1)


    exit_factory_mode(com)

    # sys.exit(ExitCodes.SUCCESS.value)
    # serial_cleanup(com)
    return nic_parameters_data, prov_sucess

def send_reboot_nic_tap_command(com, args: argparse):
    # com = Communication()
    # global tap_filter, nic_com
    # serial_initialization(ser_initilizer, args.serial_port, nic_com)
    # serial_initialization(ser_initilizer)
    payload = bytes([0, TapMessageType.RESET_REQUEST.value])
    
    com.tap_filter = True
    com.hdlc_decode.set()
    
    send_raw_hdlc_data(com, payload)
    
    try:
        com.tap_reset_response_queue.get(timeout=com.TAP_RESET_RESPONSE_RECEIVE_TIMEOUT_S)
    except queue.Empty:
        error_print_and_exit(
            "Tap reset response message not received in the given timeout!",
            ExitCodes.RECEPTION_TIMEOUT,
        )
        # serial_cleanup(nic_com)
        return False

    com.hdlc_decode.clear()
    com.tap_filter = False
    
    logging.info("Waiting for NIC to reboot...")
    return True
    
def read_nic_parameters(com: Communication, args: argparse):
    # global nic_com
    wait_for_challenge_response(com)
    perform_parameters_reading(com)

    exit_factory_mode(com)

    sys.exit(ExitCodes.SUCCESS.value)

if __name__ == "__main__":
    error_print_and_exit(
        "Unavailable. Please use 'provision_nic_parameters.py' or 'read_nic_parameters.py'",
        ExitCodes.CALL_TO_MAIN,
    )
