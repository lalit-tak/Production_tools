from gp_node.network.network_api import NetworkAPI
from Test_cases_verificationClass import TestCasePCTMCT
import serial
import datetime
import time
import subprocess
from config import Config
import easygui
from fg23_prov import provision_nic_parameters, nic_provisioning
from multiprocessing import freeze_support
import logging
from logging.handlers import TimedRotatingFileHandler
import openpyxl
from colorama import Fore, Style, init
import sys
import os
import easygui
import pythoncom
import win32com.client
import threading
from threading import Thread
import pandas as pd
from queue import Queue
import db_connect
init(autoreset=True)

ACCESS_KEY = "PUT_YOUR_ACCESS_KEY_HERE"
SECRET_KEY = "PUT_YOUR_SECRET_KEY_HERE"
bucket_name = "PUT_YOUR_BUCKET_NAME_HERE"
folder_name = "PUT_YOUR_FOLDER_NAME_HERE"

global abort_threads
global portID

# ============================================================================
# DICTIONARY-BASED RESULT STORAGE
# ----------------------------------------------------------------------------
# The original script tracked every test step positionally: MeterInfo /
# result_list were built with .append() in a fixed hand-maintained order,
# PCT_Fail_list had to line up with result_list by index (via fail_indexes)
# to produce readable failure text, and run()'s PCB re-entry check poked
# entry[1][2] / entry[1][-1] / entry[2] -- magic indices into an opaque
# list-of-lists. Any of those lists gaining/losing an entry silently shifted
# every column/message after it.
#
# This version stores everything in named dictionaries instead, mirroring
# mct_multiport_logs.py:
#   meter_info : {'Meter PCB Serial No': ..., 'Live Version': ..., ...}
#   test_result: {'Factory Reset': 'pass', 'Factory Reset_Retry_Count': 1, ...}
#   result_log : {com_port: {'mac', 'meter_info', 'result', 'bookName',
#                             'fileName', 'com_port'}, ...}   <- keyed by COM
#                 port instead of being a plain list of entries.
#
# One deliberate naming deviation from "keep every header text identical":
# the original header lists reused the literal text 'Set Time' for BOTH a
# MeterInfo column (the actual time value written) and a result column (the
# pass/fail of setting it) -- harmless under the old positional writer,
# which never looked anything up by name, but a real bug under the new
# name-based add_log_xlsc/get_header_column_map (both writes would resolve
# to the same column and the meter_info value would be silently clobbered
# by the result value). The meter_info key is renamed to 'Set Time Value'
# to avoid that collision; the result step keeps the original 'Set Time'
# text. See get_pct_field_templates() below.
# ============================================================================

# ============================================================================
# THREADING INSTEAD OF MULTIPROCESSING
# ----------------------------------------------------------------------------
# run() used to spawn one multiprocessing.Process per COM port, coordinating
# through multiprocessing.Manager().list()/.dict()/.Event() proxies because
# separate processes don't share memory. Real threads do share memory, so
# run() now spawns one threading.Thread per COM port and hands them plain
# list/dict/threading.Event() objects directly -- no proxy needed. This also
# means the PCB re-entry check's `entry = result_dict.get(...)` now returns
# the *actual* shared dict (not a deep copy pickled across a process
# boundary), so mutating entry['result'][...] in place is visible to
# everyone without needing an explicit `result_dict[key] = entry` write-back
# (the original mismatch branch never did that write-back, which would have
# silently dropped the mutation under the old Manager-proxy scheme -- with
# real threads there's nothing to drop).
# ============================================================================


def close_excel_file(filepath):
    filepath = os.path.abspath(filepath)
    ext = os.path.splitext(filepath)[1].lower()

    # -----------------------------
    # Case 1: Excel files
    # -----------------------------
    if ext in (".xlsx", ".xls", ".xlsm"):
        pythoncom.CoInitialize()
        try:
            excel = win32com.client.GetObject(Class="Excel.Application")
        except Exception:
            return False

        for wb in excel.Workbooks:
            try:
                if wb.FullName.lower() == filepath.lower():
                    print("Closing Excel file:", filepath)
                    wb.Close(SaveChanges=False)
                    excel.Quit()
                    time.sleep(0.5)
                    return True
            except Exception:
                pass

        return False


def get_pct_field_templates(meter_type, toolName, is_rf_prov):
    """
    Returns (meter_info_keys, result_keys, fail_messages) for the fields
    main_function() populates for this meter_type/toolName/is_rf_prov
    combination -- the single source of truth that used to be hand-
    duplicated between addDefaultPCTLog's 6 branch header lists,
    main_function's append order, and PCT_Fail_list (which had to stay in
    perfect positional sync with result_list to produce readable failure
    text).

    meter_info_keys/result_keys use the *exact* header text the original
    branch lists used (e.g. 'Meter PCB Serial No', 'Factory Reset') so
    existing on-disk Excel logs stay backward-compatible -- with the one
    'Set Time' -> 'Set Time Value' exception documented in the module
    docstring above. Every step in result_keys is immediately followed by
    a named '<Step>_Retry_Count' sibling key -- the named replacement for
    the old interleaved 'retry_count_N' placeholders -- except for the
    final 'Meter PCB Serial Numebr Check' step, which is only ever set by
    run()'s PCB re-entry check (never inside main_function) and never had
    a retry count in the original header lists either.

    'Overall Result' is intentionally NOT included in meter_info_keys here
    (it's added separately by addDefaultPCTLog when building headers, and
    is deliberately never set inside main_function -- see
    finalize_overall_result()).
    """
    meter_type = meter_type.lower()
    toolName = toolName.lower()
    is_garud = 'garud' in meter_type
    is_rf_pct = 'rf_pct' in toolName
    is_prov = is_rf_pct and (str(is_rf_prov).strip() == '1')

    meter_info_keys = [
        'Date-time', 'Meter_SERIAL_NUM', 'Meter PCB Serial No', 'Nic PCB No',
        'Live Version', 'Internal Version',
        'CurrentV_with_Relay_On', 'CurrentN_with_Relay_On', 'Live_Tamper_with_Relay_On',
        'Set Time Value',
    ]
    result_steps = [
        'Factory Reset', 'Calibration Unlock', 'Meter Serial Num', 'Get Meter PCB No',
        'Get Nic PCB No', 'live version', 'Get Internal Version', 'Set Relay Mode',
        'Verify Current with Relay On', 'Relay Off', 'Set Time',
    ]
    fail_messages = {
        'Factory Reset': 'Fail in Factory Reset',
        'Calibration Unlock': 'Fail in Calib Unlock',
        'Meter Serial Num': 'Fail in set Meter Serial No',
        'Get Meter PCB No': 'Fail in set Meter PCB No',
        'Get Nic PCB No': 'Fail in Set NIC PCB No',
        'live version': 'Fail in Get live version',
        'Get Internal Version': 'Fail in Get Internal Version',
        'Set Relay Mode': 'Fail in Set Relay Mode',
        'Verify Current with Relay On': 'Fail in Verify Current with Relay On',
        'Relay Off': 'Fail in Relay Off',
        'Set Time': 'Fail in Set Time',
    }

    if is_garud:
        meter_info_keys += ['Bootloader Version']
        result_steps += ['Verify Bootloader Version']
        fail_messages['Verify Bootloader Version'] = 'Fail in Verify Bootloader Version'
    else:  # better
        meter_info_keys += ['Bootloader Version_1st', 'Bootloader Version_2nd']
        result_steps += ['Verify 1st Bootloader Version', 'Verify 2nd Bootloader Version']
        fail_messages['Verify 1st Bootloader Version'] = 'Fail in Verify 1st Bootloader Version'
        fail_messages['Verify 2nd Bootloader Version'] = 'Fail in Verify 2nd Bootloader Version'

    meter_info_keys += ['Current rating', 'Manufacturing Year', 'Payment Mode']
    result_steps += ['Set Current Rating', 'Set Manufacturing Year', 'Set Payment Mode']
    fail_messages['Set Current Rating'] = 'Fail in Set Current Rating'
    fail_messages['Set Manufacturing Year'] = 'Fail in Set Manufacturing Year'
    fail_messages['Set Payment Mode'] = 'Fail in Set Payment Mode'

    if is_garud:
        meter_info_keys += ['Hw Version']
        result_steps += ['Set Hw Version']
        fail_messages['Set Hw Version'] = 'Fail in Set Hw Version'

    meter_info_keys += ['Battery Voltage']
    result_steps += ['Verify Battery Voltage']
    fail_messages['Verify Battery Voltage'] = 'Fail in Verify Battery Voltage'

    meter_info_keys += ['CurrentV_with_Relay_Off', 'CurrentN_with_Relay_Off', 'Live_Tamper_with_Relay_Off']
    result_steps += ['Verify Current with Relay Off', 'Relay On']
    fail_messages['Verify Current with Relay Off'] = 'Fail in Verify Current with Relay Off'
    fail_messages['Relay On'] = 'Fail in Relay On'

    meter_info_keys += ['GPRS_Protocol_Value']
    result_steps += ['Set GPRS Protocol', 'Get GPRS Protocol']
    fail_messages['Set GPRS Protocol'] = 'Fail in Set GPRS Protocol'
    fail_messages['Get GPRS Protocol'] = 'Fail in Get GPRS Protocol'

    if is_prov:
        meter_info_keys += ['Set Provision Channel', 'Get Provision Channel']
        result_steps += ['Open Tunnel Mode', 'Set Provisioning to ch_9']
        fail_messages['Open Tunnel Mode'] = 'Fail in Open Tunnel Mode'
        fail_messages['Set Provisioning to ch_9'] = 'Fail in Provisioning to ch 9'

    result_steps += ['Meter PCB Serial Numebr Check']

    result_keys = []
    for step in result_steps:
        result_keys.append(step)
        if step != 'Meter PCB Serial Numebr Check':
            result_keys.append(f"{step}_Retry_Count")

    return meter_info_keys, result_keys, fail_messages


