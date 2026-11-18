import os
import argparse
from gp_node.network.network_api import NetworkAPI
from gp_node.network.protocols.common.tap import TAPHandler, TAPPacket, TAPError
from gp_node.network.protocols._1p.flash_io_new import FlashIOMasterNew, FlashIOErrorNew
from gp_node.utils.address import Address
import serial
import serial.tools.list_ports
import gp_node.utils.serialize as serialize
import json
import datetime
import time
import threading
import queue
import logging
from logging.handlers import TimedRotatingFileHandler
from threading import Thread
import socket
import paho.mqtt.client as mqtt
import signal
import sys
from config import Config
from Test_cases_verificationClass import TestCasePCTMCT
import easygui
from queue import Queue
import msvcrt
import tkinter as Tk
import re
from fg23_prov import read_nic_parameters, provision_nic_parameters
from colorama import Fore, Style, init
import gc
from multiprocessing import Process, freeze_support
from multiprocessing import  Event
from queue import Queue
import xlrd
import pythoncom
import win32com.client
import openpyxl
from provisioning_tool.ftt_prov_logging import setup_logger
from provisioning_tool import rtt_data
from provisioning_tool.provision_img_parameters import run_provisioning
import provisioning_tool.wirepas_provisioning as wirepas_provisioning
import db_connect
import pandas as pd
from colorama import Fore, Style, init
# setup_logger()
init(autoreset=True)

ACCESS_KEY = "PUT_YOUR_ACCESS_KEY_HERE"
SECRET_KEY = "PUT_YOUR_SECRET_KEY_HERE"
bucket_name = "PUT_YOUR_BUCKET_NAME_HERE"
folder_name = "PUT_YOUR_FOLDER_NAME_HERE"


# ============================================================================
# DICTIONARY-BASED RESULT STORAGE
# ----------------------------------------------------------------------------
# The original script tracked every test step positionally: MeterInfo /
# result_list were built with .append() in a fixed hand-maintained order,
# FTT_Fail_list had to line up with result_list by index (via fail_indexes)
# to produce readable failure text, and run()'s serial-number re-entry check
# poked entry[1][1] / entry[1][-1] / entry[2][-4] -- magic indices into an
# opaque list-of-lists ([mac, MeterInfo, result_list, bookName, fileName]).
# Any of those lists gaining/losing an entry silently shifted every
# column/message after it -- and several retry loops in this script *could*
# exit having appended nothing at all for a step if every attempt raised an
# exception, which would shift every later column by one position under the
# old positional writer.
#
# This version stores everything in named dictionaries instead, mirroring
# pct_multiport_dict_threaded.py:
#   meter_info : {'Meter_PCB_Serial_No': ..., 'Live_version': ..., ...}
#   test_result: {'factory_reset': 'pass', 'factory_reset_Retry_Count': '1', ...}
#   result_log : {com_port: {'mac', 'meter_info', 'result', 'bookName',
#                             'fileName', 'com_port'}, ...}   <- keyed by COM
#                 port instead of being a plain list of [mac, MeterInfo,
#                 result_list, bookName, fileName] entries.
#
# Header text is kept byte-identical to the original script's header lists
# wherever possible (including 'MAC_ADDR' as the literal column-1 header --
# the original addDefaultFttLog used mac = "MAC_ADDR" as a placeholder that
# became the header cell text itself, unlike a hand-written 'MAC Address'
# header). The one deliberate exception is the "retryN" / "retry_count"
# placeholders (e.g. 'retry1', 'retry17') -- these carried no information
# about which step they belonged to, so (mirroring the PCT conversion) they
# are renamed to named '<Step>_Retry_Count' siblings.
# ============================================================================

# ============================================================================
# PRE-EXISTING BUGS PRESERVED VERBATIM (see final conversion report for full
# detail with original line numbers) -- this is a pure data-structure
# refactor, not a bug-fix pass:
#   1. In the "Again verify serial number" block, a failed re-read sets the
#      result to capital 'Fail' (not lowercase 'fail'), so it silently never
#      counts as a failure anywhere that checks `== 'fail'`.
#   2. build_fail_messages() below intentionally reproduces the original's
#      swapped-argument message format `"COM Port {}: {}".format(<message>,
#      <com_port>)`, which renders as "COM Port <message>: <com_port>"
#      instead of the sane "COM Port <com_port>: <message>".
#   3. In run()'s serial-number re-entry check, on an actual mismatch the RF
#      branch sets Verify_Serial_No_Mismatch to 'fail' but the non-RF branch
#      sets it to 'pass' -- an existing inconsistency, preserved as-is.
# ============================================================================


def verify_log_xlsc(bookName,fileName):
    loc = bookName#self.LOG_FILE_NAME

    try:
        wb = openpyxl.load_workbook(loc)
        sheet = wb.active
        cell_value = sheet.cell(row=1, column=1).value
    except:
        print("LOG XL file not found, creating one for you")
        wb = openpyxl.Workbook()
        wb.create_sheet(index = 0 , title = fileName) # MRI_DATA_LOG
        sheet = wb.active
        print("sheet name = ",sheet.title)
        del(wb['Sheet'])
        wb.save(loc)
        print("New xlsc file created")
        return False
    else:
        return True

def get_system_mac_address(toolName):
    mac = "None"
    try:
        if sys.platform == 'win32':
            current_header = ""
            for raw_line in os.popen("ipconfig /all"):
                line = raw_line.rstrip('\n')
                if not line.strip():
                    continue
                if line == line.lstrip():          # unindented line = new adapter section header
                    current_header = line.strip()
                    continue
                stripped = line.lstrip()
                if stripped.startswith('Physical Address') and ':' in stripped:
                    if current_header.lower().startswith('ethernet adapter'):
                        value = stripped.split(':', 1)[1].strip()
                        if value:
                            mac = value.replace('-', ':')
                            break
        else:
            for line in os.popen("/sbin/ifconfig"):
                if line.find('Ether') > -1:
                    mac = line.split()[4]
                    break
    except Exception as e:
        logging.error("Error in get mac address")
    logging.info(f"In FTT, MAC Address of system: {mac}")
    return mac



def get_header_column_map(sheet):
    """Read the header row (row 1) into {header_name: column_index}. Writing
    a row then becomes a name -> column lookup instead of relying on
    positional column counters staying in sync with the header row."""
    header_map = {}
    for col_idx, cell in enumerate(sheet[1], start=1):
        if cell.value is not None:
            header_map[cell.value] = col_idx
    return header_map


def add_log_xlsc(log_entry):
    """Append one row to the log workbook from a dictionary-shaped
    log_entry (see build_log_entry). Every value is written to the column
    matching its own key/header name -- looked up by name, not position --
    replacing the old add_log_xlsc(log, row_state) that unpacked a 5-item
    positional list ([mac, MeterInfo, result_list, bookName, fileName]) and
    wrote MeterInfo/result values by raw list position. If a key isn't in
    the header yet, the sheet is extended with a new column instead of
    silently dropping the value."""
    bookName = log_entry['bookName']
    fileName = log_entry['fileName']

    loc = bookName
    wb = openpyxl.load_workbook(loc)
    sheet1 = wb[fileName]

    numRows = sheet1.max_row + 1
    header_map = get_header_column_map(sheet1)

    def write(header_name, value):
        col_idx = header_map.get(header_name)
        if col_idx is None:
            col_idx = sheet1.max_column + 1
            sheet1.cell(row=1, column=col_idx).value = header_name
            header_map[header_name] = col_idx
        sheet1.cell(row=numRows, column=col_idx).value = value

    # 'MAC_ADDR' is the literal original header text for column 1 (the
    # original addDefaultFttLog used mac = "MAC_ADDR" as the value written
    # into the header row -- it was never "MAC Address").
    write('MAC_ADDR', log_entry['mac'])
    write('Index', numRows - 1)
    for key, value in log_entry['meter_info'].items():
        write(key, str(value))
    for key, value in log_entry['result'].items():
        write(key, str(value))

    wb.save(loc)


def is_manufacturing_name_enabled(data_dict):
    """Config switch for the Set/Get Manufacturing Name steps
    ('MANUFACTURING_NAME_SET': 1 = run, 0 = skip). Accepts 1/0, "1"/"0"
    and "True"/"False"; defaults to enabled when the key is absent so
    existing config files keep their current behaviour."""
    value = data_dict.get('MANUFACTURING_NAME_SET', 1)
    if isinstance(value, str):
        value = value.strip().lower()
        return value not in ('0', 'false', 'no', 'off', '')
    return bool(value)


def get_ftt_field_templates(meter_type, toolName, rf_prov, project='wb', manufacturing_name_enable=True):
    """
    Returns (meter_info_keys, result_keys, fail_messages) for the fields
    main_function() populates -- the single source of truth that used to be
    hand-duplicated between addDefaultFttLog's 4 branch header lists,
    main_function's append order, and FTT_Fail_list (which had to stay in
    perfect positional sync with result_list, via fail_indexes = [idx//2 for
    failing idx], to produce readable failure text).

    meter_info_keys/result_keys use the *exact* header text the original
    branch lists used (e.g. 'Meter_PCB_Serial_No', 'factory_reset') so
    existing on-disk Excel logs stay backward-compatible, with one
    documented exception: the original "retryN" placeholders (e.g.
    'retry1'..'retry19') carried no information about which step they
    belonged to, so -- mirroring the PCT conversion -- every step is
    followed by a named '<step>_Retry_Count' sibling key instead.

    meter_type is accepted only for interface symmetry with
    get_pct_field_templates(); in the original script addDefaultFttLog's
    MeterInfo header list was IDENTICAL across all 4 toolName/rf_prov
    branches (only the result/FTT_Fail_list branches actually varied), so
    meter_type has no effect on the returned field set here.

    Four fields ('Set Provisioning Channel', 'Set Provisioning Channel
    Status', 'Get Provisioning Channel', 'Check Provisioning Parameters
    Status') are only present when toolName contains 'rf' and rf_prov == 1,
    and are standalone flat values rather than a step+retry-count pair (the
    original script never gave them their own retry column either).

    When toolName contains 'img' (and is not the rf+rf_prov==1 case above),
    a different, larger set of standalone flat fields is added instead --
    the IMG (non-RF) provisioning parameters/status columns written by
    main_function's img_provisioning()/check_provisioning_status() call,
    same "no retry column" treatment as the RF provisioning fields.

    When toolName contains '4g' and project contains 'tn', four more
    step+retry-count pairs ('Set_Periodic_Push_IPV6', 'Get_Periodic_Push_IPV6',
    'Set_Event_Push_IPV6', 'Get_Event_Push_IPV6') plus their raw
    'Periodic_Push_IPV6'/'Event_Push_IPV6' meter_info values are added --
    mirroring the same '4g' in toolName and 'tn' in PROJECT gate
    main_function uses to decide whether to run those steps at all, so a
    non-4g/TN row still gets these columns defaulted (via
    fill_missing_fields()) instead of the sheet only growing them ad hoc
    the first time a 4g/TN row is logged.

    When manufacturing_name_enable is False the 'Set_Manufacturing_Name' /
    'Get_Manufacturing_Name' step+retry columns and the
    'Manufacturing_Name' column are left out of the log entirely,
    since main_function never runs those steps in that case.
    """
    toolName = str(toolName).lower()
    is_rf = 'rf' in toolName
    is_prov = is_rf and (rf_prov == 1)
    is_img_prov = 'img' in toolName and not is_prov
    # is_4g_tn = ('4g' in toolName) and ('tn' in str(project).lower())
    is_4g = '4g' in toolName

    meter_info_keys = [
        'Date_time', 'Original_Serial_Number', 'Live_version', 'Duplicate_Serial_No',
        'Check_Calib_Lock_Status_Result', 'Original_meter_address',
        'Active_Energy', 'Apparent_Energy', 'Reactive_Energy',
        'Meter_PCB_Serial_No', 'NIC_PCB_No', 'Internal_Version',
        'CalibSign', 'FrequencyCoeff', 'VCoeff', 'ICoeff[0]', 'ICoeff[1]',
        'ActPowerCoeff[0]', 'ActPowerCoeff[1]', 'PhAngle[0]', 'PhAngle[1]',
        'GPRS_Protocol_Value', 'Voltage_Influence_Test_Voltage',
    ]

    result_steps = [
        'get_duplicate_serial_num', 'Calibration_Unlock', 'set_original_Meter_Serial_No',
        'get_serial_num_after_set', 'Calib_Lock', 'Check_Calib_Lock_Status',
        'Verify_meter_address', 'Verify_DLMS_Activation', 'Verify_Clear_Energy',
        'Get_Meter_PCB_Serial_No', 'Get_NIC_PCB_No', 'Get_Internal_Version',
        'Verify_Meter_Calibration', 'Set_GPRS_Protocol', 'Get_GPRS_Protocol',
        'Verify_Voltage_Influence_Test',
    ]
    

    fail_messages = {
        'get_duplicate_serial_num': 'Fail in get duplicate serial number',
        'Calibration_Unlock': 'Fail in calib unlock',
        'set_original_Meter_Serial_No': 'Fail in set meter serial No',
        'get_serial_num_after_set': 'Fail in get meter serial No after set',
        'Calib_Lock': 'Fail in calib lock',
        'Check_Calib_Lock_Status': 'Fail in Check Calib Status',
        'Verify_meter_address': 'Fail in Verify Meter Address',
        'Verify_DLMS_Activation': 'Fail in Verify DLMS Activation',
        'Verify_Clear_Energy': 'Fail in verify Clear Energy',
        'Get_Meter_PCB_Serial_No': 'Fail in Get Meter PCB No',
        'Get_NIC_PCB_No': 'Fail in Get NIC PCB No',
        'Get_Internal_Version': 'Fail in Get Internal Version',
        'Verify_Meter_Calibration': 'Fail in Meter Calibration',
        'Set_GPRS_Protocol': 'Fail in Set GPRS Protocol',
        'Get_GPRS_Protocol': 'Fail in Get GPRS Protocol',
        'Verify_Voltage_Influence_Test': 'Fail in Voltage Influence Test',
        'factory_reset': 'Fail in Factory Reset',
        'Verify_Serial_No_Mismatch': 'Fail in Serial No Mismatch between Printed Meter Serial No and Inside Meter Serial No',
        'Live_version_Status': 'Fail in Live Version',
    }

    if manufacturing_name_enable:
        result_steps += ['Set_Manufacturing_Name', 'Get_Manufacturing_Name']
        meter_info_keys.append('Manufacturing_Name')
        fail_messages['Set_Manufacturing_Name'] = 'Fail in Set Manufacturing Name'
        fail_messages['Get_Manufacturing_Name'] = 'Fail in Get Manufacturing Name'

    result_keys = []
    for step in result_steps:
        result_keys.append(step)
        result_keys.append(f"{step}_Retry_Count")

    if is_prov:
        # Standalone flat provisioning fields -- NOT a step+retry-count
        # pair, exactly like the original header list treated them.
        result_keys += [
            'Set Provisioning Channel',
            'Set Provisioning Channel Status',
            'Get Provisioning Channel',
            'Check Provisioning Parameters Status',
        ]
        # NOTE on fail-message re-pairing (see conversion report): the
        # original FTT_Fail_list for this branch had 23 entries but
        # result_list's idx//2 pairing only ever produced 21 distinct pair
        # indices, because these 4 flat values consume only 2 "pairs" worth
        # of index space while the author supplied 4 messages for them. That
        # silently shifted the messages for 'factory_reset',
        # 'Verify_Serial_No_Mismatch' and 'Live_version_Status' by 2 slots
        # (e.g. a real factory-reset failure would have displayed
        # "Fail in Get Provisioning Channel"), and left 2 of the 23 original
        # strings ("...Serial No Mismatch..." / "...Live Version") dead code
        # that could never be selected. Named lookup makes that kind of
        # misalignment structurally impossible, so each step below is given
        # its own correct, sensibly-paired message text instead of
        # replicating the shift.
        fail_messages['Set Provisioning Channel Status'] = 'Fail in Set Provisioning'
        fail_messages['Check Provisioning Parameters Status'] = 'Fail in Check Channel Number'

    elif is_img_prov:
        # Standalone flat fields written by main_function's non-RF IMG
        # provisioning branch (img_provisioning() / check_provisioning_status()).
        # Split the same way every other step in this function already is:
        # raw provisioning DATA (IMG ID, WIREPAS_* parameters, GW_* raw
        # version/identifier strings) goes into meter_info_keys, and
        # pass/fail STATUS columns (the "... Status" suffixed fields, plus
        # the final "IMG Provisioning Status") go into result_keys.
        # fill_missing_fields() then defaults any of these to None
        # (meter_info) / 'fail' (result) if main_function never set them
        # (e.g. provisioning was skipped because an earlier step already
        # failed) -- a raw parameter that was never read shows up as a
        # blank, a status that was never confirmed shows up as an explicit
        # failure, matching the None/'fail' distinction every other field
        # in this function already gets.
        meter_info_keys += [
            "IMG ID", "Gateway ID",
            "WIREPAS_GW_ID",
            "WIREPAS_NODE_ADDRESS", "WIREPAS_GW_KEY_ENC_KEY",
            "WIREPAS_MTR_AUTH_KEY", "WIREPAS_MTR_ENC_KEY",
            "WIREPAS_MTR_BAUD_RATE", "WIREPAS_MTR_DLMS_MODE",
            "WIREPAS_NODE_ROLE", "WIREPAS_ENCRYPTION_KEY",
            "WIREPAS_AUTHENTICATION_KEY", "WIREPAS_NETWORK_ADDRESS",
            "WIREPAS_NETWORK_CHANNEL", "WIREPAS_SINK_ADDRESS",
            "WIREPAS_SIM_SELECTION",
            "WIREPAS_SIM1_PDP_TYPE", "WIREPAS_SIM1_BAND_LOCK",
            "WIREPAS_SIM2_PDP_TYPE", "WIREPAS_SIM2_BAND_LOCK",
            "WIREPAS_MQTT_HOSTNAME", "WIREPAS_MQTT_PORT",
            "WIREPAS_MQTT_USERNAME", "WIREPAS_MQTT_PASSWORD",
            "WIREPAS_RESET_HOUR", "WIREPAS_RESET_MINUTE",
            "WIREPAS_NTP_ADDR", "WIREPAS_TZ_OFFSET_MIN",
            "WIREPAS_KEEPALIVE_INTVL_S", "GW_IMEI",
            "GW_SIM1_IMSI", "GW_SIM1_ICCID",
            "GW_SIM2_IMSI", "GW_SIM2_ICCID",
            "GW_CORE_VER", "GW_MAIN_VER", "GW_SINK_APP_VER",
            "GW_MODEM_FIRMWARE_VER", "GW_METER_LIB_VER",
        ]
        result_keys += [
            "MCT_Test_Status",
            "Set Debug Print Mode",
            "GW_CORE_VER_STATUS", "GW_MAIN_VER_STATUS",
            "GW_SINK_APP_VER_STATUS", "GW_MODEM_FIRMWARE_VER_STATUS",
            "GW_METER_LIB_VER_STATUS", "PROVISIONING_STATUS",
        ]
        fail_messages['MCT_Test_Status'] = 'Fail in MCT'
        fail_messages['PROVISIONING_STATUS'] = 'Fail in IMG Provisioning'

    # factory_reset is placed here (rather than grouped with the other two
    # closing steps below) because that's where main_function actually runs
    # it -- right before the 4g/TN IPv6 block, not after it.
    # result_keys.append('factory_reset')
    # result_keys.append('factory_reset_Retry_Count')

    # if is_4g_tn:
    if is_4g:
        # Raw IPv6-mode GPRS protocol values read back for the periodic-push
        # and event-push channels (4g + TN only) -- same
        # data/status split as the GPRS_Protocol_Value field above.
        # Placed right after factory_reset to mirror main_function's actual
        # execution order (factory reset runs, then this IPv6 block).
        meter_info_keys += ['Active_Sim','SIM_NUM','APN','IMEI','Signal_Strength','Periodic_Push_IPV6', 'Periodic_Push_Interval', 'Event_Push_IPV6']
        for step in ('Check_GPRS_Connection','Set_Periodic_Push_IPV6', 'Get_Periodic_Push_IPV6',
                     'Set_Periodic_Push_Interval', 'Get_Periodic_Push_Interval',
                     'Set_Event_Push_IPV6', 'Get_Event_Push_IPV6'):
            result_keys.append(step)
            result_keys.append(f"{step}_Retry_Count")
        fail_messages['Check_GPRS_Connection'] =  'Fail in Check GPRS Connection'
        fail_messages['Set_Periodic_Push_IPV6'] =  'Fail in Set Periodic Push IPV6'
        fail_messages['Get_Periodic_Push_IPV6'] = 'Fail in Get Periodic Push IPV6'
        fail_messages['Set_Periodic_Push_Interval'] =  'Fail in Set Periodic Push Interval'
        fail_messages['Get_Periodic_Push_Interval'] = 'Fail in Get Periodic Push Interval'
        fail_messages['Set_Event_Push_IPV6'] = 'Fail in Set Event Push IPV6'
        fail_messages['Get_Event_Push_IPV6'] = 'Fail in Get Event Push IPV6'
        

    meter_info_keys += ['OVER_ALL_RESULT']

    for step in ('factory_reset','Verify_Serial_No_Mismatch', 'Live_version_Status'):
        result_keys.append(step)
        result_keys.append(f"{step}_Retry_Count")

    return meter_info_keys, result_keys, fail_messages


