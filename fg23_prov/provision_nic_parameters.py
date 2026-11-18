# Copyright 2024 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.
#

import argparse
import logging
from fg23_prov import nic_provisioning
import shlex 

SECRET_MAX_SIZE = 32
KEY_SIZE = 16
FLAG_ID_LENGTH = 3
MINIMUM_NETWORK_ADDRESS = 1
MAXIMUM_NETWORK_ADDRESS = 0xFFFFFF
MINIMUM_NETWORK_CHANNEL = 1
MAXIMUM_NETWORK_CHANNEL = 12
MINIMUM_NODE_ADDRESS = 1
# 0x0xFFFFFFFE => APP_ADDR_ANYSINK
# 0x0xFFFFFFFF => APP_ADDR_BROADCAST
MAXIMUM_NODE_ADDRESS = 0xFFFFFFFD


def validate_key(key: str) -> bytes:
    byte_data = bytes.fromhex(key)
    if len(byte_data) != KEY_SIZE:
        raise argparse.ArgumentTypeError(
            "Given key must be " + str(KEY_SIZE) + " bytes long"
        )
    return byte_data


def validate_network_address(network_address: str) -> int:
    network_address = int(network_address, 0)
    if network_address not in range(
        MINIMUM_NETWORK_ADDRESS, MAXIMUM_NETWORK_ADDRESS + 1
    ):
        raise argparse.ArgumentTypeError("Given Network Address is out of range")
    return network_address


def validate_network_channel(network_channel: str) -> int:
    network_channel = int(network_channel, 0)
    if network_channel not in range(
        MINIMUM_NETWORK_CHANNEL, MAXIMUM_NETWORK_CHANNEL + 1
    ):
        raise argparse.ArgumentTypeError("Given Network Channel is out of range")
    return network_channel


def validate_node_address(node_address: str) -> int:
    node_address = int(node_address, 0)
    if node_address < MINIMUM_NODE_ADDRESS or node_address > MAXIMUM_NODE_ADDRESS:
        raise argparse.ArgumentTypeError("Given Node Address is out of range")

    # Checking we are not in the multicast space
    if (node_address & 0xFF000000) == 0x80000000:
        raise argparse.ArgumentTypeError("Given Node Address is in the multicast address range")

    return node_address


class CustomArgumentParser(argparse.ArgumentParser):
    def convert_arg_line_to_args(self, arg_line):
        # Skip empty lines and comments
        if not arg_line.strip() or arg_line.strip().startswith('#'):
            return []
        
        # Use shlex to properly handle quoted strings
        try:
            # This will preserve quoted empty strings like ""
            return shlex.split(arg_line, posix=True)
        except ValueError as e:
            # Handle potential errors in the line format
            logging.warning(f"Error parsing argument line: {arg_line}")
            logging.warning(f"Error details: {str(e)}")
            # Return the line split by whitespace as a fallback
            return arg_line.strip().split()


# if __name__ == "__main__":
def run_provisioning(ser_initilizer, provisioning_dict):
    try:
        nic_parameters_data = {}
        prov_sucess = False
        summary = ""
        nic_reboot_status = False

        parser = CustomArgumentParser(fromfile_prefix_chars="@")
        # Serial parameters

        args = argparse.Namespace(
            serial_port = str(provisioning_dict['serial_port']),
            encryption_key = validate_key(provisioning_dict['encryption_key']) if provisioning_dict['encryption_key'] else None,
            authentication_key = validate_key(provisioning_dict['authentication_key']) if provisioning_dict['authentication_key'] else None,
            network_address = validate_network_address(provisioning_dict['network_address']) if provisioning_dict['network_address'] else None,
            network_channel = validate_network_channel(provisioning_dict['network_channel']) if provisioning_dict['network_channel'] else None,
            node_address = validate_node_address(provisioning_dict['node_address']) if provisioning_dict['node_address'] else None
        )

        # com = nic_provisioning.Communication()
        com_ser = nic_provisioning.serial_initialization(ser_initilizer)

        # nic_reboot_status = nic_provisioning.send_reboot_nic_tap_command(com_ser, args)
        # print("NIC reboot status: ", nic_reboot_status)
        nic_reboot_status = True
        if nic_reboot_status:
            nic_parameters_data, prov_sucess = nic_provisioning.provision_nic_parameters(com_ser, args)
        else:
            return {}, False
        nic_provisioning.stop_rx_thread_only(com_ser)
        return nic_parameters_data, prov_sucess
    except Exception as e:
        print("Exception in Provisioning: ",e)
        nic_provisioning.stop_rx_thread_only(com_ser)
        return {}, False
