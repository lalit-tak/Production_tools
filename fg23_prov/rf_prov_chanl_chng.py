def send_reboot_nic_tap_command(ser_initilizer, args: argparse):
    global tap_filter, nic_com
    serial_initialization(ser_initilizer, args.serial_port, nic_com)
    
    payload = bytes([0, TapMessageType.RESET_REQUEST.value])
    
    tap_filter = True
    nic_com.hdlc_decode.set()
    
    send_raw_hdlc_data(nic_com, payload)
    
    try:
        nic_com.tap_reset_response_queue.get(timeout=nic_com.TAP_RESET_RESPONSE_RECEIVE_TIMEOUT_S)
    except queue.Empty:
        error_print_and_exit(
            "Tap reset response message not received in the given timeout!",
            ExitCodes.RECEPTION_TIMEOUT,
        )
        # serial_cleanup(nic_com)
        return False

    nic_com.hdlc_decode.clear()
    tap_filter = False
    
    logging.info("Waiting for NIC to reboot...")
    return True
    