def build_log_entry(mac, meter_info, test_result, bookName, fileName, com_port=None, provisioning_reason=''):
    """Bundle one port's results into a single dictionary instead of the
    old positional 5-item list [mac, MeterInfo, result_list, bookName,
    fileName]. Keys are self-describing, and com_port travels with the
    entry so run() can key result_dict by COM port without needing a
    second parallel structure.

    provisioning_reason is deliberately kept OUTSIDE meter_info/test_result:
    add_log_xlsc() writes every key of those two dicts as its own Excel
    column, so it's the only way to hand the popup summary a free-text
    provisioning failure reason without it also showing up as a new
    "PROVISIONING_REASON" column in the log workbook."""
    return {
        'mac': mac,
        'meter_info': meter_info,
        'result': test_result,
        'bookName': bookName,
        'fileName': fileName,
        'com_port': com_port,
        'provisioning_reason': provisioning_reason,
    }


def build_fail_messages(com_port, test_result, fail_message_lookup):
    """Named-key replacement for the old
    `["COM Port {}: {}".format(FTT_Fail_list[idx], com_port) for idx in
    fail_indexes]` pattern, where fail_indexes = [idx // 2 for idx enumerate
    result_list if value == 'fail']. There is no positional index to keep
    in sync with result_list any more, so a step's failure text can never
    attach to the wrong step (see get_ftt_field_templates() docstring for
    the specific positional-shift bug this eliminates for the provisioning
    branch). Retry-count keys never match (their values are strings like
    '1'/'3', never 'fail'), so they're naturally skipped here exactly like
    they were skipped by the old `if result == 'fail'` scan.

    The message FORMAT itself intentionally reproduces the original's
    swapped-argument bug -- the original was
    `"COM Port {}: {}".format(FTT_Fail_list[idx], com_port)`, which renders
    as "COM Port <message>: <com_port>" instead of the sane
    "COM Port <com_port>: <message>". Preserved verbatim; see conversion
    report.

    MCT_Test_Status/PROVISIONING_STATUS (and the GW_*_STATUS sub-checks
    check_provisioning_status() writes alongside PROVISIONING_STATUS -- a
    single failing sub-check is what makes PROVISIONING_STATUS 'fail' in
    the first place) are skipped here: the summary popup shows MCT and IMG
    Provisioning as their own pass/fail rows (with their own reason), so
    folding any of this failure text into the FTT message list too would
    just show the same provisioning failure twice, once under FTT and once
    under its own row."""
    steps_with_their_own_summary_row = {
        'MCT_Test_Status', 'PROVISIONING_STATUS',
        'GW_CORE_VER_STATUS', 'GW_MAIN_VER_STATUS', 'GW_SINK_APP_VER_STATUS',
        'GW_MODEM_FIRMWARE_VER_STATUS', 'GW_METER_LIB_VER_STATUS',
    }
    messages = []
    for step_key, value in test_result.items():
        if step_key in steps_with_their_own_summary_row:
            continue
        if value == 'fail':
            text = fail_message_lookup.get(step_key, f"Fail in {step_key}")
            messages.append("COM Port {}: {}".format(text, com_port))
    return messages


# Sentinel values written into the log when a step's real data was never
# recorded (e.g. a retry loop's 3 attempts all raised an exception, so the
# loop exited without ever appending/assigning anything for that step).
# A missing result step reads as 'fail', never a silent 'pass' -- untested
# must never look identical to tested-and-passed.
NOT_TESTED_METER_VALUE = None
NOT_TESTED_RESULT_VALUE = 'fail'


def fill_missing_fields(entry, meter_info_keys, result_keys):
    """Ensure every field in meter_info_keys/result_keys exists on `entry`,
    filling in NOT_TESTED_* defaults for anything main_function never got to
    write. This is what prevents the Excel "column mismatch" the old
    list-based script suffered from: several retry loops in main_function
    have NO fallback append on their except branch, so if all 3 attempts
    raised an exception the loop exits having appended nothing at all for
    that step -- under the old positional writer this silently shifted
    every later column. add_log_xlsc() already writes by header *name*
    rather than position, but a field simply absent from the dict would
    still leave a blank, unexplained cell. Calling this right before
    build_log_entry()/queuing guarantees every row has a value under every
    header.

    'Verify_Serial_No_Mismatch' needs NO special exclusion here (unlike the
    PCT reference's 'Meter PCB Serial Numebr Check'): the original
    main_function already writes an explicit *optimistic* 'pass' placeholder
    into this field unconditionally (both branches of the final
    "if check_port == LIVE_VERSION" block set it), before main_function
    returns -- it is never left absent. run()'s serial-number re-entry
    check later overwrites it with the real verdict. Since it's always
    already present by the time fill_missing_fields()/build_fail_messages()
    run at the end of main_function, there's no risk of a premature 'fail'
    default being read as a genuine failure."""
    for key in meter_info_keys:
        entry['meter_info'].setdefault(key, NOT_TESTED_METER_VALUE)
    for key in result_keys:
        entry['result'].setdefault(key, NOT_TESTED_RESULT_VALUE)


def addDefaultFttLog(bookName,fileName, toolName = 'rf_ftt', rf_prov = 1, project = 'wb', manufacturing_name_enable = True):
    """Create the log workbook (if missing) and write its header row.
    Headers come from get_ftt_field_templates(), so they always match the
    keys main_function() will populate -- no more 4 hand-written branch
    header lists (MeterInfo/result) to keep in sync with main_function's
    append order by convention alone."""
    if False == verify_log_xlsc(bookName,fileName):
        print("xlsx file for log not found. creating one to store test report")

        # meter_type is intentionally not passed through here -- the
        # original addDefaultFttLog never took a meter_type argument either,
        # and its MeterInfo header list was identical regardless of
        # meter_type (see get_ftt_field_templates() docstring).
        meter_info_keys, result_keys, _ = get_ftt_field_templates(None, toolName, rf_prov, project, manufacturing_name_enable)

        wb = openpyxl.load_workbook(bookName)
        sheet = wb[fileName]

        headers = ['MAC_ADDR', 'Index'] + meter_info_keys + result_keys
        for col_idx, header in enumerate(headers, start=1):
            sheet.cell(row=1, column=col_idx).value = header

        wb.save(bookName)
        print("New xlsx file created with headers")
        logging.info("New xlsx file created with headers")

def enterSrNum_ftt(PROJECT):
    if (PROJECT.lower() == "gomati") or (PROJECT.lower() == "saryu"):
        while(1):
            # scanning of barcode and taking serial no input
            try:
                serial_num = ''
                serial_num = input("Enter Meter Serial Num(ex-PO12345678): ")
                # match=re.match(r'^[a-zA-Z]{4}\d{6}$',serial_num)
                match = re.match(r'^PO\d{8}$', serial_num)
                # print "type of serial_num = ",type(serial_num)
                if  match:
                    last_EIGHT_digits=serial_num[-8:]
                    return last_EIGHT_digits
                else:
                    raise ValueError("invalid  format of serial num please  enter in this format  (ex-PO12345678)")
            except ValueError as e:
                print(f"Error during get serial number at start: {str(e)}")
                logging.error(f"Error during get serial number at start: {str(e)}")
    elif((PROJECT.lower() == "manipur")):
        while(1):
            # scanning of barcode and taking serial no input
            try:
                serial_num = ''
                serial_num = input("Enter Meter Serial Num(ex-MN1P232345): ")
                # match=re.match(r'^[a-zA-Z]{4}\d{6}$',serial_num)
                match = re.match(r'^MN1P\d{6}$', serial_num)
                # print "type of serial_num = ",type(serial_num)
                if  match:
                    last_six_digits=serial_num[-6:]
                    return last_six_digits
                else:
                    raise ValueError("invalid  format of serial num please  enter in this format  (ex-MN1P232345)")
            except ValueError as e:
                print(f"Error during get serial number at start: {str(e)}")
                logging.error(f"Error during get serial number at start: {str(e)}")
    elif((PROJECT.lower() == "wb")):
        while(1):
            # scanning of barcode and taking serial no input
            try:
                serial_num = ''
                serial_num = input("Enter Meter Serial Num(ex-PPL1234567): ")  # wb requirement to change PLL from PO
                # match=re.match(r'^[a-zA-Z]{4}\d{6}$',serial_num)
                match = re.match(r'^PPL\d{7}$', serial_num)
                # print "type of serial_num = ",type(serial_num)
                if  match:
                    last_Seven_digits=serial_num[-7:]
                    return last_Seven_digits
                else:
                    raise ValueError("invalid  format of serial num please  enter in this format  (ex-PPL1234567)")
            except ValueError as e:
                print(f"Error during get serial number at start: {str(e)}")
                logging.error(f"Error during get serial number at start: {str(e)}")
    elif((PROJECT.lower() == "tn")):
        while(1):
            # scanning of barcode and taking serial no input
            try:
                serial_num = ''
                serial_num = input("Enter Meter Serial Num(ex-PO12345678): ")
                # match=re.match(r'^[a-zA-Z]{4}\d{6}$',serial_num)
                match = re.match(r'^PO\d{8}$', serial_num)
                # print "type of serial_num = ",type(serial_num)
                if  match:
                    last_EIGHT_digits=serial_num[-8:]
                    return last_EIGHT_digits
                else:
                    raise ValueError("invalid  format of serial num please  enter in this format  (ex-PO12345678)")
            except ValueError as e:
                print(f"Error during get serial number at start: {str(e)}")
                logging.error(f"Error during get serial number at start: {str(e)}")
    elif((PROJECT.lower() == "others")):
        while(1):
            # scanning of barcode and taking serial no input
            try:
                serial_num = ''
                serial_num = input("Enter Meter Serial Num(ex-LR12345678 or any other identifier): ")
                # match=re.match(r'^[a-zA-Z]{4}\d{6}$',serial_num)
                # match = re.match(r'^PL\d{8}$', serial_num)
                # print "type of serial_num = ",type(serial_num)
                if len(serial_num) == 10:
                    last_EIGHT_digits=serial_num[-8:]
                    return last_EIGHT_digits
                else:
                    raise ValueError("invalid  format of serial num please  enter in this format  (ex-LR12345678 or any other identifier)")
            except ValueError as e:
                print(f"Error during get serial number at start: {str(e)}")
                logging.error(f"Error during get serial number at start: {str(e)}")
    elif (PROJECT.lower() == "tata_delhi"):
        while(1):
            # scanning of barcode and taking serial no input
            try:
                serial_num = ''
                data = input("Enter Meter Serial Num(ex- 'TPDDL || 1126 || PO20000002'): ")
                logging.info(f"Data received for serial number: {data}")
                # match=re.match(r'^[a-zA-Z]{4}\d{6}$',serial_num)
                serial_num = data.split("||")[-1].strip()
                match = re.match(r'^PO\d{8}$', serial_num)
                # print "type of serial_num = ",type(serial_num)
                if  match:
                    last_EIGHT_digits=serial_num[-8:]
                    return last_EIGHT_digits
                else:
                    raise ValueError("invalid  format of serial num please  enter in this format  (ex- 'TPDDL || 1126 || PO20000002')")
            except ValueError as e:
                print(f"Error during get serial number at start: {str(e)}")
                logging.error(f"Error during get serial number at start: {str(e)}")
    else:
        raise ValueError("invalid  format of Project name selected in config file please  enter in this format  (ex-gomati or saryu or manipur or wb or tata_delhi)")