def build_log_entry(mac, meter_info, test_result, bookName, fileName, com_port=None):
    """Bundle one port's results into a single dictionary instead of the
    old positional 5-item list. Keys are self-describing, and com_port
    travels with the entry so run() can key result_dict by COM port
    without needing a second parallel structure."""
    return {
        'mac': mac,
        'meter_info': meter_info,
        'result': test_result,
        'bookName': bookName,
        'fileName': fileName,
        'com_port': com_port,
    }


def build_fail_messages(com_port, test_result, fail_message_lookup):
    """Named-key replacement for the old `PCT_Fail_list[idx] for idx in
    fail_indexes` pattern -- there is no positional index to keep in sync
    with result_list any more, so a step's failure text can never attach to
    the wrong step. Retry-count keys never match (their values are ints,
    never the string 'fail'), so they're naturally skipped here exactly
    like they were skipped by the old `if result == 'fail'` scan."""
    messages = []
    for step_key, value in test_result.items():
        if value == 'fail':
            text = fail_message_lookup.get(step_key, f"Fail in {step_key}")
            messages.append("COM Port: {}, {}".format(com_port, text))
    return messages


# Sentinel values written into the log when a step's real data was never
# recorded (worker crashed/exited a retry loop before reaching that step).
# A missing result step reads as 'fail', never a silent 'pass' -- untested
# must never look identical to tested-and-passed.
NOT_TESTED_METER_VALUE = None
NOT_TESTED_RESULT_VALUE = 'fail'


def fill_missing_fields(entry, meter_info_keys, result_keys):
    """Ensure every field in meter_info_keys/result_keys exists on `entry`,
    filling in NOT_TESTED_* defaults for anything main_function never got to
    write. This is what prevents the Excel "column mismatch" the old
    list-based script suffered from: if an exception path exited a retry
    loop without ever appending a value (or a whole block was skipped
    because of an unexpected exception), the row would otherwise be missing
    that field entirely. add_log_xlsc() already writes by header *name*
    rather than position, but a field simply absent from the dict still
    left a blank, unexplained cell. Calling this right before
    build_log_entry() guarantees every row has a value under every header."""
    for key in meter_info_keys:
        entry['meter_info'].setdefault(key, NOT_TESTED_METER_VALUE)
    for key in result_keys:
        entry['result'].setdefault(key, NOT_TESTED_RESULT_VALUE)