global abort_threads

def rf_run_provisioning_worker(queue, ser_initilizer, provisioning_param):
    try:
        nic_parameters_data, prov_success = provision_nic_parameters.run_provisioning(ser_initilizer, provisioning_param)
        queue.put((nic_parameters_data, prov_success))
    except Exception as e:
        logging.exception(
            f"Provisioning worker failed for "
            f"{provisioning_param.get('serial_port')}"
        )
        queue.put(({}, False))

# NOTE: this used to be named run_provisioning_with_timeout(), same as the
# IMG-flow function further down (which takes different args: just
# (provisioning_param, timeout_seconds)). Python keeps only the LAST def
# with a given name at module scope, so that IMG version silently shadowed
# this one -- rf_meter_provisioning()'s call below was actually invoking
# the IMG version with mismatched args (`ser` bound to its
# `provisioning_param`, and this function's `provisioning_param` dict bound
# to its `timeout_seconds`), which then failed inside Thread.join() trying
# to compare that dict against 0 ("'>' not supported between instances of
# 'int' and 'dict'"). Renamed so the two can no longer collide.
def rf_run_provisioning_with_timeout(ser_initilizer, provisioning_param, timeout_seconds=5):
    queue = Queue()
    print(type(ser_initilizer))
    print(ser_initilizer)
    stop_event = threading.Event()
    provisioning_param = dict(provisioning_param, stop_event=stop_event)
    p = Thread(target=rf_run_provisioning_worker, args=(queue, ser_initilizer, provisioning_param), daemon=True)

    p.start()
    # p.join(timeout_seconds)

    p.join(timeout_seconds)
    if p.is_alive():
        # The worker shares `ser` with main_function. Left running, it kept
        # writing provisioning challenges to the port, so the factory reset
        # that follows failed with "write timeout" and main_function overran
        # run()'s thread join. Tell it to stop and wait for it to let go.
        logging.warning(f"RF provisioning timed out after {timeout_seconds}s for {provisioning_param.get('serial_port')}, cancelling")
        stop_event.set()
        p.join(15)
        if p.is_alive():
            logging.error(f"RF provisioning worker still alive after cancel for {provisioning_param.get('serial_port')}")
        try:
            ser_initilizer.reset_input_buffer()
            ser_initilizer.reset_output_buffer()
        except Exception as e:
            logging.warning(f"Could not flush serial buffers after provisioning cancel: {e}")
        return {}, False

    if not queue.empty():
        return queue.get()
    else:
        return {}, False
    # return queue.get()

    # # Completed normally
    # if not queue.empty():
    #     return queue.get()
    # else:
    #     return {}, False

def rf_meter_provisioning(ser, com_port):

    # if enable_tunnel_mode:
    nic_parameters_data = {}
    prov_sucess = False
    prov_channel = None
    param_data = {
        'serial_port': com_port,
        'encryption_key': "e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1",
        'authentication_key': "e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1",
        'network_address': "12238529",
        'network_channel': "1",
        'node_address': "1"
    }
    # nic_parameters_data, prov_sucess = provision_nic_parameters.run_provisioning(param_data)
    logging.info(f"Provisioning started for com: {com_port}\n parameters: {param_data}")
    nic_parameters_data, prov_sucess = rf_run_provisioning_with_timeout(ser, param_data)
    logging.info(f"COM: {com_port}, Provisioning result: {nic_parameters_data}, status: {prov_sucess}")
    # prov_channel = nic_parameters_data.get('WIREPAS_NETWORK_CHANNEL', None)
    print(nic_parameters_data, prov_sucess)
    if len(nic_parameters_data) > 0:
        prov_channel = nic_parameters_data.get('WIREPAS_NETWORK_CHANNEL', None)
    return prov_sucess, prov_channel


DEFAULT_BAUDRATE = 9600

def run_provisioning_worker(result_queue, provisioning_param):
    nic_parameters_data, prov_success, summary = {}, False, ""
    try:
        nic_parameters_data, prov_success, summary = run_provisioning(provisioning_param)
        result_queue.put((nic_parameters_data, prov_success, summary))
    except Exception as e:
        summary = str(e)
        result_queue.put((nic_parameters_data, prov_success, summary))

def run_provisioning_with_timeout(provisioning_param, timeout_seconds=70):
    result_queue = queue.Queue()
    t = threading.Thread(target=run_provisioning_worker, args=(result_queue, provisioning_param), daemon=True)
    t.start()
    t.join(timeout_seconds)
    if t.is_alive():
        # Can't force-kill a thread. It keeps running in the background using `ser`;
        # we just stop waiting on it and report timeout to the caller.
        return {}, False, "TIMEOUT"
    if not result_queue.empty():
        return result_queue.get()
    else:
        return {}, False, "NO_RESPONSE"

def img_provisioning(data, img_id, gateway_id, com_port, com_ser ,baudrate = DEFAULT_BAUDRATE ):
    serial_port = com_port
    project = data.get('BROKER', '')
    reboot_time = str(data.get('REBOOT_TIME_SEC', "300"))
    # reboot_time = '0'
    network_channel = str(data.get("NETWORK_CHANNEL", "1"))
    # network_channel = "2"

    logging.info(f"Port {serial_port}, IMG Provisioning Started")

    provisioning_param = {}
    nic_parameters_data = {}
    prov_sucess = False
    summary = ""
    reason = ""
    print("\nStarting IMG Provisioning....")
    print(f"\nProject: {project}")
    try:
        user = ""
        password = ""
        hostname = ""
        ntp_addr = ""
        if project.upper() == "GOMATI":
            user = "Gomati-Broker"
            password = "G0m@ti-Br0k3r!2024$"
            # sync_apn = "polarisgomati"
            hostname = "broker.gomatimvvnl.in"
            ntp_addr = "wnms.gomatimvvnl.in"
        elif project.upper() == "SARYU":
            user = "Saryu-Broker"
            password = "S@ryu-Br0k3r!#V&2420$"
            # sync_apn = "polarissaryu"
            hostname = "broker.saryumvvnl.in"
            ntp_addr = "wnms.saryumvvnl.in"
        elif project.upper() == "MANIPUR":
            user = "sangaibroker"
            password = "V3aSLGXkUy4o1CIBs"
            # sync_apn = "polarissangai"
            hostname = "broker.sangaimspdcl.in"
            ntp_addr = "wnms.sangai.polarisgrids.com"
        elif project.upper() == "WB":
            user = "wbsedcl"
            password = "nU4Eq5rE2e"
            # sync_apn = "polarissangai"
            hostname = "broker.hooghlywbsedcl.in"
            ntp_addr = "wnms.hooghlywbsedcl.in"
        elif project.upper() == "TN":
            user = "TNPDCL-Broker"
            password = "oJBUnxKCqPjXoWgCz3Jwojce"
            # sync_apn = "polarissangai"
            hostname = "broker.private.tnpdcl.in"
            ntp_addr = "wnms.private.tnpdcl.in"
        elif project.upper() == "TATA_DELHI":
            user = "TNPDCL-Broker"
            password = "oJBUnxKCqPjXoWgCz3Jwojce"
            # sync_apn = "polarissangai"
            hostname = "broker.private.tnpdcl.in"
            ntp_addr = "wnms.private.tnpdcl.in"
        
        else:
            return {}, False, "No broker match"
        
        print("Starting provisioning script")
        provisioning_param = {
            "com_ser": com_ser,
            "serial_port": serial_port,
            "baudrate": data.get("baudrate", ''),
            "reboot_time": reboot_time,
            "encryption_key": "e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1",
            "authentication_key": "e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1",
            "network_address": "12238529",
            "network_channel": network_channel,
            "node_address": "1",
            "sink_address": img_id,
            "node_role": None,
            "gateway_id": gateway_id,
            "gw_key_enc_key": None,
            "mtr_auth_key": None,
            "mtr_enc_key": None,
            "mtr_mr_secret": None,
            "mtr_us_secret": None,
            "mtr_fu_secret": None,
            "mtr_baud_rate": None,
            "mtr_dlms_mode": None,
            "sim1_apn": None,
            "sim1_username": None,
            "sim1_password": None,
            "sim1_pdp_type": None,
            "sim1_pin": None,
            "sim1_puk": None,
            "sim1_band_lock": None,
            "sim2_apn": None,
            "sim2_username": None,
            "sim2_password": None,
            "sim2_pdp_type": None,
            "sim2_pin": None,
            "sim2_puk": None,
            "sim2_band_lock": None,
            "mqtt_hostname": hostname,
            "mqtt_port": "1883",
            "mqtt_username": user,
            "mqtt_password": password,
            "mqtt_unsecure": "true",
            "reset_hour": "21",
            "reset_minute": "30",
            "ntp_addr": ntp_addr,
            "tz_offset_min": "330",
            "keepalive_interval": "300",
            "sim_selection": "dual_prefer_sim1"
            }
        
        logging.info(f"Port {provisioning_param}, input")
        
        nic_parameters_data, prov_sucess, summary= run_provisioning_with_timeout(provisioning_param)   

        if prov_sucess:
            
            logging.info(f"Port {serial_port}, IMG Provisioning Successfully Completed")
        else:
            reason = summary
            print(f"Command failed with return code: {prov_sucess}")
            logging.info(f"Port {serial_port}, IMG Provisioning Failed")

        logging.info(f"Port {serial_port}, IMG Provisioning: {nic_parameters_data}")
        return nic_parameters_data, prov_sucess, reason
    except Exception as e:
        print(str(e))
        # show_results_popup("Fail", serial_port)
        logging.error(f"Port {serial_port}, Error during IMG Provisioning, Error: {e}")
    return nic_parameters_data, prov_sucess, "Error in Provisioning"

def check_provisioning_status(provision_data, serial_config_json):
    overall_result = "pass"
    reason = ""
    status_dict = {}
    sim2_id = ""
    sim1_id = ""

    if provision_data.get('GW_CORE_VER', '') == serial_config_json['GW_CORE_VER']:
        status_dict['GW_CORE_VER_STATUS'] = "pass"
    else:
        status_dict['GW_CORE_VER_STATUS'] = "fail"
        overall_result = "fail"
        reason = "GW_CORE_VER not match"
    
    if provision_data.get('GW_MAIN_VER', '') == serial_config_json['GW_MAIN_VER']:
        status_dict['GW_MAIN_VER_STATUS'] = "pass"
        # overall_result = True
    else:
        status_dict['GW_MAIN_VER_STATUS'] = "fail"
        overall_result = "fail"
        reason = "GW_MAIN_VER not match"
    
    if provision_data.get('GW_SINK_APP_VER', '') == serial_config_json['GW_SINK_APP_VER']:
        status_dict['GW_SINK_APP_VER_STATUS'] = "pass"
        # overall_result = True
    else:
        status_dict['GW_SINK_APP_VER_STATUS'] = "fail"
        overall_result = "fail"
        reason = "GW_SINK_APP_VER not match"
    
    if provision_data.get('GW_MODEM_FIRMWARE_VER', '') == serial_config_json['GW_MODEM_FIRMWARE_VER']:
        status_dict['GW_MODEM_FIRMWARE_VER_STATUS'] = "pass"
        # overall_result = True
    else:
        status_dict['GW_MODEM_FIRMWARE_VER_STATUS'] = "fail"
        overall_result = "fail"
        reason = "GW_MODEM_FIRMWARE_VER not match"
    
    if provision_data.get('GW_METER_LIB_VER') == serial_config_json['GW_METER_LIB_VER']:
        status_dict['GW_METER_LIB_VER_STATUS'] = "pass"
        # overall_result = True
    else:
        status_dict['GW_METER_LIB_VER_STATUS'] = "fail"
        overall_result = "fail"
        reason = "GW_METER_LIB_VER not match"
    

    if serial_config_json.get('BROKER', '').lower() == 'manipur':
        if 'sangai' not in  provision_data.get('WIREPAS_MQTT_USERNAME', '').lower():
            overall_result = "FAIL"
            reason = "Broker not found in provisioning"
    elif serial_config_json.get('BROKER', '').lower() == 'wb':
        if 'wbsedcl' not in  provision_data.get('WIREPAS_MQTT_USERNAME', '').lower():
            overall_result = "FAIL"
            reason = "Broker not found in provisioning"
    else:
        if (serial_config_json.get('BROKER', '').lower() not in  provision_data.get('WIREPAS_MQTT_USERNAME', '').lower()):
            overall_result = "FAIL"
            reason = "Broker not found in provisioning"

    if 'GW_SIM2_ICCID' in provision_data.keys():
        sim2_id = provision_data.get("GW_SIM2_ICCID", '')
    if 'GW_SIM1_ICCID' in provision_data.keys():
        sim1_id = provision_data.get("GW_SIM1_ICCID", '')
    
    

    if (sim1_id != '') and (sim2_id != ''):
        # overall_result = "pass"
        status_dict['PROVISIONING_STATUS'] = "pass"
        if len(provision_data['GW_SIM1_ICCID']) > 19:
            provision_data['GW_SIM1_ICCID'] = provision_data['GW_SIM1_ICCID'][:19]
        
        summary = wirepas_provisioning.print_provisioning_summary(provision_data)
        print("Provisioning Status: \n",summary)
        print(Fore.GREEN + "✅ IMG Provisioning Successfully Completed!")
        print(Style.RESET_ALL)
    else:
        overall_result = "FAIL"
        status_dict['PROVISIONING_STATUS'] = "FAIL"
        reason = "sim not found in img provisioning"
        summary = wirepas_provisioning.print_provisioning_summary(provision_data)
        print("Provisioning Status: \n",summary)
        print(Fore.RED + "❌ IMG Provisioning Failed! SIM not found")
        print(Style.RESET_ALL)
        # return result_dict, overall_result

    return status_dict, overall_result, reason, provision_data

class StoppableThread(Thread):
    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

def main_function(data_dict, com_port, meter_serial_num, input_pcb_no, input_nic_pcb_no ,result_queue, abort_flag, result_log):
    # ------------------------------------------------------------------
    # FLOW CHANGE: this used to require a pre-computed `rtt_results` dict
    # (built by a separate STAGE 1 in img_ftt_provisioning.py that read the
    # PCB serial number via a raw byte-array command, then ran MCT, then
    # RTT, all *before* FTT was even allowed to start). That meant the PCB
    # serial number was read from hardware twice: once via raw bytes for
    # that pre-check, and again here via the real cases.Get_pcb_serial_num()
    # command as part of FTT's own "Get PCB Serial number" step.
    #
    # Now: FTT starts directly. The PCB serial number is read exactly once,
    # via the same command-based cases.Get_pcb_serial_num() call FTT always
    # used internally, moved up to run right after the com-port liveness
    # check (see below). For 'img' tool types, RTT is checked immediately
    # after that single read, using that same serial number -- no separate
    # hardware read, no separate pre-stage. Non-img tool types skip RTT
    # entirely, same as before. If RTT fails, this function aborts exactly
    # like the old pre-check gate did (message queued, abort_flag set, no
    # log entry built) -- run() below still recognizes that as an aborted
    # port via the same "port missing from temp_result_dict" path it always
    # used, so nothing downstream needed to change for that part.
    # ------------------------------------------------------------------
    logging.info(f"FTT and RTT Test Start for com: {com_port}")
    try:
        # ser = None
        ser = serial.Serial(com_port, baudrate=9600, timeout=10)
        if not ser:
            msg = ["com port is unable to open: {}".format(com_port)]
            result_queue.put((com_port.lower(), msg))
            return
        portID=4
        network_api = NetworkAPI(ser, portID, "irda")
        cases = TestCasePCTMCT(ser,portID,data_dict.get("RETRIES", 4), data_dict.get("NIC_PCB_LENGTH", 27))
        is_excel_file_present = True
        toolName = data_dict.get("TOOL_TYPE", 'FTT')
        mct_applicable = any(t in toolName.lower() for t in ('img', '4g', 'rf'))
        mac = get_system_mac_address(toolName)
        meter_info = {}
        test_result = {}
        # Kept out of test_result on purpose -- see build_log_entry()'s
        # provisioning_reason docstring.
        provisioning_fail_reason = ''
        result_save=[]
        ResultFinal=''
        meter_type = data_dict.get("METER_TYPE", "Garud_1PH").lower()
        bookName = meter_type.title()+"_"+toolName.upper()+"_"+"{}".format(str(data_dict.get("FTT_TEST_STATION", "")))+"_LOG.xlsx"
        # bookName = meter_type+"_"+toolName+"_LOG.xlsx"
        fileName = toolName.upper()+"_DATA_LOG"
        starttime = datetime.datetime.now()
        print ("\nStartTime:",starttime, com_port)
        end_bytes = bytes([0xAA, 0xBB, 0xCC, 0xDD])
        START_ADDRESS = 0x0100
        METER_ADDRESS = "255.255.255.255"

        Date_time=datetime.datetime.now()
        meter_info['Date_time'] = Date_time
        meter_info['Original_Serial_Number'] = str(meter_serial_num)
        addDefaultFttLog(bookName,fileName, toolName.lower(), data_dict.get('rf_prov', 1), data_dict.get('PROJECT', 'wb'), is_manufacturing_name_enabled(data_dict))

        # Field templates for this toolName/rf_prov combination -- single
        # source of truth that replaces the old hand-maintained
        # FTT_Fail_list (which had to stay in perfect positional sync with
        # result_list, via fail_indexes, to produce readable failure text).
        meter_info_keys, result_keys, fail_message_lookup = get_ftt_field_templates(
            meter_type, toolName, data_dict.get('rf_prov', 1), data_dict.get('PROJECT', 'wb'),
            is_manufacturing_name_enabled(data_dict)
        )

        # Check com port status
        retryCnt = 3
        while retryCnt:
            logging.info(f"Check com port is open or not attempt{4-retryCnt}, for com: {com_port}")
            try:
                check_port = cases.get_live_version_val()
                if 'Fail' == check_port:
                    msg = ["com port is unreachable: {}".format(com_port)]
                    # result_queue.append(msg)
                    # result_queue[com_port.lower()] = msg
                    result_queue.put((com_port.lower(), msg))
                    print("ser close for port : {}".format(com_port))
                    logging.error(f"Com port is close, COM: {com_port}")
                    if ser is not None:
                        ser.close()
                abort_flag.set()
                retryCnt = 0
            except Exception as e:
                print(e)
                logging.info(f"Error to check com port status attempt{4-retryCnt}, error: {str(e)}, for com: {com_port}")
                retryCnt -= 1

            # print("ser closed for port : {}".format(com_port))
            # return

        meter_info['Live_version'] = str(check_port)  #live version

        # Get PCB Serial number -- moved up from its old position (after
        # Verify Energy) to be the first real test step, so its single
        # command-based hardware read (cases.Get_pcb_serial_num(), NOT the
        # raw byte-array read img_ftt_provisioning.py used to do
        # separately) can also feed the RTT check right below, instead of
        # each script reading the PCB serial number independently.
        retryCnt = 3
        Pcb_serial_no = None
        while (retryCnt):
            logging.info(f"Get PCB Serial number for com: {com_port}, attempt: {4-retryCnt}")
            try:
                Pcb_serial_no = cases.Get_pcb_serial_num()
                if((str(Pcb_serial_no) == str(input_pcb_no.lower()))  or (str(Pcb_serial_no) == str(input_pcb_no.upper()))):
                    meter_info['Meter_PCB_Serial_No'] = str(Pcb_serial_no)
                    test_result['Get_Meter_PCB_Serial_No'] = 'pass'
                    logging.info(f"pcb serial number for com: {com_port}, pcb serial numbr: {Pcb_serial_no}")
                else:
                    meter_info['Meter_PCB_Serial_No'] = str(Pcb_serial_no)
                    test_result['Get_Meter_PCB_Serial_No'] = 'fail'
                    logging.info(f"fail in get pcb serial number for com: {com_port}, response: {Pcb_serial_no}")
                test_result['Get_Meter_PCB_Serial_No_Retry_Count'] = '1'
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error to get pcb serial number for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1



        if mct_applicable:
            if not Pcb_serial_no:
                logging.error(f"MCT Test Fail for com: {com_port} -- PCB serial number unavailable, all read attempts failed")
                result_queue.put((com_port.lower(), ["RTT Test Failed: PCB Serial Number unavailable"]))
                abort_flag.set()
                ser.close()
                return
            # mct_status = rtt_data.rtt_run(Pcb_serial_no, data_dict.get("MCT_PREVIOUS", 15), meter_type, toolName)
            mct_status = db_connect.fetch_by_pcb_serial(Pcb_serial_no, toolName.lower())
            print(mct_status)
            if not mct_status:
                test_result['MCT_Test_Status'] = 'fail'
                logging.info(f"MCT Test Fail for com: {com_port}")
                result_queue.put((com_port.lower(), ["MCT Test Failed"]))
                abort_flag.set()
                ser.close()
                return
            logging.info(f"MCT Test Pass for com: {com_port}")
            test_result['MCT_Test_Status'] = 'pass'

        # verify serial number
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Verify Serail Number Attempt: {4-retryCnt}, for com: {com_port}")
            try:
                sr_num = cases.Verify_Serial_number()
                if 'Fail' in sr_num:
                    meter_info['Duplicate_Serial_No'] = 'Fail'
                else:
                    meter_info['Duplicate_Serial_No'] = str(sr_num)
                Sr_num2=cases.Verify_Serial_number2()
                if Sr_num2.get('Result') == 'Pass':
                    test_result['get_duplicate_serial_num'] = 'pass'
                else:
                    test_result['get_duplicate_serial_num'] = 'fail'
                test_result['get_duplicate_serial_num_Retry_Count'] = '1'
                logging.info(f"for com: {com_port} Serial Number is verified")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in verify serial Numebr com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1

        # Check Calibration unlock status
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Calibration Unlock start Attempt: {4-retryCnt}, for com: {com_port}")
            try:
                calib_unlock=cases.Calibration_unLock()
                if calib_unlock.get('Result') == 'Pass':
                    test_result['Calibration_Unlock'] = 'pass'
                else:
                    test_result['Calibration_Unlock'] = 'fail'
                test_result['Calibration_Unlock_Retry_Count'] = '1'
                logging.info(f"Sucessfully Calibration unlock for com: {com_port}, response: {calib_unlock}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in Calibarion unlock for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1

        # Set Meter Serial Number
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Set Meter Serial for com: {com_port}, attempt: {4-retryCnt}")
            try:
                set_serial_num=cases.Set_Meter_serial_number(int(meter_serial_num))
                if set_serial_num.get('Result') == 'Pass':
                    test_result['set_original_Meter_Serial_No'] = 'pass'
                else:
                    test_result['set_original_Meter_Serial_No'] = 'fail'
                test_result['set_original_Meter_Serial_No_Retry_Count'] = '1'
                logging.info(f"Sucessfully set meter serial number for com: {com_port}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in set meter serial numebr for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1

        # Again verify serial number
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Again verify Meter Serial for com: {com_port}, attempt: {4-retryCnt}")
            try:
                sr_num = cases.Verify_Serial_number()
                if (sr_num == 'Fail'):
                    # BUG preserved verbatim from the original script: this
                    # sets a *capital* 'Fail', not lowercase 'fail', so it
                    # never counts as a failure anywhere that checks
                    # `== 'fail'` (build_fail_messages / OVER_ALL_RESULT).
                    test_result['get_serial_num_after_set'] = 'Fail'
                else:
                    if(sr_num == str(meter_serial_num.lstrip('0'))):
                        test_result['get_serial_num_after_set'] = 'pass'
                    else:
                        test_result['get_serial_num_after_set'] = 'fail'
                test_result['get_serial_num_after_set_Retry_Count'] = '1'
                logging.info(f"Sucessfully verify meter serial number for com: {com_port}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in again verigy meter serial numebr for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1

        # Calib Lock
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Calibration lock start Attempt: {4-retryCnt}, for com: {com_port}")
            try:
                calib_lock=cases.Calibration_Lock()
                if calib_lock.get('Result') == 'Pass':
                    test_result['Calib_Lock'] = 'pass'
                else:
                    test_result['Calib_Lock'] = 'fail'
                test_result['Calib_Lock_Retry_Count'] = '1'
                logging.info(f"Sucessfully Calibration lock for com: {com_port}, response: {calib_lock}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in Calibarion lock for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1

        # Check Calib Lock Status
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Check Calibration status start Attempt: {4-retryCnt}, for com: {com_port}")
            try:
                calib_lock_status=cases.Calibration_status()
                meter_info['Check_Calib_Lock_Status_Result'] = calib_lock_status.get('value', None)
                if calib_lock_status.get('Result') == 'Pass':
                    test_result['Check_Calib_Lock_Status'] = 'pass'
                else:
                    test_result['Check_Calib_Lock_Status'] = 'fail'
                test_result['Check_Calib_Lock_Status_Retry_Count'] = '1'
                logging.info(f"Calibration lock status for com: {com_port}, response: {calib_lock_status}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in Calibarion lock status for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    meter_info['Check_Calib_Lock_Status_Result'] = None
                    test_result['Check_Calib_Lock_Status'] = 'fail'
                    test_result['Check_Calib_Lock_Status_Retry_Count'] = '3'

        # Get Meter Address
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Get meter address for com: {com_port}, attempt: {4-retryCnt}")
            try:
                Meter_address=cases.get_Meter_address(str(METER_ADDRESS))
                if 'Fail' in Meter_address:
                    meter_info['Original_meter_address'] = 'Fail'
                else:
                    meter_info['Original_meter_address'] = str(Meter_address)
                meter_addr2=cases.get_Meter_address2(str(METER_ADDRESS),int(sr_num))
                if meter_addr2.get('Result') == 'Pass':
                    test_result['Verify_meter_address'] = 'pass'
                else:
                    test_result['Verify_meter_address'] = 'fail'
                test_result['Verify_meter_address_Retry_Count'] = '1'
                logging.info(f"Sucessfully get meter address for com: {com_port}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error to get meter address for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1

        # Check DLMS Activation
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Check DLMS Actiavation for com: {com_port}, DLMS Type: {data_dict.get('DLMS_TYPE', 'old_dlms').lower()}, attempt: {4-retryCnt}")
            try:
                CHECK_DLMS_ACTIVATION = cases.dlms_Activation_check_value(data_dict.get("DLMS_TYPE", 'old_dlms').lower())
                if CHECK_DLMS_ACTIVATION.get('Result') == 'Pass':
                    test_result['Verify_DLMS_Activation'] = 'pass'
                    logging.info(f"DLMS is actiavte for com: {com_port}")
                else:
                    test_result['Verify_DLMS_Activation'] = 'fail'
                    logging.info(f"DLMS is not actiavte for com: {com_port}")
                test_result['Verify_DLMS_Activation_Retry_Count'] = '1'
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in check DLMS activation for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1

        # Verify Energy
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Verify energy for com: {com_port}, attempt: {4-retryCnt}")
            try:
                clear_energy = cases.Verify_energy()
                logging.info(f"Result of Verify Current: {clear_energy}, for com:{com_port}")
                meter_info['Active_Energy'] = clear_energy.get('energy_value',{}).get('active_energy_imp', None)
                meter_info['Apparent_Energy'] = clear_energy.get('energy_value',{}).get('apparent_energy_imp', None)
                meter_info['Reactive_Energy'] = clear_energy.get('energy_value',{}).get('reactive_energy_imp', None)
                if clear_energy.get('Result').lower() == 'pass':
                    test_result['Verify_Clear_Energy'] = 'pass'
                    logging.info(f"pass in verify energy for com: {com_port}")
                else:
                    test_result['Verify_Clear_Energy'] = 'fail'
                    logging.info(f"fail in verify energy for com: {com_port}")
                test_result['Verify_Clear_Energy_Retry_Count'] = '1'
                retryCnt = 0
            except Exception as e:
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    meter_info['Active_Energy'] = 'None'
                    meter_info['Apparent_Energy'] = 'None'
                    meter_info['Reactive_Energy'] = 'None'
                    test_result['Verify_Clear_Energy'] = 'fail'
                    test_result['Verify_Clear_Energy_Retry_Count'] = '1'
                    logging.error(f"Error in verify energy for com: {com_port}, error: {str(e)}")

        # (PCB serial number is no longer read here -- it's now read once,
        # earlier, right after the com-port liveness check, and reused for
        # both this step's verification and the RTT check. See the block
        # right after "Check com port status" above.)

        # Get NIC Pcb Number
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Get NIC PCB Serial number for com: {com_port}, attempt: {4-retryCnt}")
            try:
                Nic_PCB_no = cases.Nic_PCB_No(data_dict.get("NIC_PCB_SFG_PREFIX", "0000004"), data_dict.get("NIC_PCB_LENGTH", 27))
                if((str(Nic_PCB_no) == str(input_nic_pcb_no.lower())) or (str(Nic_PCB_no) == str(input_nic_pcb_no.upper()))):
                    meter_info['NIC_PCB_No'] = str(Nic_PCB_no)
                    test_result['Get_NIC_PCB_No'] = 'pass'
                    logging.info(f"nic pcb serial number for com: {com_port}, nic pcb serial numbr: {Nic_PCB_no}")
                else:
                    meter_info['NIC_PCB_No'] = str(Nic_PCB_no)
                    test_result['Get_NIC_PCB_No'] = 'fail'
                    logging.info(f"fail in get nic pcb serial number for com: {com_port}, response: {Nic_PCB_no}")
                test_result['Get_NIC_PCB_No_Retry_Count'] = '1'
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error to get pcb serial number for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1

        # Check Internal Version
        if data_dict.get("INTERNAL_VERSION", 0) == 0:
            print("\nSkipping to Get INTERNAL VERSION")
            logging.info(f"Skip internal version check for com: {com_port}")
            test_result['Get_Internal_Version'] = 'pass'
            test_result['Get_Internal_Version_Retry_Count'] = '1'
            meter_info['Internal_Version'] = '0'
        else:
            retryCnt = 3
            while (retryCnt):
                logging.info(f"Get Inetrnal version for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    int_version=cases.get_internal_version_val()
                    if str(int_version)==str(data_dict.get("INTERNAL_VERSION", 00)):
                        test_result['Get_Internal_Version'] = 'pass'
                        meter_info['Internal_Version'] = str(int_version)
                    else:
                        test_result['Get_Internal_Version'] = 'fail'
                        meter_info['Internal_Version'] = str(int_version)
                    test_result['Get_Internal_Version_Retry_Count'] = '1'
                    logging.info(f"get internal version for com: {com_port}, response: {int_version}")
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in get internal version for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1

        # Get 1p cofficient
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Get 1p calibration cofficient for com: {com_port}, attempt: {4-retryCnt}")
            try:
                calib_cofficient=cases.get_1p_calib_coffi()
                logging.info(f"Result of calib cofficient: {calib_cofficient}, for com: {com_port}")
                if 'Fail' in calib_cofficient:
                    meter_info['CalibSign'] = 'Fail'
                    meter_info['FrequencyCoeff'] = 'Fail'
                    meter_info['VCoeff'] = 'Fail'
                    meter_info['ICoeff[0]'] = 'Fail'
                    meter_info['ICoeff[1]'] = 'Fail'
                    meter_info['ActPowerCoeff[0]'] = 'Fail'
                    meter_info['ActPowerCoeff[1]'] = 'Fail'
                    meter_info['PhAngle[0]'] = 'Fail'
                    meter_info['PhAngle[1]'] = 'Fail'
                    test_result['Verify_Meter_Calibration'] = 'fail'
                    test_result['Verify_Meter_Calibration_Retry_Count'] = '1'
                    logging.info(f"Fail in get 1p calib cofficient for com: {com_port}")
                else:
                        meter_info['CalibSign'] = str(calib_cofficient.get('CalibSign'))
                        meter_info['FrequencyCoeff'] = str(calib_cofficient.get('FrequencyCoeff'))
                        meter_info['VCoeff'] = str(calib_cofficient.get('VCoeff'))
                        meter_info['ICoeff[0]'] = str(calib_cofficient.get('ICoeff[0]'))
                        meter_info['ICoeff[1]'] = str(calib_cofficient.get('ICoeff[1]'))
                        meter_info['ActPowerCoeff[0]'] = str(calib_cofficient.get('ActPowerCoeff[0]'))
                        meter_info['ActPowerCoeff[1]'] = str(calib_cofficient.get('ActPowerCoeff[1]'))
                        meter_info['PhAngle[0]'] = str(calib_cofficient.get('PhAngle[0]'))
                        meter_info['PhAngle[1]'] = str(calib_cofficient.get('PhAngle[1]'))
                        test_result['Verify_Meter_Calibration_Retry_Count'] = '1'
                        if 'better' in meter_type.lower():
                            if (
                                ((float(calib_cofficient.get('FrequencyCoeff')) >= 0) and (float(calib_cofficient.get('FrequencyCoeff')) <= 2)) and
                                ((float(calib_cofficient.get('VCoeff')) >= 0) and (float(calib_cofficient.get('VCoeff')) <= 2)) and
                                ((float(calib_cofficient.get('ICoeff[0]')) >= 0) and (float(calib_cofficient.get('ICoeff[0]')) <= 2)) and
                                ((float(calib_cofficient.get('ICoeff[1]')) >= 0) and (float(calib_cofficient.get('ICoeff[1]')) <= 2)) and
                                ((float(calib_cofficient.get('ActPowerCoeff[0]')) >= 0) and (float(calib_cofficient.get('ActPowerCoeff[0]')) <= 2)) and
                                ((float(calib_cofficient.get('ActPowerCoeff[1]')) >= 0) and (float(calib_cofficient.get('ActPowerCoeff[1]')) <= 2)) and
                                ((float(calib_cofficient.get('PhAngle[0]')) >= 0) and (float(calib_cofficient.get('PhAngle[0]')) <= 2)) and
                                ((float(calib_cofficient.get('PhAngle[1]')) >= 0) and (float(calib_cofficient.get('PhAngle[1]')) <= 2))
                            ):
                                test_result['Verify_Meter_Calibration'] = 'pass'
                                logging.info(f"Pass in get 1p calib cofficient for com: {com_port}")
                            else:
                                test_result['Verify_Meter_Calibration'] = 'fail'
                                logging.info(f"Fail in get 1p calib cofficient for com: {com_port}")
                        else:
                            if ('wb' in data_dict.get('PROJECT', 'wb').lower()) or ('tn' in data_dict.get('PROJECT', 'wb').lower()):
                                if (
                                    ((float(calib_cofficient.get('FrequencyCoeff')) >= 0.99) and (float(calib_cofficient.get('FrequencyCoeff')) <= 1.1)) and
                                    ((float(calib_cofficient.get('VCoeff')) >= 0.00044) and (float(calib_cofficient.get('VCoeff')) <= 0.00047)) and
                                    ((float(calib_cofficient.get('ICoeff[0]')) >= 0.00000350) and (float(calib_cofficient.get('ICoeff[0]')) <= 0.00000400)) and
                                    ((float(calib_cofficient.get('ICoeff[1]')) >= 0.000000190) and (float(calib_cofficient.get('ICoeff[1]')) <= 0.000000240)) and
                                    ((float(calib_cofficient.get('ActPowerCoeff[0]')) >= 0.00000000150) and (float(calib_cofficient.get('ActPowerCoeff[0]')) <= 0.00000000200)) and
                                    ((float(calib_cofficient.get('ActPowerCoeff[1]')) >= 0.0000000000900) and (float(calib_cofficient.get('ActPowerCoeff[1]')) <= 0.000000000950)) and
                                    ((float(calib_cofficient.get('PhAngle[0]')) >= 0.13) and (float(calib_cofficient.get('PhAngle[0]')) <= 0.15)) and
                                    ((float(calib_cofficient.get('PhAngle[1]')) >= 0.11) and (float(calib_cofficient.get('PhAngle[1]')) <= 0.14))
                                ):
                                    test_result['Verify_Meter_Calibration'] = 'pass'
                                    logging.info(f"Pass in get 1p calib cofficient for com: {com_port}")
                                else:
                                    test_result['Verify_Meter_Calibration'] = 'fail'
                                    logging.info(f"Fail in get 1p calib cofficient for com: {com_port}")
                            else:
                                if (
                                    ((float(calib_cofficient.get('FrequencyCoeff')) >= 0.99) and (float(calib_cofficient.get('FrequencyCoeff')) <= 1.1)) and
                                    ((float(calib_cofficient.get('VCoeff')) >= 0.00044) and (float(calib_cofficient.get('VCoeff')) <= 0.00047)) and
                                    ((float(calib_cofficient.get('ICoeff[0]')) >= 0.00000350) and (float(calib_cofficient.get('ICoeff[0]')) <= 0.00000400)) and
                                    ((float(calib_cofficient.get('ICoeff[1]')) >= 0.000000340) and (float(calib_cofficient.get('ICoeff[1]')) <= 0.000000400)) and
                                    ((float(calib_cofficient.get('ActPowerCoeff[0]')) >= 0.00000000150) and (float(calib_cofficient.get('ActPowerCoeff[0]')) <= 0.00000000200)) and
                                    ((float(calib_cofficient.get('ActPowerCoeff[1]')) >= 0.000000000150) and (float(calib_cofficient.get('ActPowerCoeff[1]')) <= 0.000000000200)) and
                                    ((float(calib_cofficient.get('PhAngle[0]')) >= 0.13) and (float(calib_cofficient.get('PhAngle[0]')) <= 0.15)) and
                                    ((float(calib_cofficient.get('PhAngle[1]')) >= 0.11) and (float(calib_cofficient.get('PhAngle[1]')) <= 0.14))
                                ):
                                    test_result['Verify_Meter_Calibration'] = 'pass'
                                    logging.info(f"Pass in get 1p calib cofficient for com: {com_port}")
                                else:
                                    test_result['Verify_Meter_Calibration'] = 'fail'
                                    logging.info(f"Fail in get 1p calib cofficient for com: {com_port}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in get 1p calibration cofficient for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1


        # Set GPRS Protocol value
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Set GPRS Protocol Value for com: {com_port}, attempt: {4-retryCnt}")
            try:
                set_gprs_prot=cases.set_gprs_protocol_val(2)
                logging.info(f"Set GPRS protocol result: {set_gprs_prot}, for com: {com_port}")
                if set_gprs_prot.get('Result') == 'Pass':
                    test_result['Set_GPRS_Protocol'] = 'pass'
                else:
                    test_result['Set_GPRS_Protocol'] = 'fail'
                test_result['Set_GPRS_Protocol_Retry_Count'] = '1'
                logging.info(f"Set GPRS protocol value for com: {com_port} = {set_gprs_prot}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in set GPRS Protocol value for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1

        # Get Gprs Protocol Value
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Check GPRS Protocol Value for com: {com_port}, attempt: {4-retryCnt}")
            try:
                get_gprs_prot=cases.get_gprs_protocol_val()
                meter_info['GPRS_Protocol_Value'] = get_gprs_prot.get('gprs_proto', 'None')
                if get_gprs_prot.get('Result').lower() == 'pass':
                    test_result['Get_GPRS_Protocol'] = 'pass'
                else:
                    test_result['Get_GPRS_Protocol'] = 'fail'
                test_result['Get_GPRS_Protocol_Retry_Count'] = '1'
                logging.info(f"GPRS protocol value for com: {com_port} = {get_gprs_prot}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in get GPRS Protocol value for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    meter_info['GPRS_Protocol_Value'] = 'None'
                    test_result['Get_GPRS_Protocol'] = 'fail'
                    test_result['Get_GPRS_Protocol_Retry_Count'] = f'{3-retryCnt}'

        #for voltage Influence Test check voltage
        print("\n\n.............Waiting for Bench Stablization Before Voltage Influence Test...........")
        logging.info(f".............Waiting for Bench Stablization Before Voltage Influence Test for {data_dict.get("Bench_StabT_VolI", 0)} sec...........")
        time.sleep(data_dict.get("Bench_StabT_VolI", 0))
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Get Volatages Influence values for com: {com_port}, attempt: {4-retryCnt}")
            try:
                voltage_val = cases.Verify_Voltage()
                if(float(data_dict.get("Voltage_Influence_minV", 0.0)) <= float(voltage_val) <= float(data_dict.get("Voltage_Influence_maxV", 0.0))):
                    test_result['Verify_Voltage_Influence_Test'] = 'pass'
                    meter_info['Voltage_Influence_Test_Voltage'] = str(voltage_val)
                else:
                    test_result['Verify_Voltage_Influence_Test'] = 'fail'
                    meter_info['Voltage_Influence_Test_Voltage'] = str(voltage_val)
                test_result['Verify_Voltage_Influence_Test_Retry_Count'] = '1'
                logging.info(f"Sucessfull get volateg values for com: {com_port}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in verify voltage for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1


        # Set/Get Manufacturing Name only run when enabled in config
        # (MANUFACTURING_NAME_ENABLE); when disabled they are skipped and
        # their columns are omitted from the Excel log.
        if is_manufacturing_name_enabled(data_dict):
            # set Manufacturing name
            retryCnt = 3
            while (retryCnt):
                logging.info(f"set Manufacturing Name for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    set_manufacturing_name = cases.set_manufacturing_name(int(data_dict.get("MANUFACTURING_NAME", 1)))
                    if set_manufacturing_name.get("Result").lower() == 'fail':
                        test_result['Set_Manufacturing_Name'] = 'fail'
                    else:
                        test_result['Set_Manufacturing_Name'] = 'pass'
                    retryCnt = 0
                    logging.info(f"set Manufacturing Name for com: {com_port}, response: {set_manufacturing_name}")
                except Exception as e:
                    logging.error(f"Error in set Manufacturing Name for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1
                    if retryCnt == 0:
                        test_result['Set_Manufacturing_Name'] = 'fail'
            test_result['Set_Manufacturing_Name_Retry_Count'] = 4-retryCnt

            # get Manufacturing name
            retryCnt = 3
            while (retryCnt):
                logging.info(f"Check Manufacturing name Value for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    get_manufacturing_name = cases.get_manufacturing_name()
                    meter_info['Manufacturing_Name'] = get_manufacturing_name.get('manufacturing_name', 'None')
                    if get_manufacturing_name.get('Result').lower() == 'pass':
                        if str(get_manufacturing_name.get('manufacturing_name', 'None')) == str(data_dict.get("MANUFACTURING_NAME", 1)):
                            test_result['Get_Manufacturing_Name'] = 'pass'
                        else:
                            test_result['Get_Manufacturing_Name'] = 'fail'
                    else:
                        test_result['Get_Manufacturing_Name'] = 'fail'
                    test_result['Get_Manufacturing_Name_Retry_Count'] = '1'
                    logging.info(f"Manufacturing Name for com: {com_port} = {get_manufacturing_name}")
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in get Manufacturing Name for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1
                    if retryCnt == 0:
                        meter_info['Manufacturing_Name'] = 'None'
                        test_result['Get_Manufacturing_Name'] = 'fail'
                        test_result['Get_Manufacturing_Name_Retry_Count'] = f'{3-retryCnt}'
        else:
            logging.info(f"Manufacturing Name set/get skipped (disabled in config) for com: {com_port}")

        channle_num = None
        prv_status = False
        if (('rf' in toolName.lower()) and (data_dict.get('rf_prov',1) == 1)) or ('img' in toolName.lower()):
            retryCnt = 3
            while (retryCnt > 0):
                logging.info(f"Set Tunnel Mode for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    debug_status = cases.set_tunnel_mode()
                    if debug_status.get("Result")=='Fail':
                        retryCnt -= 1
                        time.sleep(0.5)
                        print("Tunnel Mode Fail")
                        ser.write(end_bytes)
                        time.sleep(0.1)
                        ser.write(end_bytes)
                        time.sleep(0.1)
                        ser.write(end_bytes)
                        time.sleep(0.5)
                    else:
                        test_result['Set Debug Print Mode'] = 'pass'
                        break
                    logging.info(f"Set Tunnel Mode for com: {com_port} = {debug_status}")
                except Exception as e:
                    logging.error(f"Error in set Tunnel Mode for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1
                    time.sleep(0.5)
                    ser.write(end_bytes)
                    time.sleep(0.1)
                    ser.write(end_bytes)
                    time.sleep(0.1)
                    ser.write(end_bytes)
                    time.sleep(0.5)

            # with prov_lock:
            if (('rf' in toolName.lower()) and (data_dict.get('rf_prov',1) == 1)):
                prv_status, channle_num = rf_meter_provisioning(ser, com_port)
                print(prv_status, channle_num)
                logging.info(f"Get provisioning result\n Status: {prv_status} \n channel num: {channle_num} ")
                if prv_status:
                    test_result['Set Provisioning Channel'] = '1'
                    test_result['Set Provisioning Channel Status'] = 'pass'
                    if str(channle_num) == '1':
                        test_result['Get Provisioning Channel'] = channle_num
                        test_result['Check Provisioning Parameters Status'] = 'pass'
                    else:
                        test_result['Get Provisioning Channel'] = channle_num
                        test_result['Check Provisioning Parameters Status'] = 'fail'
                else:
                    test_result['Set Provisioning Channel'] = '1'
                    test_result['Set Provisioning Channel Status'] = 'fail'
                    if str(channle_num) == '1':
                        test_result['Get Provisioning Channel'] = channle_num
                        test_result['Check Provisioning Parameters Status'] = 'pass'
                    else:
                        test_result['Get Provisioning Channel'] = channle_num
                        test_result['Check Provisioning Parameters Status'] = 'fail'
            else:
                # Only attempt IMG provisioning if every FTT step run so far
                # has passed. There's no point provisioning a meter that's
                # already going to fail overall, and running it anyway risks
                # writing provisioning data onto a meter that failed an
                # earlier check. If anything above already failed, skip the
                # img_provisioning() call entirely and record this result as
                # 'fail' too -- same 'fail' in test_result.values() check
                # used everywhere else in this function to look back at
                # every step run so far.
                if 'fail' in test_result.values():
                    logging.info(f"Skipping IMG Provisioning for com: {com_port} -- an earlier FTT step already failed")
                    print(Fore.RED + "❌ Skipping IMG Provisioning -- earlier FTT step(s) failed")
                    print(Style.RESET_ALL)
                    test_result['PROVISIONING_STATUS'] = 'fail'
                    provisioning_fail_reason = "Skipped -- an earlier FTT step already failed"
                else:
                    img_id_str = str(meter_info['NIC_PCB_No'][-8:])
                    img_id = str(int(img_id_str))
                    gateway_id = data_dict.get('GATEWAY_TEXT_PREFIX','IMG') + img_id_str
                    # img_id/gateway_id are DATA, not pass/fail -- goes into
                    # meter_info like every other raw value in this function
                    # (Meter_PCB_Serial_No, NIC_PCB_No, etc.), not test_result.
                    meter_info['IMG ID'] = img_id
                    meter_info['Gateway ID'] = gateway_id
                    nic_parameters_data, prov_sucess, reason = img_provisioning(data_dict, img_id, gateway_id, com_port, ser)
                    if prov_sucess:
                            status_dict, result_status, reason, nic_parameters_data = check_provisioning_status(nic_parameters_data, data_dict)
                            # Split the same way the rest of this function
                            # does: status_dict holds pass/fail verification
                            # columns (the "... Status" fields) -> test_result
                            # (this function's result_list equivalent).
                            # nic_parameters_data holds the raw provisioning
                            # parameters/version strings actually read back
                            # from the gateway (WIREPAS_*, GW_*) -> meter_info.
                            # (Previously both were dumped into an undefined
                            # `result_dict` name that collides with the
                            # unrelated Queue also called result_dict in
                            # run() -- see conversion notes.)
                            test_result.update(status_dict)
                            meter_info.update(nic_parameters_data)
                            if result_status == "pass":
                                overall_result = "pass"
                            else:
                                overall_result = "fail"
                                print(Fore.RED + "❌ IMG Provisioning Failed!")
                                print(Style.RESET_ALL)
                                # return result_dict, overall_result, reason

                    else:
                        overall_result = "FAIL"
                        print(Fore.RED + "❌ IMG Provisioning Failed!")
                        print(Style.RESET_ALL)
                        # reason = "Error in Provisioning"
                        # return result_dict, overall_result, reason

                    # Record the outcome in test_result so it actually feeds
                    # into OVER_ALL_RESULT below and into the Excel
                    # log/fail-message list, the same as every other step --
                    # previously `overall_result` was a local variable that
                    # nothing downstream ever read.
                    #
                    # provisioning_fail_reason (local var, NOT a test_result
                    # key) carries this same reason to the summary popup via
                    # build_log_entry()'s dedicated provisioning_reason
                    # param instead -- test_result gets dumped wholesale into
                    # an Excel column per key by add_log_xlsc(), so adding it
                    # there would silently create an unwanted
                    # "PROVISIONING_FAIL_REASON" column in the log workbook.
                    test_result['PROVISIONING_STATUS'] = overall_result.lower()
                    provisioning_fail_reason = reason if overall_result.lower() == 'fail' else ''


            # Close Tunnel Mode
            print("🔄 Sending end bytes...")
            retryCnt = 3
            while retryCnt > 0:
                try:
                    logging.info(f"Closing Tunnel mode for com: {com_port}, attempt: {4-retryCnt}")
                    print("Sending Command to Close Tunnel Mode")
                    ser.write(end_bytes)
                    time.sleep(0.5)
                    retryCnt -= 1
                except Exception as e:
                    retryCnt = 0
                    print("Not Able to Close Tunnel Mode")
                    logging.info(f"Error in Closing Tunnel mode for com: {com_port}, error: {str(e)}")
                    msg = [f"COM: {com_port} Not Able to Close Tunnel Mode"]
                    # result_queue.append(msg)
                    result_queue.put((com_port.lower(), msg))
                    abort_flag.set()
                    # return
            print("✅ End bytes sent.")

        time.sleep(2)
        
        # if ('4g' in toolName.lower()) and ('tn' in data_dict.get('PROJECT', 'wb').lower()):
        if '4g' in toolName.lower():
            periodic_push_ipv6 = "2406.da1a.565.f50d.c7ee.8336.ef46.ffc2,4059"
            event_push_ipv6 = "2406.da1a.565.f50d.c7ee.8336.ef46.ffc2,4059"
            meter_project = data_dict.get('PROJECT', 'wb').lower()
            if meter_project == 'gomati':
                periodic_push_ipv6 = "2406.da1a.565.f50d.c7ee.8336.ef46.ffc2,4059"
                event_push_ipv6 = "2406.da1a.565.f50d.c7ee.8336.ef46.ffc2,4059"
            elif meter_project == 'saryu':
                periodic_push_ipv6 = "2406.da1a.f52.c907.7a85.8dfe.a74d.c7da,4059"
                event_push_ipv6 = "2406.da1a.f52.c907.7a85.8dfe.a74d.c7da,4059"
            elif meter_project == 'manipur':
                periodic_push_ipv6 = "2406.da1a.ccf.9500.eeaa.4c65.58ae.63bb,4059"
                event_push_ipv6 = "2406.da1a.ccf.9500.eeaa.4c65.58ae.63bb,4059"
            elif meter_project == 'wb':
                periodic_push_ipv6 = "2603.c021.4007.a000.db7a.c271.e6f8.c28d,4059"
                event_push_ipv6 = "2603.c021.4007.a000.db7a.c271.e6f8.c28d,4059"
            elif meter_project == 'tn':
                periodic_push_ipv6 = "2406.da1a.1bc9.cd03.0000.0000.0000.000a,4059"
                event_push_ipv6 = "2406.da1a.1bc9.cd03.0000.0000.0000.000a,4059"
            elif meter_project == 'tata_delhi':
                periodic_push_ipv6 = "2405.0203.0502.0000.0000.0000.0000.0013,4059"
                event_push_ipv6 = "2405.0203.0502.0000.0000.0000.0000.0013,4059"
            periodic_push_interval = "60"

            # Check GPRS connection
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Checking GPRS Connection, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    check_gprs_conn = cases.get_meter_sim_and_sim_number(com_port, meter_type.lower())
                    logging.debug(f"Result of getting SIM details: {check_gprs_conn}, for com: {com_port}")
                    sim_values = check_gprs_conn.get('sim_result_value')
                    meter_info['Active_Sim'] = str(sim_values[0])
                    meter_info['SIM_NUM'] = str(sim_values[1])
                    meter_info['APN'] = str(sim_values[2])
                    meter_info['IMEI'] = str(sim_values[3])
                    meter_info['Signal_Strength'] = str(sim_values[4])
                    if check_gprs_conn.get('Result', '').lower() == 'fail':
                        test_result['Check_GPRS_Connection'] = 'fail'
                    else:
                        test_result['Check_GPRS_Connection'] = 'pass'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker4g func in checking GPRS connection: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1
                    if retryCnt == 0:
                        meter_info['Active_Sim'] = 'fail'
                        meter_info['SIM_NUM'] = 'fail'
                        meter_info['APN'] = 'fail'
                        meter_info['IMEI'] = 'fail'
                        meter_info['Signal_Strength'] = 'fail'
                        test_result['Check_GPRS_Connection'] = 'fail'
            
            # Set Periodic push ipv6 address value
            retryCnt = 3
            while (retryCnt):
                logging.info(f"Set Periodic push ipv6 address for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    perioad_push_ipv6_res = cases.set_periodic_push_val(periodic_push_ipv6)
                    logging.info(f"Set Periodic push ipv6 address result: {perioad_push_ipv6_res}, for com: {com_port}")
                    if perioad_push_ipv6_res.get('Result').lower() == 'pass':
                        test_result['Set_Periodic_Push_IPV6'] = 'pass'
                    else:
                        test_result['Set_Periodic_Push_IPV6'] = 'fail'
                    test_result['Set_Periodic_Push_IPV6_Retry_Count'] = '1'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in Periodic push ipv6 address for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1

            # Get Periodic push ipv6 address value
            retryCnt = 3
            while (retryCnt):
                logging.info(f"Check Periodic push ipv6 address for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    get_periodic_push_ipv6_res = cases.get_periodic_push_val()
                    print((f"Periodic push ipv6 address for com: {com_port} = {get_periodic_push_ipv6_res}"))
                    logging.info(f"Periodic push ipv6 address for com: {com_port} = {get_periodic_push_ipv6_res}")
                    if get_periodic_push_ipv6_res.lower() != 'fail':
                        if get_periodic_push_ipv6_res.lower() == periodic_push_ipv6.replace('.',':').lower():
                            meter_info['Periodic_Push_IPV6'] = get_periodic_push_ipv6_res
                            test_result['Get_Periodic_Push_IPV6'] = 'pass'
                        else:
                            meter_info['Periodic_Push_IPV6'] = get_periodic_push_ipv6_res
                            test_result['Get_Periodic_Push_IPV6'] = 'fail'
                    else:
                        meter_info['Periodic_Push_IPV6'] = ''
                        test_result['Get_Periodic_Push_IPV6'] = 'fail'
                    test_result['Get_Periodic_Push_IPV6_Retry_Count'] = '1'
                    
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in get Periodic push ipv6 address for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1
                    if retryCnt == 0:
                        meter_info['Periodic_Push_IPV6'] = 'None'
                        test_result['Get_Periodic_Push_IPV6'] = 'fail'
                        test_result['Get_Periodic_Push_IPV6_Retry_Count'] = f'{3-retryCnt}'

            # Set Periodic push Interval value
            retryCnt = 3
            while (retryCnt):
                logging.info(f"Set Periodic push interval for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    periodic_push_interval_res = cases.set_periodic_push_interval_val(periodic_push_interval)
                    logging.info(f"Set Periodic push interval result: {periodic_push_interval_res}, for com: {com_port}")
                    if periodic_push_interval_res.get('Result').lower() == 'pass':
                        test_result['Set_Periodic_Push_Interval'] = 'pass'
                    else:
                        test_result['Set_Periodic_Push_Interval'] = 'fail'
                    test_result['Set_Periodic_Push_Interval_Retry_Count'] = '1'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in Periodic push interval for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1

            # Get Periodic push Interval value
            retryCnt = 3
            while (retryCnt):
                logging.info(f"Check Periodic push interval for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    get_periodic_push_interval_res = cases.get_periodic_push_interval_val()
                    print((f"Periodic push interval for com: {com_port} = {get_periodic_push_interval_res}"))
                    logging.info(f"Periodic push interval for com: {com_port} = {get_periodic_push_interval_res}")
                    if get_periodic_push_interval_res.lower() != 'fail':
                        if str(get_periodic_push_interval_res).lower() == str(periodic_push_interval).lower():
                            meter_info['Periodic_Push_Interval'] = str(get_periodic_push_interval_res)
                            test_result['Get_Periodic_Push_Interval'] = 'pass'
                        else:
                            meter_info['Periodic_Push_Interval'] = str(get_periodic_push_interval_res)
                            test_result['Get_Periodic_Push_Interval'] = 'fail'
                    else:
                        meter_info['Periodic_Push_Interval'] = ''
                        test_result['Get_Periodic_Push_Interval'] = 'fail'
                    test_result['Get_Periodic_Push_Interval_Retry_Count'] = '1'

                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in get Periodic push interval for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1
                    if retryCnt == 0:
                        meter_info['Periodic_Push_Interval'] = 'None'
                        test_result['Get_Periodic_Push_Interval'] = 'fail'
                        test_result['Get_Periodic_Push_Interval_Retry_Count'] = f'{3-retryCnt}'

            # Set Event push ipv6 address value
            retryCnt = 3
            while (retryCnt):
                logging.info(f"Set Event push ipv6 address for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    set_event_push_ipv6_res = cases.set_event_push_val(event_push_ipv6)
                    logging.info(f"Set Event push ipv6 address result: {set_event_push_ipv6_res}, for com: {com_port}")
                    if set_event_push_ipv6_res.get('Result').lower() == 'pass':
                        test_result['Set_Event_Push_IPV6'] = 'pass'
                    else:
                        test_result['Set_Event_Push_IPV6'] = 'fail'
                    test_result['Set_Event_Push_IPV6_Retry_Count'] = '1'
                    logging.info(f"Set Event push ipv6 address for com: {com_port} = {set_event_push_ipv6_res}")
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in set Event push ipv6 address for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1

            # Get Event push ipv6 address value
            retryCnt = 3
            while (retryCnt):
                logging.info(f"Check Event push ipv6 address for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    get_event_push_ipv6_res = cases.get_event_push_val()
                    print(f"Event push ipv6 address for com: {com_port} = {get_event_push_ipv6_res}")
                    logging.info(f"Event push ipv6 address for com: {com_port} = {get_event_push_ipv6_res}")
                    # meter_info['Event_Push_IPV6'] = get_event_push_ipv6_res.get('gprs_proto', 'None')
                    if get_event_push_ipv6_res.lower() != 'fail':
                        if get_event_push_ipv6_res.lower() == event_push_ipv6.replace('.',':').lower():
                            meter_info['Event_Push_IPV6'] = get_event_push_ipv6_res
                            test_result['Get_Event_Push_IPV6'] = 'pass'
                        else:
                            meter_info['Event_Push_IPV6'] = get_event_push_ipv6_res
                            test_result['Get_Event_Push_IPV6'] = 'fail'
                    else:
                        meter_info['Event_Push_IPV6'] = ''
                        test_result['Get_Event_Push_IPV6'] = 'fail'
                    test_result['Get_Event_Push_IPV6_Retry_Count'] = '1'
                    
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in get Event push ipv6 address for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1
                    if retryCnt == 0:
                        meter_info['Event_Push_IPV6'] = 'None'
                        test_result['Get_Event_Push_IPV6'] = 'fail'
                        test_result['Get_Event_Push_IPV6_Retry_Count'] = f'{3-retryCnt}'

        # Factory reset
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Factory reset start for com: {com_port}, attempt: {4-retryCnt}")
            try:
                FactoryReset=cases.Factory_reset_val()
                if FactoryReset.get('Result').lower() == 'pass':
                    test_result['factory_reset'] = 'pass'
                else:
                    test_result['factory_reset'] = 'fail'
                test_result['factory_reset_Retry_Count'] = '1'
                logging.info(f"Factory reset is done for com: {com_port}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in factory reset for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1

        # logging.info(f"Waiting for 8 sec for meter restart after factory reset")
        # time.sleep(8)
                
        if(str(check_port) == str(data_dict.get("LIVE_VERSION", 00))):
            test_result['Verify_Serial_No_Mismatch'] = 'pass' #use to fill sr no mismatch column initially
            test_result['Verify_Serial_No_Mismatch_Retry_Count'] = '1'
            test_result['Live_version_Status'] = 'pass'
            test_result['Live_version_Status_Retry_Count'] = '1'
        else:
            test_result['Verify_Serial_No_Mismatch'] = 'pass' #use to fill sr no mismatch column initially
            test_result['Verify_Serial_No_Mismatch_Retry_Count'] = '1'
            test_result['Live_version_Status'] = 'fail'
            test_result['Live_version_Status_Retry_Count'] = '1'



        # print("prv status is:",prv_status, "channel num is:", channle_num)


        print (test_result)
        if 'fail' in test_result.values():
            meter_info['OVER_ALL_RESULT'] = 'fail'
        else:
            meter_info['OVER_ALL_RESULT'] = 'pass'

        ser.close()

        entry = build_log_entry(mac, meter_info, test_result, bookName, fileName, com_port, provisioning_fail_reason)
        # 'Verify_Serial_No_Mismatch' needs NO exclusion here -- unlike the
        # PCT reference's 'Meter PCB Serial Numebr Check', the block right
        # above always writes an explicit optimistic 'pass' placeholder for
        # it before we ever get here, so it's never "missing" at this point.
        # See fill_missing_fields() docstring.
        fill_missing_fields(entry, meter_info_keys, result_keys)
        result_log.put((com_port.lower(), entry))

        time.sleep(0.1)
        # Always queue (even an empty list): run() indexes
        # temp_results[com_port] unconditionally further down whenever
        # OVER_ALL_RESULT is 'fail', and now that build_fail_messages()
        # excludes MCT/provisioning keys it's possible for a port whose
        # only failure was MCT/provisioning to produce an empty list here --
        # skipping the queue put in that case would leave temp_results
        # without an entry for this port and crash that lookup with a
        # KeyError.
        fail_messages = build_fail_messages(com_port, test_result, fail_message_lookup)
        result_queue.put((com_port.lower(), fail_messages))

        EndTime = datetime.datetime.now()
        print ("\nStartTime:",starttime)
        print ("EndTime:",EndTime)
        print ("Diff : ", EndTime - starttime)

    except Exception as e:
        print("Error:", e)
        # result_queue[com_port.lower()] = ["com port is unreachable:{}".format(com_port)]
        # result_queue.put(["com port is unreachable:{}".format(com_port)])
        result_queue.put((com_port.lower(), ["com port is unreachable:{}".format(com_port)]))
        # result_queue.append(["com port is unreachable:{}".format(com_port)])
        if ser is not None:
            ser.close()
        return

def make_pop_result(list_port, unique_results='' ):
    print("\n========== FINAL RESULTS ==========\n")

    unreachable = []
    failures = []
    passes = []
    info = []

    for line in unique_results:

        line = str(line)

        if "unreachable" in line.lower():
            unreachable.append(line)

        elif "fail" in line.lower():
            failures.append(line)

        elif "pass" in line.lower():
            passes.append(line)

        else:
            info.append(line)


    total_ports = len(list_port)
    total_unreachable = len(unreachable)
    total_failures = len(failures)
    total_pass = len(passes)


    # ----------------------------
    # Console Output (Colored)
    # ----------------------------

    print(Fore.CYAN + "========== PCT TEST SUMMARY ==========")
    print(Fore.CYAN + "Total Ports   :", total_ports)
    print(Fore.GREEN + "Passed        :", total_pass)
    print(Fore.YELLOW + "Failures      :", total_failures)
    print(Fore.RED + "Unreachable   :", total_unreachable)
    print(Fore.CYAN + "======================================\n")


    if unreachable:
        print(Fore.RED + "❌ UNREACHABLE PORTS")
        print(Fore.RED + "---------------------")
        for u in unreachable:
            print(Fore.RED + u)
        print()

    if failures:
        print(Fore.YELLOW + "⚠ TEST FAILURES")
        print(Fore.YELLOW + "----------------")
        for f in failures:
            print(Fore.YELLOW + f)
        print()

    if passes:
        print(Fore.GREEN + "✔ PASSED PORTS")
        print(Fore.GREEN + "----------------")
        for p in passes:
            print(Fore.GREEN + p)
        print()

    if info:
        print(Fore.CYAN + "Passed Ports")
        print(Fore.CYAN + "----")
        for i in info:
            print(Fore.CYAN + i)
        print()


    # ----------------------------
    # Popup Text Formatting
    # ----------------------------

    popup_text = []
    popup_text.append("========== PCT TEST SUMMARY ==========\n")

    popup_text.append(f"Total Ports   : {total_ports}")
    popup_text.append(f"Passed        : {total_pass}")
    popup_text.append(f"Failures      : {total_failures}")
    popup_text.append(f"Unreachable   : {total_unreachable}")
    popup_text.append("")


    if unreachable:
        popup_text.append("❌ UNREACHABLE PORTS")
        popup_text.append("---------------------")
        popup_text.extend(unreachable)
        popup_text.append("")

    if failures:
        popup_text.append("⚠ TEST FAILURES")
        popup_text.append("----------------")
        popup_text.extend(failures)
        popup_text.append("")

    if passes:
        popup_text.append("✔ PASSED PORTS")
        popup_text.append("----------------")
        popup_text.extend(passes)
        popup_text.append("")

    if info:
        popup_text.append("INFO")
        popup_text.append("----")
        popup_text.extend(info)

    msg_text = "\n".join(popup_text)
    return msg_text

# def close_excel_file(filepath):
#     filepath = os.path.abspath(filepath)
#     ext = os.path.splitext(filepath)[1].lower()

#     # -----------------------------
#     # Case 1: Excel files
#     # -----------------------------
#     if ext in (".xlsx", ".xls", ".xlsm"):
#         pythoncom.CoInitialize()
#         try:
#             excel = win32com.client.GetObject(Class="Excel.Application")
#         except Exception:
#             return False

#         for wb in excel.Workbooks:
#             try:
#                 if wb.FullName.lower() == filepath.lower():
#                     print("Closing Excel file:", filepath)
#                     wb.Close(SaveChanges=False)
#                     excel.Quit()
#                     time.sleep(1)
#                     return True
#             except Exception:
#                 pass

#         return False


# update to resolve file corrupt issue
def close_excel_file(filepath):
    filepath = os.path.abspath(filepath)
    ext = os.path.splitext(filepath)[1].lower()

    # -----------------------------
    # Case 1: Excel files
    # -----------------------------
    if ext in (".xlsx", ".xls", ".xlsm"):
        pythoncom.CoInitialize()
        try:
            try:
                excel = win32com.client.GetObject(Class="Excel.Application")
            except Exception:
                return False

            try:
                for wb in excel.Workbooks:
                    try:
                        if wb.FullName.lower() == filepath.lower():
                            print("Closing Excel file:", filepath)
                            wb.Close(SaveChanges=False)
                            if excel.Workbooks.Count == 0:
                                excel.Quit()
                            time.sleep(1)
                            return True
                    except Exception:
                        pass
            except Exception as e:
                logging.warning(f"close_excel_file: Excel COM not responding, skipping close: {e}")

            return False
        finally:
            pythoncom.CoUninitialize()


def run(data_dict, list_port, cpu_serial_num):
    # `rtt_results` is no longer accepted here -- RTT is now checked inside
    # main_function() itself (for 'img' tool types), right after it reads
    # the PCB serial number, instead of being pre-computed by a separate
    # stage in img_ftt_provisioning.py before FTT was ever allowed to start.
    print(Fore.YELLOW + ".........................Starting FTT Test checks.......................")
    print(Style.RESET_ALL)
    toolName=data_dict.get("TOOL_TYPE", "FTT")
    mct_applicable = any(t in toolName.lower() for t in ('img', '4g', 'rf'))
    meter_type = data_dict.get("METER_TYPE", "Garud_1PH").lower()
    bookName = meter_type.title() + "_" + toolName.upper() + "_" + "{}".format(str(data_dict.get("FTT_TEST_STATION", ''))) + "_LOG.xlsx"
    # bookName = meter_type+"_"+toolName+"_LOG.xlsx"
    fileName = toolName.upper()+"_DATA_LOG"
    port_inputs = []
    addDefaultFttLog(bookName,fileName, toolName.lower(), data_dict.get('rf_prov', 1), data_dict.get('PROJECT', 'wb'), is_manufacturing_name_enabled(data_dict))
    main_pcb_suffix = str(data_dict.get("Main_PCB_SFG_Prefix", "0000001"))
    # main_pcb_suffix = "0000001"
    nic_pcb_suffix = str(data_dict.get("NIC_PCB_SFG_PREFIX", "0000004"))
    ftt_result = {}

    print(list_port)

    for i, port in enumerate(list_port):

    # to take input for position 1 meter
        while True:
            com_port = input(f"Enter Com port for COM{port}(Ex.comx etc): ").lower()
            # com_port = 'com3'
            if com_port.lower() == "com{}".format(port).lower():
                break
            else:
                print("Wrong position of com port scanned please scan meter at")
                logging.info("Wrong position of com port scanned please scan meter at")

        meter_serial_num = enterSrNum_ftt(data_dict.get("PROJECT", "wb"))
        # meter_serial_num = "1234561"
        # logging.info(f"Input for 1st position com: {com_port}\nMeter Serial Num: {meter_serial_num}")

        while True:
            Meter_pcb_serial_no = input("Eneter Meter PCB serial No (Ex.FOR PCB V1.6.1 --- R161XXXX AND FOR PCB V1.6.4 -- P24101301000000100210000001...... etc): ")
            # Meter_pcb_serial_no = "P26052501000008000600026686"
            if ((str(Meter_pcb_serial_no[0:4]) == 'R161') or (str(Meter_pcb_serial_no[0:4]) == 'r161') or (str(Meter_pcb_serial_no[9:16]) == str(main_pcb_suffix))):
                break
            else:
                print("Invalid Format of Meter PCB Serial Num,Enter in this Format(Ex.FOR PCB V1.6.1 --- R161XXXX AND FOR PCB V1.6.4 -- P24101301000000100210000001...... etc)")
                logging.info("Invalid Format of Meter PCB Serial Num at ,Enter in this Format(Ex.FOR PCB V1.6.1 --- R161XXXX AND FOR PCB V1.6.4 -- P24101301000000100210000001...... etc)")

        while True:
            # Nic_PCB_serial_no = "P26042902000006900400111341"
            Nic_PCB_serial_no = input("Eneter NIC PCB serial No (Ex.R154XXXX...... or P24101301000000400310000001 etc): ")
            if((str(Nic_PCB_serial_no[0:4]) == 'R154') or (str(Nic_PCB_serial_no[0:4]) == 'r154') or (str(Nic_PCB_serial_no[9:16]) == str(nic_pcb_suffix))):
                break
            else:
                print("Invalid Format of NIC PCB Serial Num for RF,Enter in this Format(Ex.R154XXXX...... or P24101301000000400310000001 etc)")
                logging.info("Invalid Format of NIC PCB Serial Num for RF Enter in this Format(Ex.R154XXXX...... or P24101301000000400310000001 etc)")

        port_inputs.append((com_port.lower(), meter_serial_num, Meter_pcb_serial_no, Nic_PCB_serial_no))
    logging.info(f"Input for com: {port_inputs}")


    input_flag = True
    start_time = datetime.datetime.now()
    enter_flag1 = True
    # print("Press Enter to start the FTT script........")
    input("Press Enter to start the FTT script........")


    results = Queue()
    result_dict = Queue()
    abort_flag = Event()
    processes = []

    print("\n========== STARTING TESTING ==========\n")

    # -----------------------------
    # Create Thread For Each Port
    # -----------------------------
    for port_data in port_inputs:

        p = Thread(
            target=main_function,
            args=(
                data_dict,     # configuration data
                port_data[0],  # com_port
                port_data[1],  # meter_serial
                port_data[2],  # pcb_serial
                port_data[3],  # nic pcb
                results,
                abort_flag,
                result_dict,
            )
        )

        processes.append(p)

    # -----------------------------
    # Start Threads
    # -----------------------------
    for p in processes:
        # logging.info(f"Starting {p.name}")
        p.start()
        # logging.info(f"Started {p.name}")
        time.sleep(data_dict.get("thread_time_delay", 1))

    # -----------------------------
    # Wait For Completion
    # -----------------------------
    # 60s was enough for a passing meter, but a failing meter (provisioning
    # timeout + factory reset retries) runs longer. If the join gave up
    # early, run() found no result for the port, skipped the serial number
    # re-scan and never logged the failure.
    thread_timeout = data_dict.get("FTT_THREAD_TIMEOUT", 300)
    for p in processes:
        p.join(timeout=thread_timeout)
        if p.is_alive():
            logging.error(f"FTT thread {p.name} still running after {thread_timeout}s")
            print(Fore.RED + f"FTT thread {p.name} still running after {thread_timeout}s")
            print(Style.RESET_ALL)
    abort_flag.set()
    print("\n========== ALL PORTS COMPLETED for FTT ==========\n")
    logging.info("\n========== ALL PORTS COMPLETED for FTT ==========\n")

    reentered_pcbs = {}
    input_flag_2 = True
    start_time = datetime.datetime.now()
    enter_flag_3 = True

    temp_result_dict = {}
    while not result_dict.empty():
        key, value = result_dict.get()
        temp_result_dict[key] = value

    temp_results = {}
    while not results.empty():
        key, value = results.get()
        temp_results[key] = value

    if(len(temp_result_dict) > 0):
        print("\n\nAgain Scan Meter Serial No to complete the process...........")
        logging.info("\n========== VERIFY Meter SERIAL NUMBER ==========\n")
        logging.info("Input for verification...")



        for port in list_port:
            sr_num_received = ''
            com_port = f"com{port}"
            if (data_dict.get("PROJECT", "wb").lower() == "gomati") or (data_dict.get("PROJECT", "wb").lower() == "saryu"):
                while(1):
                    # scanning of barcode and taking serial no input
                    try:
                        serial_num = ''
                        serial_num = input("Enter Meter Serial Num for COM{} Meter(ex-PO12345678): ".format(port))
                        # match=re.match(r'^[a-zA-Z]{4}\d{6}$',serial_num)
                        match = re.match(r'^PO\d{8}$', serial_num)
                        # print "type of serial_num = ",type(serial_num)
                        if  match:
                            sr_num_received = serial_num[-8:]
                            reentered_pcbs[port] = sr_num_received
                            break
                        else:
                            reentered_pcbs[port] = ""
                            raise ValueError("invalid  format of serial num please  enter in this format  (ex-PO12345678)")
                    except ValueError as e:
                        logging.error(f"Error in Again scan meter serial number: {str(e)}")
                        print(f"Error in Again scan meter serial number: {str(e)}")

            elif((data_dict.get("PROJECT", "wb").lower() == "manipur")):
                while(1):
                    # scanning of barcode and taking serial no input
                    try:
                        serial_num = ''
                        serial_num = input("Enter Meter Serial Num for COM{} Meter(ex-MN1P232345): ".format(port))
                        # match=re.match(r'^[a-zA-Z]{4}\d{6}$',serial_num)
                        match = re.match(r'^MN1P\d{6}$', serial_num)
                        # print "type of serial_num = ",type(serial_num)
                        if  match:
                            sr_num_received = serial_num[-6:]
                            reentered_pcbs[port] = sr_num_received
                            break
                        else:
                            reentered_pcbs[port] = ""
                            raise ValueError("invalid  format of serial num please  enter in this format  (ex-MN1P232345)")
                    except ValueError as e:
                        logging.error(f"Error in Again scan meter serial number: {str(e)}")
                        print(f"Error in Again scan meter serial number: {str(e)}")

            elif((data_dict.get("PROJECT", "wb").lower() == "wb")):
                while(1):
                    # scanning of barcode and taking serial no input
                    try:
                        # serial_num = 'PPL1234561'
                        serial_num = input("Enter Meter Serial Num for COM{} Meter(ex-PPL1234567): ".format(port))
                        # match=re.match(r'^[a-zA-Z]{4}\d{6}$',serial_num)
                        match = re.match(r'^PPL\d{7}$', serial_num)
                        # print "type of serial_num = ",type(serial_num)
                        if  match:
                            sr_num_received=serial_num[-7:]
                            reentered_pcbs[port] = sr_num_received
                            break
                        else:
                            reentered_pcbs[port] = ""
                            raise ValueError("invalid  format of serial num please  enter in this format  (ex-PPL1234567)")
                    except ValueError as e:
                        logging.error(f"Error in Again scan meter serial number: {str(e)}")
                        print(f"Error in Again scan meter serial number: {str(e)}")

            elif((data_dict.get("PROJECT", "wb").lower() == "tn")):
                while(1):
                    # scanning of barcode and taking serial no input
                    try:
                        serial_num = ''
                        serial_num = input("Enter Meter Serial Num for COM{} Meter(ex-PO12345678): ".format(port))
                        # match=re.match(r'^[a-zA-Z]{4}\d{6}$',serial_num)
                        match = re.match(r'^PO\d{8}$', serial_num)
                        # print "type of serial_num = ",type(serial_num)
                        if  match:
                            sr_num_received = serial_num[-8:]
                            reentered_pcbs[port] = sr_num_received
                            break
                        else:
                            reentered_pcbs[port] = ""
                            raise ValueError("invalid  format of serial num please  enter in this format  (ex-PO12345678)")
                    except ValueError as e:
                        logging.error(f"Error in Again scan meter serial number: {str(e)}")
                        print(f"Error in Again scan meter serial number: {str(e)}")

            elif((data_dict.get("PROJECT", "wb").lower() == "others")):
                while(1):
                    # scanning of barcode and taking serial no input
                    try:
                        serial_num = ''
                        serial_num = input("Enter Meter Serial Num for COM{} Meter(ex-LR12345678 or any other identifier): ".format(port))
                        # match=re.match(r'^[a-zA-Z]{4}\d{6}$',serial_num)
                        # match = re.match(r'^PL\d{8}$', serial_num)
                        # print "type of serial_num = ",type(serial_num)
                        if len(serial_num) == 10:
                            sr_num_received=serial_num[-8:]
                            reentered_pcbs[port] = sr_num_received
                            break
                        else:
                            reentered_pcbs[port] = ""
                            raise ValueError("invalid  format of serial num please  enter in this format  (ex-LR12345678 or any other identifier)")
                    except ValueError as e:
                        logging.error(f"Error in Again scan meter serial number: {str(e)}")
                        print(f"Error in Again scan meter serial number: {str(e)}")

            elif (data_dict.get("PROJECT", "wb").lower() == "tata_delhi"):
                while(1):
                    # scanning of barcode and taking serial no input
                    try:
                        serial_num = ''
                        # serial_num = input("Enter Meter Serial Num for COM{} Meter(ex-PO12345678): ".format(port))
                        data = input("Enter Meter Serial Num for COM{} Meter(ex- 'TPDDL || 1126 || PO20000002'): ".format(port))
                        logging.info(f"Meter Serial Num for COM{port} Meter: {data}")
                        # match=re.match(r'^[a-zA-Z]{4}\d{6}$',serial_num)
                        serial_num = data.split("||")[-1].strip()
                        match = re.match(r'^PO\d{8}$', serial_num)
                        # print "type of serial_num = ",type(serial_num)
                        if  match:
                            sr_num_received = serial_num[-8:]
                            reentered_pcbs[port] = sr_num_received
                            break
                        else:
                            reentered_pcbs[port] = ""
                            raise ValueError("invalid  format of serial num please  enter in this format  (ex- 'TPDDL || 1126 || PO20000002')")
                    except ValueError as e:
                        logging.error(f"Error in Again scan meter serial number: {str(e)}")
                        print(f"Error in Again scan meter serial number: {str(e)}")
            else:
                reentered_pcbs[port] = ""
                raise ValueError("invalid  format of Project name selected in config file please  enter in this format  (ex-gomati or saryu or manipur or wb)")
        logging.info(f"Again Scanned Meter Serial Verification: {reentered_pcbs}")


    print(results)
    for port in list_port:
        com_port = f"com{port}"
        # 'rtt'/'rtt_reason' are new -- img_ftt_provisioning.py's run_main()
        # used to compute these itself, in a separate stage, before FTT ever
        # ran. Now RTT is checked inside main_function() (for 'img' tool
        # types only), so this is where that status has to be reported back
        # to the caller instead.
        ftt_result[com_port.lower()] = {
            "result": "fail",
            "reason": " ",
            "rtt": "pass" if not mct_applicable else "fail",
            "rtt_reason": "",
            # 'mct'/'provisioning' are new -- MCT_Test_Status/
            # PROVISIONING_STATUS (+ PROVISIONING_FAIL_REASON) already existed in
            # test_result, but nothing surfaced them here for the summary
            # popup to show as their own pass/fail rows, so a provisioning
            # failure only ever showed up folded into the FTT reason.
            "mct": "pass" if not mct_applicable else "fail",
            "mct_reason": "",
            "provisioning": "pass" if 'img' not in toolName.lower() else "fail",
            "PROVISIONING_FAIL_REASON": "",
        }
        if com_port not in temp_result_dict:
            # A port with no entry aborted somewhere inside main_function
            # before it could build one -- for 'img' tool types the most
            # likely cause is the RTT check right after the PCB serial read,
            # but com-port-unreachable and other early aborts land here too.
            # temp_results holds whatever message main_function actually
            # queued for this port, so surface that instead of a fixed
            # generic string.
            abort_reason = temp_results.get(com_port.lower(), 'Test Aborted')
            ftt_result[com_port.lower()]['reason'] = abort_reason
            if mct_applicable:
                ftt_result[com_port.lower()]['rtt'] = 'fail'
                ftt_result[com_port.lower()]['rtt_reason'] = abort_reason
                # main_function() aborted before test_result was ever built
                # for this port, so MCT/provisioning never ran either --
                # surface the same abort reason rather than a bare 'fail'.
                ftt_result[com_port.lower()]['mct'] = 'fail'
                ftt_result[com_port.lower()]['mct_reason'] = abort_reason
            if 'img' in toolName.lower():
                ftt_result[com_port.lower()]['provisioning'] = 'fail'
                ftt_result[com_port.lower()]['PROVISIONING_FAIL_REASON'] = abort_reason
            continue


        entry_found = False
        entry = temp_result_dict.get(com_port, None)
        meter_pcb_reenter = reentered_pcbs.get(port, '')

        if entry is None:
            print(f"Warning: No result found for COM{port}")
            continue

        # Reaching here means main_function() ran to completion for this
        # port, which (for 'img' tool types) is only possible if its inliness
        # RTT check already passed -- so rtt can be reported 'pass' now.
        if mct_applicable:
            ftt_result[com_port.lower()]['rtt'] = 'pass'
            ftt_result[com_port.lower()]['rtt_reason'] = ''
            # entry['result'] is main_function()'s test_result dict --  
            # MCT_Test_Status/PROVISIONING_STATUS were already being written
            # into it, just never read back out here. The reason text comes
            # from entry['provisioning_reason'] instead (a top-level
            # build_log_entry() field, NOT part of test_result) so it never
            # becomes an Excel column -- see build_log_entry()'s docstring.
            ftt_result[com_port.lower()]['mct'] = entry['result'].get('MCT_Test_Status', 'fail')
            ftt_result[com_port.lower()]['mct_reason'] = '' if ftt_result[com_port.lower()]['mct'] == 'pass' else 'MCT Test Failed'
        if 'img' in toolName.lower():
            ftt_result[com_port.lower()]['provisioning'] = entry['result'].get('PROVISIONING_STATUS', 'fail')
            ftt_result[com_port.lower()]['PROVISIONING_FAIL_REASON'] = entry.get('provisioning_reason', '')

        # Named lookup replaces the old entry[1][1] magic index into
        # MeterInfo (the 2nd positional item happened to be the original
        # serial number the operator scanned in at the start of the test) --
        # 'Original_Serial_Number' is the actual field name and can't
        # silently point at the wrong column if a branch's field order
        # ever changes.
        target_value = entry['meter_info'].get('Original_Serial_Number')



        if str(meter_pcb_reenter) == str(target_value):
            # Named lookup replaces the old entry[2][-4] magic index into
            # result_list (the 4th-from-last positional item happened to be
            # the 'Verify_Serial_No_Mismatch' optimistic 'pass' placeholder
            # main_function wrote before returning).
            # if 'rf' in toolName.lower():
            #     entry['result']['Verify_Serial_No_Mismatch'] = 'pass'
            # else:
            #     entry['result']['Verify_Serial_No_Mismatch'] = 'pass'
            entry['result']['Verify_Serial_No_Mismatch'] = 'pass'
            entry_found = True
            # Named lookup replaces the old entry[1][-1] magic index into
            # MeterInfo (the last positional item happened to be
            # 'OVER_ALL_RESULT', which main_function computes itself before
            # returning -- see main_function's final "if 'fail' in
            # test_result.values()" block).
            if entry['meter_info'].get('OVER_ALL_RESULT') == 'pass':
                ftt_result[com_port.lower()]["result"] = "pass"
                pass_messages = "PASS: COM{}".format(port)
                temp_results[com_port.lower()] = ""
            else:
                ftt_result[com_port.lower()]["result"] = "fail"
                ftt_result[com_port.lower()]["reason"] = temp_results[com_port.lower()]
                fail_messages = "COM Port: {}, Meter test failed".format("COM{}".format(port))
                temp_results[com_port.lower()].append(fail_messages)

        # -----------------------------------
        # Serial number mismatch case
        # -----------------------------------

        if not entry_found:
            entry = temp_result_dict.get(f"com{port}", None)
            # PRESERVED VERBATIM: pre-existing inconsistency in the original
            # script -- on an actual mismatch, the RF branch correctly marks
            # Verify_Serial_No_Mismatch as 'fail', but the non-RF branch
            # leaves/sets it to 'pass' instead. Not fixed here; this is a
            # pure refactor of storage, not of decision logic. See
            # conversion report.
            # if 'rf' in toolName.lower():
            #     entry['result']['Verify_Serial_No_Mismatch'] = 'fail'
            # else:
                # entry['result']['Verify_Serial_No_Mismatch'] = 'pass'
            entry['result']['Verify_Serial_No_Mismatch'] = 'fail'
            entry['meter_info']['OVER_ALL_RESULT'] = 'fail'
            ftt_result[com_port.lower()]["result"] = "fail"
            ftt_result[com_port.lower()]["reason"] = temp_results.get(com_port.lower(), '')
            fail_messages = "COM Port: {}, Fail in Meter Serial Number Mismatch between Printed Meter Serial No and Reentered Meter Serial No".format("COM{}".format(port))
            if len(ftt_result[com_port.lower()]["reason"]) > 0:
                ftt_result[com_port.lower()]["reason"].append(fail_messages)
            else:
                ftt_result[com_port.lower()]["reason"] = [fail_messages]

            if com_port.lower() not in temp_results:
                temp_results[com_port.lower()] = []

            temp_results[com_port.lower()].append(fail_messages)


    if temp_results:
        # Flatten and remove duplicates
        for result in temp_results.values():
            flat_results = [item for sublist in result for item in sublist]
            unique_results = list(set(flat_results))
            msg_text = "\n".join(unique_results)


    if (len(temp_result_dict)) > 0:

        # for entry in result_dict:
        for port in list_port:
            entry = temp_result_dict.get(f"com{port}", None)
            if entry is None:
                continue

            try:
                close_excel_file(bookName)
                add_log_xlsc(entry)
            except Exception as e:
                logging.error(f"Error writing Excel log for {entry.get('com_port','')}: {e}", exc_info=True)
                print(f"Error writing Excel log: {e}")

    if data_dict.get("IS_DATA_CONN", 1) == 1:
        df_frame = pd.read_excel(bookName)
        print(df_frame)
        try:
            status = False
            error = ""
            print(data_dict.get('rf_prov', 1), toolName)
            if 'better' in meter_type.lower():
                if ('rf' in toolName.lower()) and (data_dict.get('rf_prov', 1) == 1):
                    status, error = db_connect.upload_dataframe(df_frame, 'better', 'rf')
                else:
                    status, error = db_connect.upload_dataframe(df_frame, 'better', '4g')
            else:
                if ('rf' in toolName.lower()) and (data_dict.get('rf_prov', 1) == 1):
                    status, error = db_connect.upload_dataframe(df_frame, 'garud', 'rf')
                else:
                    status, error = db_connect.upload_dataframe(df_frame, 'garud', '4g')
            if not status:
                print(f"DB upload failed . Saved locally for retry. Error: {error}")
            else:
                if (len(temp_result_dict)) > 0:       # if the result file is empty then don't upload to server



                    import boto3
                    from botocore.exceptions import NoCredentialsError
                    


                    def upload_to_aws(local_folder, bucket, s3_file,sub_folder, file_time,folder_name1, cpu_serial_num):
                        s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                                        aws_secret_access_key=SECRET_KEY)

                        try:
                            key = str(cpu_serial_num + "_" +file_time + "_" + s3_file)
                            print("Uploaded to S3 Server...", key)
                            logging.info(f"Uploaded to S3 Server: {key}")
                            s3.upload_file(s3_file, bucket, folder_name +  "/{0}/{1}/{2}/{3}".format(folder_name1,sub_folder,local_folder, key))
                            print("Upload Successful")
                            logging.info("Upload Successful")
                            os.remove(s3_file)
                            return True
                        except NoCredentialsError:
                            print("Credentials not available")
                            return False
                        except Exception as e:
                            print(e)
                            print("The file was not found")
                            return False


                    al = os.listdir("./")
                    txt = list(filter(lambda x: x[-5:] == '.xlsx',al))
                    print(txt)
                    if len(txt) == 0:
                        print("file doesn't exist")#/dev/gp-gateway"
                        return#args.baud_rate = 9600

                    for j in range(len(txt)):
                        # today = date.today()
                        # print("Today date is: ", today)

                        file_time = datetime.datetime.now()
                        print("time = ",file_time)
                        date_only = datetime.datetime.strftime(file_time, '%Y-%m-%d')
                        time_only = datetime.datetime.strftime(file_time, '%H_%M_%S')
                        print("time is",time_only)
                        print("date is",date_only)

                        sub_folder = "UNKNOWN"
                        xyx =  str(txt[j])
                        if("PCT2" in xyx):
                            sub_folder = "PCT2"
                        elif("ftt" in xyx.lower()):
                            sub_folder = "FTT"
                        elif("MCT" in xyx):
                            sub_folder = "MCT"
                        elif("RTT" in xyx):
                            sub_folder = "RTT"
                        elif("PCT" in xyx):
                            sub_folder = "PCT"
                        else:
                            print("improper file name given for tool type")
                            continue
                        print ("sub_folder = ",sub_folder)
                        logging.info(f"sub_folder = {sub_folder}")

                        # print (xyx.find("AP"))
                        folder_name1 = "UNKNOWN"
                        if("SM_1P" in xyx):
                            folder_name1 = "ISM_1P"
                        elif("SM_3P" in xyx):
                            folder_name1 = "ISM_3P"
                        elif("AP_3P" in xyx):
                            folder_name1 = "CAP_3P"
                        elif("CU_" in xyx):
                            folder_name1 = "DCU_"
                        elif("garud" in xyx.lower()):
                            folder_name1 = "Garud"
                        elif("better" in xyx.lower()):
                            folder_name1 = "Better_Meter"
                        else:
                            print("improper file name given for Meter type")
                            continue
                        print("folder_name1 = ",folder_name1)
                        logging.info(f"folder_name1 = {folder_name1}")

                        if data_dict.get("IS_OFFLINE", 1) == 1:
                            uploaded = upload_to_aws(str(date_only), bucket_name, txt[j],sub_folder, time_only,folder_name1, cpu_serial_num )
                            print("FTT DATA SUCCESSFULLY UPLOADED TO CLOUD")
                            logging.info("FTT DATA SUCCESSFULLY UPLOADED TO CLOUD")
                        else:
                            print("FTT DATA SUCCESSFULLY SAVED TO LOCAL")
                            logging.info("FTT DATA SUCCESSFULLY SAVED TO LOCAL")


                    # ****************************************************************************************************************
                else:
                    print("Skipping to Upload the log file to server")
                    logging.info("Skipping to Upload the log file to server")
        except Exception as e:
            print(f"Error writing DB log: {str(e)}")
            logging.error(f"Error writing DB log: {str(e)}")

    else:
        try:
            if (len(temp_result_dict)) > 0:       # if the result file is empty then don't upload to server

                import boto3
                from botocore.exceptions import NoCredentialsError



                def upload_to_aws(local_folder, bucket, s3_file,sub_folder, file_time,folder_name1, cpu_serial_num):
                    s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                                    aws_secret_access_key=SECRET_KEY)

                    try:
                        key = str(cpu_serial_num + "_" +file_time + "_" + s3_file)
                        print("Uploaded to S3 Server...", key)
                        s3.upload_file(s3_file, bucket, folder_name +  "/{0}/{1}/{2}/{3}".format(folder_name1,sub_folder,local_folder, key))
                        print("Upload Successful")
                        os.remove(s3_file)
                        return True
                    except NoCredentialsError:
                        print("Credentials not available")
                        return False
                    except Exception as e:
                        print(e)
                        print("The file was not found")
                        return False


                al = os.listdir("./")
                txt = list(filter(lambda x: x[-5:] == '.xlsx',al))
                print(txt)
                if len(txt) == 0:
                    print("file doesn't exist")#/dev/gp-gateway"
                    return#args.baud_rate = 9600

                for j in range(len(txt)):
                    # today = date.today()
                    # print("Today date is: ", today)

                    file_time = datetime.datetime.now()
                    print("time = ",file_time)
                    date_only = datetime.datetime.strftime(file_time, '%Y-%m-%d')
                    time_only = datetime.datetime.strftime(file_time, '%H_%M_%S')
                    print("time is",time_only)
                    print("date is",date_only)

                    sub_folder = "UNKNOWN"
                    xyx =  str(txt[j])
                    if("PCT2" in xyx):
                        sub_folder = "PCT2"
                    elif("ftt" in xyx.lower()):
                        sub_folder = "FTT"
                    elif("MCT" in xyx):
                        sub_folder = "MCT"
                    elif("RTT" in xyx):
                        sub_folder = "RTT"
                    elif("PCT" in xyx):
                        sub_folder = "PCT"
                    else:
                        print("improper file name given for tool type")
                        continue
                    print ("sub_folder = ",sub_folder)

                    # print (xyx.find("AP"))
                    folder_name1 = "UNKNOWN"
                    if("SM_1P" in xyx):
                        folder_name1 = "ISM_1P"
                    elif("SM_3P" in xyx):
                        folder_name1 = "ISM_3P"
                    elif("AP_3P" in xyx):
                        folder_name1 = "CAP_3P"
                    elif("CU_" in xyx):
                        folder_name1 = "DCU_"
                    elif("garud" in xyx.lower()):
                        folder_name1 = "Garud"
                    elif("better" in xyx.lower()):
                        folder_name1 = "Better_Meter"
                    else:
                        print("improper file name given for Meter type")
                        continue
                    print("folder_name1 = ",folder_name1)

                    if data_dict.get("IS_OFFLINE", 1) == 1:
                        uploaded = upload_to_aws(str(date_only), bucket_name, txt[j],sub_folder, time_only,folder_name1, cpu_serial_num )
                        print("FTT DATA SUCCESSFULLY UPLOADED TO CLOUD")
                    else:
                        print("FTT DATA SUCCESSFULLY SAVED TO LOCAL")


                # ****************************************************************************************************************
            else:
                print("Skipping to Upload the log file to server")
        except Exception as e:
            print(f"Error Uploading log: {str(e)}")
            logging.error(f"Error Uploading log: {str(e)}")
    print(ftt_result)
    return ftt_result