def finalize_overall_result(entry):
    """Single-entry version of the companion script's
    finalize_overall_results() -- PCT has no phase-1/phase-2 merge, but
    Overall Result still can't be computed inside main_function() because
    run()'s PCB re-entry check can flip a pass to a fail *after*
    main_function returns (a PCB serial number mismatch). Call this once,
    right before writing to Excel, so Overall Result always reflects the
    final state including any PCB mismatch."""
    entry['meter_info']['Overall Result'] = 'fail' if 'fail' in entry['result'].values() else 'pass'


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
    so a row's data can never land under the wrong header even if a
    branch's field order or count changes later. If a key isn't in the
    header yet, the sheet is extended with a new column instead of silently
    dropping the value."""
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

    write('MAC_ADDR', log_entry['mac'])
    write('Index', numRows - 1)
    for key, value in log_entry['meter_info'].items():
        write(key, value)
    for key, value in log_entry['result'].items():
        write(key, value)

    wb.save(loc)


def verify_log_xlsc(bookName,fileName):
    loc = bookName

    try:
        wb = openpyxl.load_workbook(loc)
        sheet = wb.active
        cell_value = sheet.cell(row=1, column=1).value
    except:
    # except Exception as e:
        # print("hi")
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
            for line in os.popen("ipconfig /all"):
                if line.lstrip().startswith('Physical Address'):
                    mac = line.split(':')[1].strip().replace('-',':')
                    break
        else:
            for line in os.popen("/sbin/ifconfig"):
                if line.find('Ether') > -1:
                    mac = line.split()[4]
                    break
        # print "Mac Address : ",mac
    except:
        msg = "MAC ADDRESS NOT FOUND"
        easygui.msgbox(msg, title = (str(toolName)+str("|| GRAMPOWER")))#title="METER CUSTOMISATION TOOL || GRAMPOWER")
        sys.exit("Restart Tool")
    return mac

def setup_logger(enable_file_log=False):
    log_folder = "Logs"
    os.makedirs(log_folder, exist_ok=True)
    log_file = os.path.join(log_folder, "PCT.log")

    logger = logging.getLogger()

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(logging.INFO)  # DEBUG generates too many writes

    # File handler — only in main process
    if enable_file_log:
        handler = TimedRotatingFileHandler(
            log_file, when="midnight", interval=1,
            backupCount=7, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(processName)s - %(levelname)s - %(message)s"
        ))
        logger.addHandler(handler)

def addDefaultPCTLog(bookName, fileName, meter_type, toolName, is_rf_prov):
    """Create the log workbook (if missing) and write its header row.
    Headers come from get_pct_field_templates(), so they always match the
    keys main_function() will populate -- no more 6 hand-written branch
    header lists (MeterInfo/result) to keep in sync with main_function's
    append order."""
    if not verify_log_xlsc(bookName, fileName):
        print("xlsx file for log not found. creating one to store test report")

        meter_info_keys, result_keys, _ = get_pct_field_templates(meter_type, toolName, is_rf_prov)
        meter_info_keys = meter_info_keys + ['Overall Result']

        wb = openpyxl.load_workbook(bookName)
        sheet = wb[fileName]

        headers = ['MAC_ADDR', 'Index'] + meter_info_keys + result_keys
        for col_idx, header in enumerate(headers, start=1):
            sheet.cell(row=1, column=col_idx).value = header

        wb.save(bookName)
        print("New xlsx file created with headers")

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
    total_failures = total_ports - total_unreachable - len(passes)
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

def run_provisioning_worker(queue, ser_initilizer, provisioning_param):
    try:
        nic_parameters_data, prov_success = provision_nic_parameters.run_provisioning(ser_initilizer, provisioning_param)
        queue.put((nic_parameters_data, prov_success))
    except Exception as e:
        queue.put(({}, False))

def run_provisioning_with_timeout(ser_initilizer, provisioning_param, timeout_seconds=5):
    """
    Fixed provisioning with proper timeout handling
    """
    queue = Queue()

    p = Thread(target=run_provisioning_worker, args=(queue, ser_initilizer, provisioning_param), daemon=False)
    p.daemon = False  # Ensure proper cleanup

    try:
        p.start()
        p.join(timeout=timeout_seconds)  # Use full timeout parameter

        if p.is_alive():
            logging.warning(f"Provisioning thread still alive after {timeout_seconds}s timeout")
            # Thread will continue in background, don't try to kill it
            return {}, False

        # Check if completed normally
        if not queue.empty():
            return queue.get()
        else:
            logging.warning("Provisioning completed but no result in queue")
            return {}, False

    except Exception as e:
        logging.error(f"Error in provisioning timeout handler: {str(e)}")
        return {}, False

def rf_meter_provisioning(ser, com_port, prov_channel = 9):
    """
    Fixed RF meter provisioning with better error handling
    """
    try:
        nic_parameters_data = {}
        prov_success = False
        # prov_channel = 9
        e_key = f"e{prov_channel}"*16
        d_key = f"e{prov_channel}"*16
        n_channel = str(prov_channel)
        n_add_hex = f"BABEC{prov_channel}"
        n_address = str(int(n_add_hex, 16))


        param_data = {
            'serial_port': com_port,
            'encryption_key': e_key,
            'authentication_key': d_key,
            'network_address': "12238537",
            'network_channel': n_channel,
            'node_address': "1"
        }

        logging.info(f"Provisioning started for com: {com_port}")

        # Run provisioning with timeout
        nic_parameters_data, prov_success = run_provisioning_with_timeout(ser, param_data, timeout_seconds=30)
        print(f"Provisioning Result: {nic_parameters_data}")

        logging.info(f"COM: {com_port}, Provisioning result: {nic_parameters_data}, status: {prov_success}")

        if len(nic_parameters_data) > 0:
            prov_channel = nic_parameters_data.get('WIREPAS_NETWORK_CHANNEL', 9)

        return prov_success, prov_channel

    except Exception as e:
        logging.error(f"Error in rf_meter_provisioning for {com_port}: {str(e)}")
        return False, 9


def main_function(com_port, data_json, meter_serial_num, pcb_serial_num, Nic_pcb_num,result_queue,abort_flag,result_log):
    setup_logger(enable_file_log=True)
    logging.info(f"user input:")
    logging.info(f"Meter serial number: {meter_serial_num}")
    logging.info(f"PCB serial number: {pcb_serial_num}")
    logging.info(f"NIC PCB serial number: {Nic_pcb_num}")
    ser = None

    try:
        ser = serial.Serial(com_port, baudrate=9600, timeout=10, write_timeout=10, exclusive=True)
        # ser = nic_provisioning.serial_initialization(com_port)
        if not ser:
            return 0
        portID=4
        network_api = NetworkAPI(ser, portID, "irda")
        cases = TestCasePCTMCT(ser,portID,data_json)
        toolName = data_json.get("TOOL_TYPE", 'rf_pct').lower()
        mac = get_system_mac_address(toolName.upper())
        is_excel_file_present = True
        meter_info = {}
        test_result = {}
        ResultFinal=''
        meter_type = data_json.get("METER_TYPE", "Garud_1PH").lower()
        bookName = meter_type.title()+"_"+toolName.upper()+"_LOG.xlsx"
        fileName = toolName.upper()+"_DATA_LOG"
        rf_meter_pass_status = 'fail'
        prov_success = False
        prov_ch = 9
        starttime = datetime.datetime.now()
        print ("\nStartTime:",starttime, com_port)
        initial_bytes = bytes([
            0xAA, 0x01, 0x82, 0x35, 0xC9, 0xFF, 0xFF, 0xFF,
            0xFF, 0x04, 0x04, 0x03, 0x82, 0x35, 0xBB, 0xD9, 0x78
            ])
        end_bytes = bytes([0xAA, 0xBB, 0xCC, 0xDD])
        START_ADDRESS = 0x0100
        METER_ADDRESS = "255.255.255.255"
        # packet_size = 128

        # network_api.enable_print_rxtx(Address(METER_ADDRESS))
        # print starttime
        # serial_num = '11223344'

        # Field templates for this meter_type/toolName/provision combination
        # -- single source of truth that replaces the old hand-maintained
        # PCT_Fail_list (which had to stay in perfect positional sync with
        # result_list to produce readable failure text).
        meter_info_keys, result_keys, fail_message_lookup = get_pct_field_templates(
            meter_type, toolName, str(data_json.get('IS_RF_CHANNEL_PROVISION', 0))
        )

        Date_time=datetime.datetime.now()
        meter_info['Date-time'] = Date_time
        addDefaultPCTLog(bookName,fileName, meter_type.lower(), toolName.lower(), str(data_json.get('IS_RF_CHANNEL_PROVISION', 0)))

        # Check com port status
        retryCnt = 3
        while retryCnt:
            logging.info(f"Check com port is open or not attempt{4-retryCnt} for com:{com_port}")
            try:
                check_port = cases.get_live_version_val_check_port()
                if 'Fail' == check_port:
                    msg = ["com port is unreachable:{}".format(com_port)]
                    # result_queue.append(1)
                    result_queue.append(msg)
                    if ser is not None:
                        ser.close()
                    print("ser close for port : {}".format(com_port))
                    logging.error(f"Com port is close, COM: {com_port}")
                    abort_flag.set()
                    # return
                retryCnt = 0
            except Exception as e:
                logging.info(f"Error to check com port status attempt{4-retryCnt}, error: {str(e)}, for com: {com_port}")
                retryCnt -= 1


        # Factory reset
        if str(data_json.get("Factory_Reset", True)) == str(False):
            print("\nSkipping to do Factory Reset")
            logging.info(f"Factory reset is skip for com: {com_port}")
            test_result['Factory Reset'] = 'pass'
            test_result['Factory Reset_Retry_Count'] = '0'
        else:
            retryCnt = 3
            while (retryCnt):
                try:
                    logging.info(f"Factory reset start for com: {com_port}, attempt: {4-retryCnt}, for com: {com_port}")
                    factory_reset_val1=cases.Factory_reset_val()
                    logging.info(f"Factory reset response for com: {com_port}, response: {factory_reset_val1}")
                    if factory_reset_val1.get("Result").lower() == 'fail':
                        test_result['Factory Reset'] = 'fail'
                    else:
                        test_result['Factory Reset'] = 'pass'
                    logging.info(f"Factory reset is done for com: {com_port}")
                    break
                except Exception as e:
                    logging.error(f"Error in factory reset for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1
            test_result['Factory Reset_Retry_Count'] = 4-retryCnt
            time.sleep(data_json.get("Fact_Reset_sleepTime", 5))

        # Check Calibration unlock status
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Calibration Unlock start for com: {com_port}")
            try:
                calibUnlock = cases.Calibration_unLock()
                if calibUnlock.get("Result").lower() == 'fail':
                    test_result['Calibration Unlock'] = 'fail'
                else:
                    test_result['Calibration Unlock'] = 'pass'
                logging.info(f"Sucessfully Calibration unlock for com: {com_port}, response: {calibUnlock}")
                # retryCnt = 0
                break
            except Exception as e:
                logging.error(f"Error in Calibarion unlock for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    test_result['Calibration Unlock'] = 'fail'
        test_result['Calibration Unlock_Retry_Count'] = 4-retryCnt

        # Set Meter Serial Number
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Set Meter Serial for com: {com_port}, attempt: {4-retryCnt}")
            try:
                meter_info['Meter_SERIAL_NUM'] = meter_serial_num
                MeterSerialNumSet=meter_serial_num[-8:]
                print (MeterSerialNumSet)
                sr_num = cases.Set_Meter_serial_number(int(MeterSerialNumSet))
                if sr_num.get("Result").lower() =='fail':
                    test_result['Meter Serial Num'] = 'fail'
                else:
                    test_result['Meter Serial Num'] = 'pass'
                logging.info(f"Sucessfully set meter serial number for com: {com_port}, Serial number: {meter_serial_num}")
                # retryCnt = 0
                break
            except Exception as e:
                logging.error(f"Error in set meter serial numebr for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    test_result['Meter Serial Num'] = 'fail'
        test_result['Meter Serial Num_Retry_Count'] = 4-retryCnt

        # Set PCB Serial number
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Set PCB Serial number for com: {com_port}, attempt: {4-retryCnt}")
            try:
                pcb_num = cases.Set_Meter_PCB_serial_number(pcb_serial_num)
                meter_info['Meter PCB Serial No'] = pcb_serial_num
                if pcb_num.get("Result").lower() =='fail':
                    test_result['Get Meter PCB No'] = 'fail'
                    logging.info(f"fail in Set pcb serial number for com: {com_port}, PCB Serial Number: {pcb_serial_num}")
                else:
                    test_result['Get Meter PCB No'] = 'pass'
                    logging.info(f"pcb serial number for com: {com_port}, pcb serial numbr: {pcb_serial_num}")
                # retryCnt = 0
                break
            except Exception as e:
                logging.error(f"Error to Set pcb serial number for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    test_result['Get Meter PCB No'] = 'fail'
        test_result['Get Meter PCB No_Retry_Count'] = 4-retryCnt

        # Set NIC Pcb Number
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Set NIC PCB Serial number for com: {com_port}, attempt: {4-retryCnt}")
            try:
                nic_pcb = cases.Set_nic_pcb_no(Nic_pcb_num)
                meter_info['Nic PCB No'] = Nic_pcb_num
                if nic_pcb.get("Result").lower() =='fail':
                    test_result['Get Nic PCB No'] = 'fail'
                    logging.info(f"fail in Set nic pcb serial number for com: {com_port}, NIC PCB number: {Nic_pcb_num}")
                else:
                    test_result['Get Nic PCB No'] = 'pass'
                    logging.info(f"nic pcb serial number for com: {com_port}, NIC PCB number: {Nic_pcb_num}")
                # retryCnt = 0
                break
            except Exception as e:
                logging.error(f"Error to Set pcb serial number for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    test_result['Get Nic PCB No'] = 'fail'
        test_result['Get Nic PCB No_Retry_Count'] = 4-retryCnt

        # Get Live Version
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Get Live version for com: {com_port}, attempt: {4-retryCnt}")
            try:
                version_live=cases.get_live_version_val()
                meter_info['Live Version'] = str(version_live)
                if version_live==data_json.get("LIVE_VERSION", 0000):
                    test_result['live version'] = 'pass'
                else:
                    test_result['live version'] = 'fail'
                logging.info(f"get Live version for com: {com_port}, response: {version_live}")
                # retryCnt = 0
                break
            except Exception as e:
                logging.error(f"Error in get Live version for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    test_result['live version'] = 'fail'
        test_result['live version_Retry_Count'] = 4-retryCnt

        # Check Internal Version
        if data_json.get("INTERNAL_VERSION", 0) == 0:
            print("\nSkipping to Get INTERNAL VERSION")
            logging.info(f"Skip internal version check for com: {com_port}")
            test_result['Get Internal Version'] = 'pass'
            test_result['Get Internal Version_Retry_Count'] = '0'
            meter_info['Internal Version'] = '0'
        else:
            retryCnt = 3
            while (retryCnt):
                logging.info(f"Get Inetrnal version for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    int_version=cases.get_internal_version_val()
                    if str(int_version)==str(data_json.get("INTERNAL_VERSION", 0)):
                        test_result['Get Internal Version'] = 'pass'
                        meter_info['Internal Version'] = str(int_version)
                    else:
                        test_result['Get Internal Version'] = 'fail'
                        meter_info['Internal Version'] = str(int_version)
                    logging.info(f"get internal version for com: {com_port}, response: {int_version}")
                    # retryCnt = 0
                    break
                except Exception as e:
                    logging.error(f"Error in get internal version for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1
                    if retryCnt == 0:
                        test_result['Get Internal Version'] = 'fail'
            test_result['Get Internal Version_Retry_Count'] = 4-retryCnt

        # Set Relay Mode (On/Off, Event Log)
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Set Relay Mode for com: {com_port}, attempt: {4-retryCnt}")
            try:
                relay_mode = cases.Set_Meter_RelayMode(5)
                if relay_mode.get("Result").lower() =='fail':
                    test_result['Set Relay Mode'] = 'fail'
                else:
                    test_result['Set Relay Mode'] = 'pass'
                logging.info(f"Set Relay Mode for com: {com_port}, response: {relay_mode}")
                # retryCnt = 0
                break
            except Exception as e:
                logging.error(f"Error in Set Relay Mode for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    test_result['Set Relay Mode'] = 'fail'
        test_result['Set Relay Mode_Retry_Count'] = 4-retryCnt

        # Verify Current Befor Relay Off
        # without better meter pct relay off code
        # retryCnt = 3
        # while (retryCnt):
        #     logging.info(f"Verify Current for com: {com_port}, attempt: {4-retryCnt}")
        #     try:
        #         check_current_on = cases.Verify_Current(float(data_json.get("I_PHASE_MIN", 0.0)),float(data_json.get("I_PHASE_MAX", 0.0)),IsOff = False)
        #         logging.info(f"Verify Current for com: {com_port}, response: {check_current_on}, retry count: {4-retryCnt}")
        #         if check_current_on.get("Result").lower() == 'fail':
        #             meter_info['CurrentV_with_Relay_On'] = str(check_current_on.get('CurrentV', 'None'))
        #             meter_info['CurrentN_with_Relay_On'] = str(check_current_on.get('CurrentN', 'None'))
        #             meter_info['Live_Tamper_with_Relay_On'] = str(check_current_on.get('live_tamper', 'None'))
        #             test_result['Verify Current with Relay On'] = 'fail'

        #         else:
        #             meter_info['CurrentV_with_Relay_On'] = str(check_current_on.get('CurrentV', 'None'))
        #             meter_info['CurrentN_with_Relay_On'] = str(check_current_on.get('CurrentN', 'None'))
        #             meter_info['Live_Tamper_with_Relay_On'] = str(check_current_on.get('live_tamper', 'None'))
        #             test_result['Verify Current with Relay On'] = 'pass'
        #         break
        #         # retryCnt = 0
        #     except Exception as e:
        #         logging.error(f"Error in Verify Current for com: {com_port}, error: {str(e)}")
        #         retryCnt = retryCnt-1
        #         if retryCnt == 0:
        #             meter_info['CurrentV_with_Relay_On'] = 'None'
        #             meter_info['CurrentN_with_Relay_On'] = 'None'
        #             meter_info['Live_Tamper_with_Relay_On'] = 'None'
        #             test_result['Verify Current with Relay On'] = 'fail'
        # test_result['Verify Current with Relay On_Retry_Count'] = 4-retryCnt
        
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Verify Current for com: {com_port}, attempt: {4-retryCnt}")
            try:
                check_current_on = cases.Verify_Current(float(data_json.get("I_PHASE_MIN", 0.0)),float(data_json.get("I_PHASE_MAX", 0.0)),IsOff = False)
                logging.info(f"Verify Current for com: {com_port}, response: {check_current_on}, retry count: {4-retryCnt}")
                if check_current_on.get("Result").lower() == 'fail':
                    meter_info['CurrentV_with_Relay_On'] = str(check_current_on.get('CurrentV', 'None'))
                    meter_info['CurrentN_with_Relay_On'] = str(check_current_on.get('CurrentN', 'None'))
                    meter_info['Live_Tamper_with_Relay_On'] = str(check_current_on.get('live_tamper', 'None'))
                    test_result['Verify Current with Relay On'] = 'fail'
                    if check_current_on.get("Retries",4) == data_json.get("RETRIES", 4):
                        break
                    else:
                        retryCnt = retryCnt-1
                        time.sleep(3)

                else:
                    meter_info['CurrentV_with_Relay_On'] = str(check_current_on.get('CurrentV', 'None'))
                    meter_info['CurrentN_with_Relay_On'] = str(check_current_on.get('CurrentN', 'None'))
                    meter_info['Live_Tamper_with_Relay_On'] = str(check_current_on.get('live_tamper', 'None'))
                    test_result['Verify Current with Relay On'] = 'pass'
                    break
                # retryCnt = 0
            except Exception as e:
                logging.error(f"Error in Verify Current for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    meter_info['CurrentV_with_Relay_On'] = 'None'
                    meter_info['CurrentN_with_Relay_On'] = 'None'
                    meter_info['Live_Tamper_with_Relay_On'] = 'None'
                    test_result['Verify Current with Relay On'] = 'fail'
        test_result['Verify Current with Relay On_Retry_Count'] = 4-retryCnt

        # Meter Relay off
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Meter Relay off for com: {com_port}, attempt: {4-retryCnt}")
            try:
                relay_off = cases.Meter_Relay_OFF()
                if relay_off.get("Result").lower() == 'fail':
                    test_result['Relay Off'] = 'fail'
                else:
                    test_result['Relay Off'] = 'pass'
                logging.info(f"Meter Relay off for com: {com_port}, response: {relay_off}")
                # retryCnt = 0
                break
            except Exception as e:
                logging.error(f"Error in Meter Relay off for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    test_result['Relay Off'] = 'fail'
        test_result['Relay Off_Retry_Count'] = 4-retryCnt

        # Set Time Value
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Set Time Value for com: {com_port}, attempt: {4-retryCnt}")
            try:
                set_time=cases.Set_time_val()
                if set_time.get("Result").lower() == 'fail':
                    meter_info['Set Time Value'] = 'None'
                    test_result['Set Time'] = 'fail'
                else:
                    meter_info['Set Time Value'] = 'now'
                    test_result['Set Time'] = 'pass'
                logging.info(f"Set Time Value for com: {com_port}, response: {set_time}")
                # retryCnt = 0
                break
            except Exception as e:
                logging.error(f"Error in Set Time Value for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    meter_info['Set Time Value'] = 'None'
                    test_result['Set Time'] = 'fail'
        test_result['Set Time_Retry_Count'] = 4-retryCnt

        # Get Bootloader Version
        if "better" in meter_type.lower():
            # Get 1st Bootloader version
            retryCnt = 3
            while (retryCnt):
                logging.info(f"Get 1st Bootloader Version for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    boot_version=cases.get_better_meter_bootloader_version_val(1, data_json.get("BOOTLOADER_VERSION", 0.0))
                    meter_info['Bootloader Version_1st'] = boot_version.get('bootloader_version', 'None')
                    if boot_version.get("Result").lower() == 'fail':
                        test_result['Verify 1st Bootloader Version'] = 'fail'
                    else:
                        test_result['Verify 1st Bootloader Version'] = 'pass'
                    # retryCnt = 0
                    break
                    logging.info(f"Get 1st Bootloader Version for com: {com_port}, response: {boot_version}")
                except Exception as e:
                    logging.error(f"Error in Get 1st Bootloader Version for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1
                    if retryCnt == 0:
                        meter_info['Bootloader Version_1st'] = 'None'
                        test_result['Verify 1st Bootloader Version'] = "fail"
            test_result['Verify 1st Bootloader Version_Retry_Count'] = 4-retryCnt

            # Get 2nd Bootloader Version
            retryCnt = 3
            while (retryCnt):
                logging.info(f"Get 2nd Bootloader Version for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    boot_version2=cases.get_better_meter_bootloader_version_val(2, data_json.get("BOOTLOADER_VERSION_2", 0.0))
                    meter_info['Bootloader Version_2nd'] = boot_version2.get('bootloader_version', 'None')
                    if boot_version2.get("Result").lower() == 'fail':
                        test_result['Verify 2nd Bootloader Version'] = 'fail'
                    else:
                        test_result['Verify 2nd Bootloader Version'] = 'pass'
                    # retryCnt = 0
                    break
                    logging.info(f"Get 2nd Bootloader Version for com: {com_port}, response: {boot_version2}")
                except Exception as e:
                    logging.error(f"Error in Get 2nd Bootloader Version for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1
                    if retryCnt == 0:
                        meter_info['Bootloader Version_2nd'] = 'None'
                        test_result['Verify 2nd Bootloader Version'] = "fail"
            test_result['Verify 2nd Bootloader Version_Retry_Count'] = 4-retryCnt

        else:
            retryCnt = 3
            while (retryCnt):
                logging.info(f"Get Bootloader Version for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    boot_version=cases.get_bootloader_version_val(data_json.get("BOOTLOADER_VERSION", 0.0))
                    if boot_version.get("Result").lower() == 'fail':
                        meter_info['Bootloader Version'] = boot_version.get('bootloader_version', 'None')
                        test_result['Verify Bootloader Version'] = 'fail'
                    else:
                        meter_info['Bootloader Version'] = boot_version.get('bootloader_version', 'None')
                        test_result['Verify Bootloader Version'] = 'pass'
                    # retryCnt = 0
                    break
                    logging.info(f"Get Bootloader Version for com: {com_port}, response: {boot_version}")
                except Exception as e:
                    logging.error(f"Error in Get Bootloader Version for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1
                    if retryCnt == 0:
                        meter_info['Bootloader Version'] = 'None'
                        test_result['Verify Bootloader Version'] = "fail"
            test_result['Verify Bootloader Version_Retry_Count'] = 4-retryCnt

        # Set current rating
        if str(data_json.get("CURRENT_RATING_SET", True)) == str(False):
            print("\nSkipping to Set current rating")
            logging.info(f"Skipping to Set current rating for com: {com_port}")
            meter_info['Current rating'] = 'None'
            test_result['Set Current Rating'] = 'pass'
            test_result['Set Current Rating_Retry_Count'] = '0'
        else:
            retryCnt = 3
            while (retryCnt):
                logging.info(f"Set current rating for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    set_Current_Rating=cases.Set_Current_rating(data_json.get("CURRENT_RATING", "(5-10) A"))
                    if set_Current_Rating.get("Result").lower() == 'fail':
                        meter_info['Current rating'] = "None"
                        test_result['Set Current Rating'] = 'fail'
                    else:
                        meter_info['Current rating'] = data_json.get("CURRENT_RATING", "(5-10) A")
                        test_result['Set Current Rating'] = 'pass'
                    # retryCnt = 0
                    break
                    logging.info(f"Set current rating for com: {com_port}, response: {set_Current_Rating}")
                except Exception as e:
                    logging.error(f"Error in Set current rating for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1
                    if retryCnt == 0:
                        meter_info['Current rating'] = "None"
                        test_result['Set Current Rating'] = 'fail'
            test_result['Set Current Rating_Retry_Count'] = 4-retryCnt

        # Set manufacturing year
        if str(data_json.get("MANUFACTURING_YEAR_SET", True)) == str(False):
            print("\nSkipping to set manufacturing year")
            logging.info(f"Skipping to set manufacturing year for com: {com_port}")
            meter_info['Manufacturing Year'] = '0000'
            test_result['Set Manufacturing Year'] = 'pass'
            test_result['Set Manufacturing Year_Retry_Count'] = '0'
        else:
            retryCnt = 3
            while (retryCnt):
                logging.info(f"set manufacturing year for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    set_manufacturing_year=cases.Set_manufacturing_year(data_json.get("MANUFACTURING_YEAR", 0000))
                    meter_info['Manufacturing Year'] = str(data_json.get("MANUFACTURING_YEAR", 0000))
                    if set_manufacturing_year.get("Result").lower() == 'fail':
                        test_result['Set Manufacturing Year'] = 'fail'
                    else:
                        test_result['Set Manufacturing Year'] = 'pass'
                    # retryCnt = 0
                    break
                    logging.info(f"set manufacturing year for com: {com_port}, response: {set_manufacturing_year}")
                except Exception as e:
                    logging.error(f"Error in set manufacturing year for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1
                    if retryCnt == 0:
                        meter_info['Manufacturing Year'] = '0000'
                        test_result['Set Manufacturing Year'] = 'fail'
            test_result['Set Manufacturing Year_Retry_Count'] = 4-retryCnt

        # set payment mode
        if str(data_json.get("PAYMENT_MODE_SET", True)) == str(False):
            print("\nSkipping to set payment mode")
            logging.info(f"Skipping to set payment mode for com: {com_port}")
            test_result['Set Payment Mode'] = 'pass'
            test_result['Set Payment Mode_Retry_Count'] = '0'
            meter_info['Payment Mode'] = 'None'
        else:
            retryCnt = 3
            while (retryCnt):
                logging.info(f"set payment mode for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    set_pay_mode=cases.Set_payment_mode(data_json.get("PAYMENT_MODE", 1))
                    meter_info['Payment Mode'] = data_json.get('PAYMENT_MODE', 'None')
                    if set_pay_mode.get("Result").lower() == 'fail':
                        # MeterInfo.append('None')
                        test_result['Set Payment Mode'] = 'fail'
                    else:
                        test_result['Set Payment Mode'] = 'pass'
                    # retryCnt = 0
                    break
                    logging.info(f"set payment mode for com: {com_port}, response: {set_pay_mode}")
                except Exception as e:
                    logging.error(f"Error in set payment mode for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1
                    if retryCnt == 0:
                        meter_info['Payment Mode'] = 'None'
                        test_result['Set Payment Mode'] = 'fail'
            test_result['Set Payment Mode_Retry_Count'] = 4-retryCnt

        # set Hardware version
        if "garud" in meter_type.lower():
            if str(data_json.get("Set_Hardware_version", True)) == str(False):
                print("\nSkipping to set Hardware version")
                logging.info(f"Skipping to set Hardware version for com: {com_port}")
                test_result['Set Hw Version'] = 'pass'
                test_result['Set Hw Version_Retry_Count'] = '0'
                meter_info['Hw Version'] = 'None'
            else:
                retryCnt = 3
                while (retryCnt):
                    logging.info(f"set Hardware version for com: {com_port}, attempt: {4-retryCnt}")
                    try:
                        set_hw_version=cases.set_hardware_version(5)
                        if set_hw_version.get("Result").lower() == 'fail':
                            meter_info['Hw Version'] = 'None'
                            test_result['Set Hw Version'] = 'fail'
                        else:
                            meter_info['Hw Version'] = 5
                            test_result['Set Hw Version'] = 'pass'
                        # retryCnt = 0
                        break
                        logging.info(f"set Hardware version for com: {com_port}, response: {set_hw_version}")
                    except Exception as e:
                        logging.error(f"Error in set Hardware version for com: {com_port}, error: {str(e)}")
                        retryCnt = retryCnt-1
                        if retryCnt == 0:
                            meter_info['Hw Version'] = 'None'
                            test_result['Set Hw Version'] = 'fail'
                test_result['Set Hw Version_Retry_Count'] = 4-retryCnt

        # check battery volt 3.0
        if str(data_json.get("verify_battery_volt", True)) == str(False):
            print("\nSkipping to verify Battery Voltage")
            logging.info(f"Skipping to verify Battery Voltage for com: {com_port}")
            test_result['Verify Battery Voltage'] = 'pass'
            test_result['Verify Battery Voltage_Retry_Count'] = '0'
            meter_info['Battery Voltage'] = 'None'
        else:
            retryCnt = 3
            while (retryCnt):
                logging.info(f"verify Battery Voltage for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    check_battery_volt=cases.Verify_Batt_volt()
                    meter_info['Battery Voltage'] = check_battery_volt.get('Bettery_voltage', 'None')
                    if check_battery_volt.get("Result").lower() == 'fail':
                        test_result['Verify Battery Voltage'] = 'fail'
                    else:
                        test_result['Verify Battery Voltage'] = 'pass'
                    # retryCnt = 0
                    break
                    logging.info(f"verify Battery Voltage for com: {com_port}, response: {check_battery_volt}")
                except Exception as e:
                    logging.error(f"Error in verify Battery Voltage for com: {com_port}, error: {str(e)}")
                    retryCnt = retryCnt-1
                    if retryCnt == 0:
                        meter_info['Battery Voltage'] = 'None'
                        test_result['Verify Battery Voltage'] = 'fail'
            test_result['Verify Battery Voltage_Retry_Count'] = 4-retryCnt

        time.sleep(2)    #time delay to settle phase current and nuetral current to 0 after relay off

        # Verify Current Value with Relay Off
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Verify Current Value with Relay Off for com: {com_port}, attempt: {4-retryCnt}")
            try:
                # check_current_off = cases.Verify_Current(data_json.get("I_PHASE_MIN", 0.0),data_json.get("I_PHASE_MAX", 0.0),IsOff=False)
                check_current_off = cases.Verify_Current(0.0,0.0,IsOff=True)
                if check_current_off.get("Result").lower() == 'fail':
                    meter_info['CurrentV_with_Relay_Off'] = str(check_current_off.get('CurrentV', 'None'))
                    meter_info['CurrentN_with_Relay_Off'] = str(check_current_off.get('CurrentN', 'None'))
                    meter_info['Live_Tamper_with_Relay_Off'] = str(check_current_off.get('live_tamper', 'None'))
                    test_result['Verify Current with Relay Off'] = 'fail'
                else:
                    meter_info['CurrentV_with_Relay_Off'] = str(check_current_off.get('CurrentV', 'None'))
                    meter_info['CurrentN_with_Relay_Off'] = str(check_current_off.get('CurrentN', 'None'))
                    meter_info['Live_Tamper_with_Relay_Off'] = str(check_current_off.get('live_tamper', 'None'))
                    test_result['Verify Current with Relay Off'] = 'pass'
                logging.info(f"Verify Current Value for com: {com_port} = {check_current_off}")
                # retryCnt = 0
                break

            except Exception as e:
                logging.error(f"Error in Verify Current with Relay Off for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    meter_info['CurrentV_with_Relay_Off'] = 'None'
                    meter_info['CurrentN_with_Relay_Off'] = 'None'
                    meter_info['Live_Tamper_with_Relay_Off'] = 'None'
                    test_result['Verify Current with Relay Off'] = 'fail'
        test_result['Verify Current with Relay Off_Retry_Count'] = 4-retryCnt

        # Meter Relay On
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Meter Relay on for com: {com_port}, attempt: {4-retryCnt}")
            try:
                relay_on = cases.Meter_Relay_On()
                if relay_on.get("Result").lower() == 'fail':
                    test_result['Relay On'] = 'fail'
                else:
                    test_result['Relay On'] = 'pass'
                    logging.info(f"Meter Relay on for com: {com_port} ")
                # retryCnt = 0
                break
            except Exception as e:
                logging.error(f"Error in Meter relay on for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    test_result['Relay On'] = 'fail'
        test_result['Relay On_Retry_Count'] = 4-retryCnt

        # Set GPRS Protocol value
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Set GPRS Protocol Value for com: {com_port}, attempt: {4-retryCnt}")
            try:
                set_gprs_proto = cases.set_gprs_protocol(data_json.get("Set_gprs_protocol", 1))
                if set_gprs_proto.get("Result").lower() == 'fail':
                    test_result['Set GPRS Protocol'] = 'fail'
                else:
                    test_result['Set GPRS Protocol'] = 'pass'
                logging.info(f"Set GPRS protocol value for com: {com_port} = {set_gprs_proto}")
                # retryCnt = 0
                break
            except Exception as e:
                logging.error(f"Error in set GPRS Protocol value for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    test_result['Set GPRS Protocol'] = 'fail'
        test_result['Set GPRS Protocol_Retry_Count'] = 4-retryCnt

        # Get Gprs Protocol Value
        retryCnt = 3
        while (retryCnt):
            logging.info(f"Check GPRS Protocol Value for com: {com_port}, attempt: {4-retryCnt}")
            try:
                get_gprs_proto = cases.get_gprs_protocol(data_json.get("Set_gprs_protocol", 1))
                meter_info['GPRS_Protocol_Value'] = str(get_gprs_proto.get('Protocol', 'None'))
                if get_gprs_proto.get("Result").lower()=='fail':
                    test_result['Get GPRS Protocol'] = 'fail'
                else:
                    test_result['Get GPRS Protocol'] = 'pass'
                logging.info(f"GPRS protocol value for com: {com_port} = {get_gprs_proto}")
                # retryCnt = 0
                break
            except Exception as e:
                logging.error(f"Error in get GPRS Protocol value for com: {com_port}, error: {str(e)}")
                retryCnt = retryCnt-1
                if retryCnt == 0:
                    meter_info['GPRS_Protocol_Value'] = 'None'
                    test_result['Get GPRS Protocol'] = 'fail'
        test_result['Get GPRS Protocol_Retry_Count'] = 4-retryCnt

        time.sleep(2)    #time delay to settle after meter reset

        # if toolName.lower() == 'rf_pct':
        debug_status = False
        if (toolName.lower() == 'rf_pct') and (str(data_json.get('IS_RF_CHANNEL_PROVISION', 0)) == "1"):
            retryCnt = 3
            while (retryCnt > 0):
                logging.info(f"Set Tunnel Mode for com: {com_port}, attempt: {4-retryCnt}")
                try:
                    debug_status = cases.set_tunnel_mode()
                    if debug_status.get("Result").lower() == 'fail':
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
                        # break
                        test_result['Open Tunnel Mode'] = "pass"

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

            if (debug_status.get("Result").lower() != 'fail'):
                test_result['Open Tunnel Mode_Retry_Count'] = 4-retryCnt
                try:
                    prov_success, prov_ch = rf_meter_provisioning(ser, com_port, data_json.get("RF_CHANNEL", 9))
                except Exception as e:
                    logging.error(f"Error in RF meter provisioning for com: {com_port}, error: {str(e)}")
                    prov_success = False
                    prov_ch = "None"
                # Close Tunnel Mode
            else:
                test_result['Open Tunnel Mode_Retry_Count'] = 4-retryCnt
                test_result['Open Tunnel Mode'] = "fail"
                rf_meter_pass_status = 'fail'
                prov_ch = "None"

            print("🔄 Sending end bytes...")
            retryCnt = 3
            while retryCnt > 0:
                try:
                    logging.info(f"Closing Tunnel mode for com: {com_port}, attempt: {4-retryCnt}")
                    print("Sending Command to Close Tunnel Mode")
                    ser.write(end_bytes)
                    retryCnt -= 1
                except Exception as e:
                    break
                    print("Not Able to Close Tunnel Mode")
                    logging.info(f"Error in Closing Tunnel mode for com: {com_port}, error: {str(e)}")
                    msg = [f"COM: {com_port} Not Able to Close Tunnel Mode"]
                    # result_queue.append(msg)
                    result_queue.put((com_port.lower(), msg))
                    abort_flag.set()
                    return
            print("✅ End bytes sent.")
            if prov_success:
                rf_meter_pass_status = 'pass'
            else:
                rf_meter_pass_status = 'fail'
            logging.info(f"Get provisioning result\n Status: {prov_success} \n channel num: {prov_ch} ")
            meter_info['Set Provision Channel'] = '9'
            meter_info['Get Provision Channel'] = prov_ch
            test_result['Set Provisioning to ch_9'] = rf_meter_pass_status
            test_result['Set Provisioning to ch_9_Retry_Count'] = 1


        # Overall Result is intentionally NOT computed here -- run()'s PCB
        # re-entry check happens AFTER main_function returns and can flip a
        # pass to a fail (PCB serial mismatch), so finalize_overall_result()
        # computes it once, in run(), from the final state of test_result.

        ser.close()

        entry = build_log_entry(mac, meter_info, test_result, bookName, fileName, com_port)
        # 'Meter PCB Serial Numebr Check' is only ever decided later, by
        # run()'s PCB re-entry check -- defaulting it here like every other
        # result key would make build_fail_messages() below treat that
        # not-yet-performed check as a real failure and queue a premature
        # "Fail in Meter PCB Serial Numebr Check" message, even on a run
        # that ultimately re-enters correctly and passes. Exclude it from
        # this fill so it stays genuinely absent from test_result until
        # run() sets it for real.
        fill_missing_fields(entry, meter_info_keys, [k for k in result_keys if k != 'Meter PCB Serial Numebr Check'])
        result_log[com_port.lower()] = entry

        time.sleep(0.1)

        EndTime = datetime.datetime.now()
        print ("\nStartTime:",starttime)
        print ("EndTime:",EndTime)
        print ("Diff : ", EndTime - starttime)

        fail_messages = build_fail_messages(com_port, test_result, fail_message_lookup)
        if fail_messages:
            result_queue.append(fail_messages)

    except Exception as e:
        print("Error:", e)
        logging.error(f"Error in main function for com: {com_port}, error: {str(e)}")
        # msg = ["com port is unreachable:{}".format(com_port)]
        result_queue.append(["com port is unreachable:{}".format(com_port)])
        if ser is not None:
            ser.close()
        return

# def get_bios_serial():
#     try:
#         result = subprocess.check_output(
#             ["wmic", "bios", "get", "serialnumber"],
#             stderr=subprocess.STDOUT,
#             text=True
#         )

#         # Clean output
#         lines = result.strip().split("\n")
#         # print(lines)
#         if len(lines) >= 2:
#             serial = lines[-1].strip()
#             return serial
#         else:
#             return "1111111111"

#     except subprocess.CalledProcessError as e:
#         print("Error:", e)
#         return "1111111111"

# Getting serial number from powershell
def get_bios_serial():
    try:
        result = subprocess.check_output(
            [
                "powershell",
                "-Command",
                "Get-CimInstance Win32_BIOS | Select-Object -ExpandProperty SerialNumber"
            ],
            stderr=subprocess.STDOUT,
            text=True
        )

        serial = result.strip()

        if serial:
            return serial
        else:
            return "1111111111"

    except subprocess.CalledProcessError as e:
        print("Error:", e)
        return "1111111111"


def run(data_json, list_port):

    toolName = data_json.get("TOOL_TYPE", 'rf_pct').lower()
    meter_type = data_json.get("METER_TYPE", "Garud_1PH").lower()
    bookName = meter_type.title()+"_"+toolName.upper()+"_LOG.xlsx"
    fileName = toolName.upper()+"_DATA_LOG"
    port_inputs = []
    results = []
    result_dict = {}
    abort_flag = threading.Event()
    # addDefaultPCTLog(bookName,fileName, data_json.get("METER_TYPE", '').lower(), data_json.get("TOOL_TYPE", '').lower(), str(data_json.get('IS_RF_CHANNEL_PROVISION', 0)))

    for i, port in enumerate(list_port):

    # to take input for position 1 meter
        while True:
            com_port = input("Enter COM port for Position {} (COM{}): ".format(i+1, port)).lower()
            # com_port1=input("Enter Com port of First Position(Ex.comx etc): ").lower()
            if com_port.lower() == "com{}".format(port).lower():
                break
            else:
                print("Wrong COM port scanned for position {}".format(i+1))
                logging.info(f"Wrong position of com port scanned please scan meter at position {i+1}")

        while True:
            meter_pcb = input("Eneter Meter PCB serial No (Ex.(FOR PCB P24101301000000100210000001...... etc): ")
            # Meter_pcb_serial_no1=input("Eneter Meter PCB serial No (Ex.FOR PCB V1.6.1 --- R161XXXX AND FOR PCB V1.6.4 -- P24101301000000100210000001...... etc): ")
            if ((str(meter_pcb[0:4]) == 'R161') or (str(meter_pcb[0:4]) == 'r161') or (str(meter_pcb[9:16]) == str(data_json.get("Main_PCB_SFG_Prefix", 0000000)))):
                break
            else:
                print("Invalid Format of Meter PCB Serial Num,Enter in this Format(Ex.FOR PCB V1.6.1 --- R161XXXX AND FOR PCB V1.6.4 -- P24101301000000100210000001...... etc)")
                logging.info(f"Invalid Format of Meter PCB Serial Num at position {i+1},Enter in this Format(Ex.FOR PCB V1.6.1 --- R161XXXX AND FOR PCB V1.6.4 -- P24101301000000100210000001...... etc)")

        while True:
            if((len(meter_pcb)>12) and str(meter_pcb[-8:]).isdigit()) :
                meter_serial = meter_pcb[-8:]
                break
            else:
                print("Meter PCB Serial Num length should be greater than 12 and last Eight Digits should be decimal only")
                print("Restart the tool as Meter PCB Serial Num length should be greater than 12 and last Eight Digits should be decimal only Failures Detected")
                logging.info("Meter PCB Serial Num length should be greater than 12 and last Eight Digits should be decimal only")
                logging.info("Restart the tool as Meter PCB Serial Num length should be greater than 12 and last Eight Digits should be decimal only Failures Detected")
                return

        while True:
            nic_pcb = input("Eneter NIC PCB serial No (Ex. P24101301000000400310000001 etc): ")
            if((str(nic_pcb[0:4]) == 'R154') or (str(nic_pcb[0:4]) == 'r154') or (str(nic_pcb[0:4]) == 'r144') or (str(nic_pcb[0:4]) == 'R144') or (str(nic_pcb[9:16]) == str(data_json.get("NIC_PCB_SFG_PREFIX", 0000000)))):
                break
            else:
                print("Invalid Format of NIC PCB Serial Num,Enter in this Format(Ex.R154XXXX...... or P24101301000000400310000001 or R144XXXX......etc)")
                logging.info(f"Invalid Format of NIC PCB Serial Num at {i+1} position,Enter in this Format(Ex.R154XXXX...... or P24101301000000400310000001 or R144XXXX......etc)")

        port_inputs.append((com_port.lower(), meter_serial, meter_pcb, nic_pcb))


    input("Press Enter to start the script........")


    starttimepct=datetime.datetime.now()

    # results = []
    # result_dict = {}



    threads  = []

    print("\n========== STARTING TESTING ==========\n")

    # -----------------------------
    # Create Thread For Each Port
    # -----------------------------
    for port_data in port_inputs:

        p = Thread(
            target=main_function,
            args=(
                port_data[0],  # com_port
                data_json,     # configuration data
                port_data[1],  # meter_serial
                port_data[2],  # pcb_serial
                port_data[3],  # nic pcb
                results,
                abort_flag,
                result_dict
            )
        )

        threads.append(p)

    # -----------------------------
    # Start Threads
    # -----------------------------
    for p in threads:
        p.start()
        time.sleep(data_json.get("thread_time_delay", 1))

    # -----------------------------
    # Wait For Completion
    # -----------------------------
    for p in threads:
        p.join()
    print("\n========== ALL PORTS COMPLETED ==========\n")

    print("\n========== VERIFY PCB SERIAL NUMBER ==========\n")


    logging.info("\n========== ALL PORTS COMPLETED ==========\n")
    logging.info("\n========== VERIFY PCB SERIAL NUMBER ==========\n")

    reentered_pcbs = {}
    if len(result_dict) != 0:
        for port in list_port:

            while True:

                meter_pcb_reenter = input(
                    "\nRe-Enter Meter PCB serial No for COM{}: ".format(port)
                )

                if str(meter_pcb_reenter[9:16]) == str(data_json.get("Main_PCB_SFG_Prefix", 0000000)):

                    reentered_pcbs[port] = meter_pcb_reenter
                    break

                else:
                    print("Invalid Format of Meter PCB Serial Num,Enter in this Format(Ex.FOR PCB V1.6.1 --- R161XXXX AND FOR PCB V1.6.4 -- P24101301000000100210000001...... etc)")
                    logging.error(f"Invalid Format of Meter PCB Serial Num at COM{port},Enter in this Format(Ex.FOR PCB V1.6.1 --- R161XXXX AND FOR PCB V1.6.4 -- P24101301000000100210000001...... etc)")
    else:
        fail_messages = ["COM Port is not connected for all ports or meter is not connected"]
        results.append(fail_messages)

    logging.info(f"Again input PCB Serial Verification: {reentered_pcbs}")

    for port in list_port:
        com_port = f"com{port}"
        if len(result_dict) == 0:
            results.append(fail_messages)
            continue

        entry_found = False
        entry = result_dict.get(com_port, None)

        meter_pcb_reenter = reentered_pcbs.get(port, '')
        if entry is None:
            print(f"Warning: No result found for COM{port}")
            continue
        # Named lookup replaces the old entry[1][2] magic index into
        # MeterInfo (the 3rd positional item happened to be the PCB
        # serial) -- 'Meter PCB Serial No' is the actual field name and
        # can't silently point at the wrong column if a branch's field
        # order ever changes.
        target_value = entry['meter_info'].get('Meter PCB Serial No')

        if str(meter_pcb_reenter) == str(target_value):
            entry['result']['Meter PCB Serial Numebr Check'] = 'pass'
            entry_found = True
            # Overall Result hasn't been finalized yet (that happens once,
            # below, after this whole PCB-check loop) -- so "was the test
            # otherwise passing" is read directly off whether any step in
            # entry['result'] is still 'fail', instead of the old
            # entry[1][-1] == 'pass' check against a not-yet-final value.
            if 'fail' not in entry['result'].values():
                pass_messages = ["PASS: COM{}".format(port)]
                results.append(pass_messages)
            else:
                fail_messages = ["COM Port: {}, Meter test failed".format("COM{}".format(port))]
                results.append(fail_messages)
            result_dict[f"com{port}"] = entry

        # -----------------------------------
        # PCB mismatch case
        # -----------------------------------
        if not entry_found:
            entry = result_dict.get(f"com{port}")
            entry['result']['Meter PCB Serial Numebr Check'] = 'fail'

            fail_messages = [
                "COM Port: {}, Fail in PCB Serial No Mismatch between Printed Meter PCB Serial No and Inside Meter PCB Serial No".format(
                    "COM{}".format(port)
                )
            ]

            results.append(fail_messages)

        # Overall Result is computed once here, from the (possibly just
        # PCB-check-updated) result dict, so it always reflects the final
        # pass/fail state regardless of which branch above ran.
        finalize_overall_result(entry)


    # -----------------------------
    # Save Logs To Excel
    # -----------------------------
    if len(result_dict) != 0:

        # for entry in result_dict:
        for port in list_port:
            entry = result_dict.get(f"com{port}")
            # print(entry)
            # print(len(entry['result']))
            if entry is None:
                continue

            try:
                close_excel_file(bookName)
                add_log_xlsc(entry)

            except Exception as e:
                print(f"Error writing Excel log: {str(e)}")


    if data_json.get("IS_DATA_CONN", 1) == 1:
        df_frame = pd.read_excel(bookName)
        print(df_frame)
        try:
            status = False
            error = ""
            if 'better' in meter_type.lower():
                if (str(data_json.get('IS_RF_CHANNEL_PROVISION', 0)) == '1') and ('rf' in str(toolName.lower())):
                    status, error = db_connect.upload_dataframe(df_frame, 'better', 'rf')
                else:
                    status, error = db_connect.upload_dataframe(df_frame, 'better', '4g')
            else:
                if (str(data_json.get('IS_RF_CHANNEL_PROVISION', 0)) == '1') and ('rf' in str(toolName.lower())):
                    status, error = db_connect.upload_dataframe(df_frame, 'garud', 'rf')
                else:
                    status, error = db_connect.upload_dataframe(df_frame, 'garud', '4g')
            if not status:
                print(f"DB upload failed . Saved locally for retry. Error: {error}")
            else:
                # if(len(result_dict) != 0):       # if the result file is empty then don't upload to server
                if len(result_dict) != 0:



                    import boto3
                    from botocore.exceptions import NoCredentialsError

                    


                    def upload_to_aws(local_folder, bucket, s3_file,sub_folder, file_time,folder_name1):
                        s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                                        aws_secret_access_key=SECRET_KEY)
                        cpu_serial_num = get_bios_serial()
                        logging.info(f"Uploaded file: {str(cpu_serial_num + "_" + file_time + "_" + s3_file)}")

                        try:
                            s3.upload_file(s3_file, bucket, folder_name +  "/{0}/{1}/{2}/{3}".format(folder_name1,sub_folder,local_folder, str(cpu_serial_num + "_" + file_time + "_" + s3_file)))
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
                    print (txt)
                    logging.info(txt)
                    if len(txt) == 0:
                        print("file doesn't exist")
                        return

                    for j in range(len(txt)):
                        xyz_time = datetime.datetime.now()
                        print ("time = ",xyz_time)
                        date_only = datetime.datetime.strftime(xyz_time, '%Y-%m-%d')
                        time_only = datetime.datetime.strftime(xyz_time, '%H_%M_%S')
                        print("time is",time_only)
                        print("date is",date_only)

                        sub_folder = "UNKNOWN"
                        xyx =  str(txt[j])
                        if('pct' in xyx.lower()):
                            sub_folder = "PCT"
                        elif('4g_mct' in xyx.lower()):
                            sub_folder = "4G_MCT"
                        elif('img_mct' in xyx.lower()):
                            sub_folder = "IMG_MCT"
                        elif('rtt' in xyx.lower()):
                            sub_folder = "RTT"
                        else:
                            print("improper file name given for tool type")
                            continue
                        print ("sub_folder = ",sub_folder)
                        logging.info(f"sub_folder = {sub_folder}")

                        # print (xyx.find("AP"))
                        folder_name1 = "UNKNOWN"
                        if('sm_1p' in xyx.lower()):
                            folder_name1 = "ISM_1P"
                        elif('sm_3p' in xyx.lower()):
                            folder_name1 = "ISM_3P"
                        elif('ap_1p' in xyx.lower()):
                            folder_name1 = "CAP_3P"
                        elif('cu_' in xyx.lower()):
                            folder_name1 = "DCU_"
                        elif('garud' in xyx.lower()):
                            folder_name1 = "Garud"
                        elif('better' in xyx.lower()):
                            folder_name1 = "Better_Meter"
                        elif('ltct' in xyx.lower()):
                            folder_name1 = "3PLTCT"
                        elif('wc' in xyx.lower()):
                            folder_name1 = "3PWC"
                        else:
                            print("improper file name given for Meter type")
                            continue
                        logging.info(f"folder_name1 = {folder_name1}")
                        print(f"folder_name1 = {folder_name1}")

                        uploaded = upload_to_aws(str(date_only), bucket_name, txt[j],sub_folder, time_only,folder_name1 )
                else:
                    logging.info("Skipping to Upload the log file to server")


        except Exception as e:
            print(f"Error writing DB log: {str(e)}")
            logging.error(f"Error writing DB log: {str(e)}")

    elif data_json.get("IS_DATA_CONN", 1) == 0:
        try:
            if len(result_dict) != 0:
                import boto3
                from botocore.exceptions import NoCredentialsError
                def upload_to_aws(local_folder, bucket, s3_file,sub_folder, file_time,folder_name1):
                    s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY,aws_secret_access_key=SECRET_KEY)
                    cpu_serial_num = get_bios_serial()
                    logging.info(f"Uploaded file: {str(cpu_serial_num + "_" + file_time + "_" + s3_file)}")

                    try:
                        s3.upload_file(s3_file, bucket, folder_name +  "/{0}/{1}/{2}/{3}".format(folder_name1,sub_folder,local_folder, str(cpu_serial_num + "_" + file_time + "_" + s3_file)))
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
                print (txt)
                if len(txt) == 0:
                    print("file doesn't exist")
                    return

                for j in range(len(txt)):
                    xyz_time = datetime.datetime.now()
                    print ("time = ",xyz_time)
                    date_only = datetime.datetime.strftime(xyz_time, '%Y-%m-%d')
                    time_only = datetime.datetime.strftime(xyz_time, '%H_%M_%S')
                    print("time is",time_only)
                    print("date is",date_only)

                    sub_folder = "UNKNOWN"
                    xyx =  str(txt[j])
                    if('pct' in xyx.lower()):
                        sub_folder = "PCT"
                    elif('4g_mct' in xyx.lower()):
                        sub_folder = "4G_MCT"
                    elif('img_mct' in xyx.lower()):
                        sub_folder = "IMG_MCT"
                    elif('rtt' in xyx.lower()):
                        sub_folder = "RTT"
                    else:
                        print("improper file name given for tool type")
                        continue
                    print ("sub_folder = ",sub_folder)

                    folder_name1 = "UNKNOWN"
                    if('sm_1p' in xyx.lower()):
                        folder_name1 = "ISM_1P"
                    elif('sm_3p' in xyx.lower()):
                        folder_name1 = "ISM_3P"
                    elif('ap_1p' in xyx.lower()):
                        folder_name1 = "CAP_3P"
                    elif('cu_' in xyx.lower()):
                        folder_name1 = "DCU_"
                    elif('garud' in xyx.lower()):
                        folder_name1 = "Garud"
                    elif('better' in xyx.lower()):
                        folder_name1 = "Better_Meter"
                    elif('ltct' in xyx.lower()):
                        folder_name1 = "3PLTCT"
                    elif('wc' in xyx.lower()):
                        folder_name1 = "3PWC"
                    else:
                        print("improper file name given for Meter type")
                        continue
                    print ("folder_name1 = ",folder_name1)

                    uploaded = upload_to_aws(str(date_only), bucket_name, txt[j],sub_folder, time_only,folder_name1 )
            else:
                print("Skipping to Upload the log file to server")
        except Exception as e:
            print(f"Error writing DB log: {str(e)}")
            logging.error(f"Error writing DB log: {str(e)}")




    # -----------------------------
    # Final Result Display
    # -----------------------------
    endtimepct = datetime.datetime.now()
    diff = endtimepct - starttimepct

    results.append(["\n\nDiff Time is: {}".format(diff)])

    flat_results = []

    for sublist in results:

        for item in sublist:

            if isinstance(item, list):
                flat_results.append(" ".join(map(str, item)))
            else:
                flat_results.append(str(item))

    unique_results = []
    seen = list()

    for item in flat_results:

        if item not in seen:
            unique_results.append(item)
            seen.append(item)

    # msg_text = "\n".join(unique_results)
    print(unique_results)
    msg_text = make_pop_result(list_port, unique_results)
    print("\n========== FINAL RESULTS ==========\n")
    print(msg_text)
    # easygui.msgbox(msg_text, "PCT Test Results")
    easygui.textbox("PCT Test Results", "Result Summary", msg_text)
    # easygui.msgbox(msg_text, "PCT Failures Detected")

if __name__ == "__main__":
    freeze_support()
    setup_logger(enable_file_log=True)
    cfg = Config()
    port_json = {}
    port_status = False
    serial_config = {}
    serial_config_status = False
    print(Fore.GREEN + "Loading Configurations...")
    port_json, port_status = cfg.load_config_json('config.json')
    if not port_status:
        print(Fore.RED + "Com Port is not available in config...")
    else:
        print(Fore.GREEN + "Com port is loaded...")
        print(Fore.GREEN + "Used Com Port: " + Fore.YELLOW + f"{port_json}")
        serial_config, serial_config_status = cfg.check_encrypted_json('config_file.enc')
        print(serial_config)
        if serial_config_status:
            print(Fore.GREEN + "Configuration Parameters is Loaded...")
            print(Fore.GREEN + Style.RESET_ALL)
            while True:
                print ("<<<<<<<<<<<<<<<<<<<<<<<<<<<<...............1-Ph PCT(RF CH-9) Tool V 2.22.....................>>>>>>>>>>>>>>>>>>>")
                logging.info("\n<<<<<<<<<<<<<<<<<<<<<<<<<<<<...............1-Ph PCT(RF CH-9) Tool V 2.22.....................>>>>>>>>>>>>>>>>>>>")
                run(serial_config, port_json.get("com_port", []))
        else:
            print(Fore.RED + "Fixed Serial config is currepted")
            time.sleep(2)
    print("Closing PCT Tool..")
    time.sleep(3)