import os
import argparse
from gp_node.utils.address import Address
import serial
import logging
import datetime
import time
import threading
from threading import Thread
import time
import sys
from scripts.Test_cases_verificationClass import TestCase
import easygui
import openpyxl
from scripts.mct import db_connect
import pandas as pd
from colorama import Fore, Style, init
init(autoreset=True)
import boto3
from botocore.exceptions import NoCredentialsError
global abort_threads


BUCKET_NAME = "PUT_YOUR_BUCKET_NAME_HERE"
FOLDER_NAME = "PUT_YOUR_FOLDER_NAME_HERE"
ACCESS_KEY = "PUT_YOUR_ACCESS_KEY_HERE"
SECRET_KEY = "PUT_YOUR_SECRET_KEY_HERE"


# ============================================================================
# DICTIONARY-BASED RESULT STORAGE
# ----------------------------------------------------------------------------
# The original script tracked every test step positionally: MeterInfo /
# result_list were built with .append() in a fixed hand-maintained order,
# MCT_Fail_list had to line up with result_list by index to produce readable
# failure text, and the two-phase (main test + No-Load-Test) merge matched
# meters up using raw list indices (l1[1][0], l2[1][3], ...). Any of those
# lists gaining/losing an entry silently shifted every column/message after
# it.
# This version stores everything in named dictionaries instead:
#   meter_info : {'Live_Version': ..., 'Meter_PCB_Serial_No': ..., ...}
#   test_result: {'Meter_Serial_Num': 'pass', 'Factory_Reset': 'fail', ...}
#   result_log : {com_port: {'mac', 'meter_info', 'result', 'bookName',
#                             'fileName', 'com_port'}, ...}   <- keyed by COM
#                 port instead of being a plain list of entries.

# run_mct_test() now also returns a dict of {com_port: 'pass'/'fail'/
# 'unreachable'} summarizing every port that was tested.
# ============================================================================



# ----------------------------------------------------------------------------
# LOGS FOLDER
# ----------------------------------------------------------------------------
# All log workbooks (<Meter>_<Tool>_LOG.xlsx) are now written inside a
# dedicated "Logs" folder instead of directly in the script's working
# directory, so log files stay grouped in one place regardless of where the
# tool is launched from. get_log_book_path() is the single place that
# decides the on-disk location of a log workbook -- every worker function
# and run_mct_test() call it instead of hand-building the "<Meter>_<Tool>_LOG.xlsx"
# string themselves, so the folder can't drift out of sync between them.
# ----------------------------------------------------------------------------

if getattr(sys, "frozen", False):
    # Running inside a PyInstaller --onefile .exe. This module gets
    # bundled INTO the exe, but "the exe's own folder" - where Logs/
    # actually needs to live so it persists and is findable - is
    # sys.executable's folder, NOT whatever the OS happens to set as the
    # current working directory when the exe is launched (double-clicking
    # an exe can set cwd to almost anywhere, e.g. System32, the user's
    # Desktop, wherever). A bare relative "Logs" path resolves against
    # that unpredictable cwd, not against the exe - which is exactly what
    # caused "the system cannot find the path specified" during the S3
    # upload step: the folder either never got created where expected,
    # or got created somewhere the later upload step couldn't find it
    # again. Same fix as main.py's BASE_DIR.
    _BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    # Normal `python calibration_multiport.py` / imported-as-a-module
    # execution - unchanged, anchored to this file's own location.
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))


LOGS_FOLDER = os.path.join(_BASE_DIR, "Logs")
MCT_FOLDER = os.path.join(LOGS_FOLDER, "MCT")

# LOGS_FOLDER = "Logs"
# MCT_FOLDER = os.path.join(LOGS_FOLDER, "MCT")

def ensure_logs_folder():
    """Create the Logs folder if it doesn't exist yet. Safe to call every
    time a workbook path is needed -- os.makedirs(..., exist_ok=True) is a
    no-op if the folder is already there."""
    os.makedirs(LOGS_FOLDER, exist_ok=True)
    os.makedirs(MCT_FOLDER, exist_ok=True)

def get_log_book_path(meter_type, toolName):
    """Build the full path to this run's log workbook inside the Logs
    folder. This replaces the old
        bookName = meter_type.title() + "_" + toolName.upper() + "_LOG.xlsx"
    line that was previously repeated in worker_function_4g,
    worker_function1, worker_function2, and run_mct_test -- one helper
    means the folder can't be added to some call sites and forgotten in
    others."""
    ensure_logs_folder()
    return os.path.join(MCT_FOLDER, f"{meter_type.title()}_{toolName.upper()}_MCT_LOG.xlsx")

def get_mct_field_templates(meter_type, toolName):
    """
    Returns (meter_info_keys, result_keys, fail_messages) for the fields a
    *single* main-test worker (worker_function1 for rf/img, or
    worker_function_4g for 4g) populates for this meter_type/toolName.

    For rf/img, the No-Load-Test fields produced by worker_function2
    are a separate template (see get_no_load_field_templates) that gets
    merged in afterwards -- mirroring how the original script only combined
    the two phases' results after both had run.

    These key lists double as the Excel header order, so headers and data
    can't drift the way two independently hand-maintained lists could.
    """

    meter_type = meter_type.lower()
    toolName = toolName.lower()
    is_garud = 'garud' in meter_type
    is_rf_or_img = toolName in ('rf', 'img')

    meter_info_keys = [
        'Date_time', 'Duplicate_Serial_No', 'Live_Version', 'Meter_PCB_Serial_No',
        'Nic_PCB_No', 'Meter_IP_Address',
        'CalibSign', 'FrequencyCoeff', 'VCoeff', 'ICoeff[0]', 'ICoeff[1]',
        'ActPowerCoeff[0]', 'ActPowerCoeff[1]', 'PhAngle[0]', 'PhAngle[1]',
        'Internal_Version', 'Set_Meter_time', 'Payment_Mode_Value',
    ]
    result_keys = [
        'Meter_Serial_Num', 'live_version', 'Get_Meter_PCB_No', 'RTT_Check', 'Get_Nic_PCB_No',
        'Get_Meter_Address', 'Get_1p_calib_cofficient', 'Get_Internal_Version',
        'Set_Time', 'verify_time', 'Calibration_Unlock', 'Clear_Energy', 'Payment_Mode',
    ]
    fail_messages = {
        'Meter_Serial_Num': 'Fail in Meter Serial No',
        'live_version': 'Fail in Get Live Version',
        'Get_Meter_PCB_No': 'Fail in Get Meter PCB No',
        'RTT_Check': 'Fail in RTT Check - Meter is failed in RTT Test',
        'Get_Nic_PCB_No': 'Fail in NIC PCB No',
        'Get_Meter_Address': 'Fail in Get meter address',
        'Get_1p_calib_cofficient': 'Fail in get 1p calib cofficent',
        'Get_Internal_Version': 'Fail in Get Internal Version',
        'Set_Time': 'Fail in Set Time',
        'verify_time': 'Fail in Verify Time',
        'Calibration_Unlock': 'Fail in Calib Unlock',
        'Clear_Energy': 'Fail in Clear Energy',
        'Payment_Mode': 'Fail in Set Payment Mode',
    }

    if is_garud:
        meter_info_keys += ['Hardware_version']
        result_keys += ['Get_HW_Version']
        fail_messages['Get_HW_Version'] = 'Fail in Get HW Version'

    if '4g' in toolName.lower():
        meter_info_keys += ['Active_Sim', 'SIM_NUM', 'APN', 'IMEI', 'Signal_Strength']
        result_keys += ['check_GPRS_connection']
        fail_messages['check_GPRS_connection'] = 'Fail in GPRS Signal Strength'

    # if is_rf_or_img:
    #     meter_info_keys += [
    #         'Start_I_StartingEnergyIn10Min', 'Final_I_StartingEnergyIn10Min',
    #         'I_StartingEnergyIn10Min', 'Stand_I_StartingEnergyIn10Min',
    #     ]
    #     result_keys += ['Verify_DLMS_Activation', 'Verify_Starting_Current_Test']
    #     fail_messages['Verify_DLMS_Activation'] = 'Fail in DLMS Activation'
    #     fail_messages['Verify_Starting_Current_Test'] = 'Fail in starting current test'
    # else:  # img
    #     meter_info_keys += ['Active_Sim', 'SIM_NUM', 'APN', 'IMEI', 'Signal_Strength']
    #     result_keys += ['Verify_DLMS_Activation', 'check_GPRS_connection']
    #     fail_messages['Verify_DLMS_Activation'] = 'Fail in DLMS Activation'
    #     fail_messages['check_GPRS_connection'] = 'Fail in GPRS Signal Strength'
    meter_info_keys += [
        'Start_I_StartingEnergyIn10Min', 'Final_I_StartingEnergyIn10Min',
        'I_StartingEnergyIn10Min', 'Stand_I_StartingEnergyIn10Min',
    ]
    result_keys += ['Verify_DLMS_Activation', 'Verify_Starting_Current_Test', 'Factory_Reset', 'Check_Num_Events']
    fail_messages['Verify_DLMS_Activation'] = 'Fail in DLMS Activation'
    fail_messages['Verify_Starting_Current_Test'] = 'Fail in starting current test'
    fail_messages['Factory_Reset'] = 'Fail in Factory Reset'
    fail_messages['Check_Num_Events'] = 'Fail in Check Num Events'

    return meter_info_keys, result_keys, fail_messages

def get_no_load_field_templates():
    """Fields populated by worker_function2 (phase 2 / No-Load Test), merged
    into the phase-1 entry by merge_no_load_result() once both phases for a
    given meter (matched by PCB serial number) have completed."""
    meter_info_keys = [
        'Start_No_Load_EnergyIn10Min', 'Final_No_Load_EnergyIn10Min',
        'No_Load_EnergyIn10Min', 'Stand_No_Load_EnergyIn10Min',
    ]
    result_keys = ['Verify_No_Load_Test', 'Calib_Unlock_No_Load', 'Clear_Energy_No_Load']
    fail_messages = {
        'Verify_No_Load_Test': 'Fail in No Load Test',
        'Calib_Unlock_No_Load': 'Fail in Calib Unlcok in No Load Test',
        'Clear_Energy_No_Load': 'Fail in Clear Energy in No Load Test',
    }
    return meter_info_keys, result_keys, fail_messages

def build_log_entry(mac, meter_info, test_result, bookName, fileName, com_port=None):
    """Bundle one port's results into a single dictionary instead of the
    old positional 5-item list. Keys are self-describing, and com_port
    travels with the entry so run_mct_test() can key its return value by
    COM port without needing a second parallel structure."""
    return {
        'mac': mac,
        'meter_info': meter_info,
        'result': test_result,
        'bookName': bookName,
        'fileName': fileName,
        'com_port': com_port,
    }

def build_fail_messages(com_port, test_result, fail_message_lookup):
    """Named-key replacement for the old `MCT_Fail_list[idx] for idx in
    fail_indexes` pattern -- there is no positional index to keep in sync
    with result_list any more, so a step's failure text can never attach to
    the wrong step."""
    messages = []
    # Meter failed the prerequisite RTT check -> every other step was
    # skipped (and later back-filled as 'fail'); report only that failure.
    if test_result.get('RTT_Check') == 'fail':
        text = fail_message_lookup.get('RTT_Check', 'Fail in RTT Check')
        return ["COM Port: {}, {}".format(com_port, text)]
    for step_key, value in test_result.items():
        if value == 'fail':
            text = fail_message_lookup.get(step_key, f"Fail in {step_key}")
            messages.append("COM Port: {}, {}".format(com_port, text))
    return messages

def verify_log_xlsc(bookName, fileName):
    loc = bookName  # self.LOG_FILE_NAME

    try:
        wb = openpyxl.load_workbook(loc)
        sheet = wb.active
        cell_value = sheet.cell(row=1, column=1).value
    except Exception as e:
        logging.info("LOG XL file not found, creating one for you")
        wb = openpyxl.Workbook()
        wb.create_sheet(index=0, title=fileName)  # MRI_DATA_LOG
        sheet = wb.active
        logging.info(f"sheet name = {sheet.title}")
        del (wb['Sheet'])
        wb.save(loc)
        logging.info("New xlsc file created")
        return False
    else:
        return True

def get_header_column_map(sheet):
    """Read the header row (row 1) into {header_name: column_index}. Writing
    a row then becomes a name -> column lookup instead of relying on dict
    insertion order lining up with header order -- the last bit of implicit
    ordering coupling left over from the initial list->dict refactor."""
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
    branch's field order or count changes later (e.g. after a No-Load-Test
    merge). If a key isn't in the header yet, the sheet is extended with a
    new column instead of silently dropping the value."""
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


# def get_system_mac_address(toolName):
#     mac = "None"
#     try:
#         if sys.platform == 'win32':
#             for line in os.popen("ipconfig /all"):
#                 if line.lstrip().startswith('Physical Address'):
#                     mac = line.split(':')[1].strip().replace('-', ':')
#                     break
#         else:
#             for line in os.popen("/sbin/ifconfig"):
#                 if line.find('Ether') > -1:
#                     mac = line.split()[4]
#                     break
#     except Exception as e:
#         logging.error(f"Error in get mac address")
#         msg = "MAC ADDRESS NOT FOUND"
#         # easygui.msgbox(msg, title=(str(toolName) + str("|| GRAMPOWER")))
#         sys.exit("Restart Tool")
#     return mac

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
    logging.info(f"In MCT, MAC Address of system: {mac}")
    return mac


def addDefaultMctLog(bookName, fileName, meter_type="garud_1ph", tool_type="rf"):
    """Create the log workbook (if missing) and write its header row.
    Headers come from get_mct_field_templates() (+ get_no_load_field_templates()
    for img/img), so they always match the keys the workers /
    merge_no_load_result() will populate -- no separate hand-maintained
    header list to keep in sync."""
    if not verify_log_xlsc(bookName, fileName):
        logging.info("xlsx file for log not found. creating one to store test report")

        meter_info_keys, result_keys, _ = get_mct_field_templates(meter_type, tool_type)

        # if tool_type.lower() in ('rf', 'img'):
        #     no_load_meter_keys, no_load_result_keys, _ = get_no_load_field_templates()
        #     meter_info_keys = meter_info_keys + no_load_meter_keys
        #     result_keys = result_keys + no_load_result_keys

        no_load_meter_keys, no_load_result_keys, _ = get_no_load_field_templates()
        meter_info_keys = meter_info_keys + no_load_meter_keys
        result_keys = result_keys + no_load_result_keys

        meter_info_keys = meter_info_keys + ['Overall_Result']

        wb = openpyxl.load_workbook(bookName)
        sheet = wb[fileName]

        headers = ['MAC_ADDR', 'Index'] + meter_info_keys + result_keys
        for col_idx, header in enumerate(headers, start=1):
            sheet.cell(row=1, column=col_idx).value = header

        wb.save(bookName)
        logging.info("New xlsx file created with headers")


class StoppableThread(Thread):
    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


def worker_function_4g(data_dict, com_port, portID, result_queue, abort_flag, result_log):

    try:
        ser = serial.Serial(com_port, baudrate=9600, timeout=20)
        if not ser:
            msg = ["com port is unable to open:{}".format(com_port)]
            result_queue.append(msg)
            return 0

        cases = TestCase(ser, portID, data_dict.get("NIC_PCB_LENGTH", 27))
        toolName = data_dict.get("TOOL_TYPE", "RF").lower()
        mac = get_system_mac_address(toolName)

        meter_info = {}
        test_result = {}
        meter_type = data_dict.get("METER_TYPE", "Garud_1PH").lower()
        # bookName = meter_type.title() + "_" + toolName.upper() + "_LOG.xlsx"
        bookName = get_log_book_path(meter_type, toolName)
        fileName = toolName.upper() + "_DATA_LOG"
        starttime = datetime.datetime.now()
        Main_PCB_SFG_Prefix = data_dict.get("MAIN_PCB_SFG_PREFIX", "0000001")
        Nic_PCB_SFG_PREFIX = data_dict.get("NIC_PCB_SFG_PREFIX", "0000004")
        START_ADDRESS = 0x0100
        METER_ADDRESS = "255.255.255.255"

        Date_time = datetime.datetime.now()
        meter_info['Date_time'] = Date_time
        addDefaultMctLog(bookName, fileName, meter_type.lower(), toolName.lower())

        # Fail-message lookup for this branch -- replaces the old
        # hand-maintained MCT_Fail_list, which had to stay in perfect
        # positional sync with result_list.
        _, _, fail_message_lookup = get_mct_field_templates(meter_type, toolName)

        # Check com port status using check live version
        retryCnt = 3
        while retryCnt:
            logging.info(f"Checking COM port connectivity, attempt: {4 - retryCnt}, for com: {com_port}")
            try:
                check_port = cases.check_port(com_port)
                if 'Fail' == check_port:
                    msg = ["com port is unreachable: {}".format(com_port)]
                    result_queue.append(msg)
                    abort_flag.set()
                    logging.info(f"ser close for port : {com_port}")
                    ser.close()
                    return
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in worker4g func in check com port connectivity: {str(e)}, for com: {com_port}")
                retryCnt -= 1

        if abort_flag.is_set():
            return

        # Verify meter serial number
        retryCnt = 3
        while (retryCnt):
            logging.debug(f"Verifying Meter Serial Number, attempt: {4 - retryCnt}, for com: {com_port}")
            try:
                sr_num = cases.Verify_Serial_number(com_port)
                if sr_num.get("status") == 'fail':
                    meter_info['Duplicate_Serial_No'] = str(sr_num.get("sr_number", "None"))
                else:
                    meter_info['Duplicate_Serial_No'] = str(sr_num.get("sr_number", "None"))
                Sr_num2 = cases.Verify_Serial_number2(com_port)
                if Sr_num2.get('status') == 'pass':
                    test_result['Meter_Serial_Num'] = 'pass'
                else:
                    test_result['Meter_Serial_Num'] = 'fail'
                logging.debug(f"Meter Serial Number: {sr_num}, for com: {com_port}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in MCT in worker4g func in verify meter serial number: {str(e)}, for com: {com_port}")
                retryCnt = retryCnt - 1

        # Get live version
        retryCnt = 3
        while (retryCnt):
            logging.debug(f"Getting Live Version, attempt: {4 - retryCnt}, for com: {com_port}")
            try:
                version_live = cases.get_live_version_val(com_port)
                meter_info['Live_Version'] = str(version_live)
                if version_live == data_dict.get("LIVE_VERSION", 0000):
                    test_result['live_version'] = 'pass'
                else:
                    test_result['live_version'] = 'fail'
                logging.debug(f"Live Version: {version_live}, for com: {com_port}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in MCT in worker4g func in live version check: {str(e)}, for com: {com_port}")
                retryCnt = retryCnt - 1

        # Get pcb serial number
        retryCnt = 3
        while (retryCnt):
            logging.debug(f"Getting Meter PCB Serial Number, attempt: {4 - retryCnt}, for com: {com_port}")
            try:
                Pcb_serial_no = cases.Get_pcb_serial_num(com_port)
                meter_info['Meter_PCB_Serial_No'] = str(Pcb_serial_no)
                if (('R161' in Pcb_serial_no) or ('r161' in Pcb_serial_no) or (str(Pcb_serial_no[9:16]) == str(Main_PCB_SFG_Prefix))):
                    test_result['Get_Meter_PCB_No'] = 'pass'
                else:
                    test_result['Get_Meter_PCB_No'] = 'fail'
                logging.debug(f"Meter PCB Serial Number: {Pcb_serial_no}, for com: {com_port}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in worker4g func in get pcb serial number: {str(e)}, for com: {com_port}")
                retryCnt = retryCnt - 1

        rtt_result = db_connect.fetch_by_pcb_serial(Pcb_serial_no, toolName.lower())
        test_result['RTT_Check'] = 'pass' if rtt_result else 'fail'

        if not rtt_result:
            logging.info(
                f"RTT failed for com: {com_port}, PCB: {Pcb_serial_no}, "
                f"RTT overall_result: {rtt_result!r} -- skipping MCT test for this meter"
            )
        
        if rtt_result:
            # Get Nic PCB serial number
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Getting NIC PCB Serial Number, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    Nic_PCB_no = cases.Nic_PCB_No(com_port)
                    logging.debug(f"NIC PCB Serial Number: {Nic_PCB_no}, for com: {com_port}")
                    Nic_PCB_no = Nic_PCB_no.get("nic_pcb_number", None)
                    meter_info['Nic_PCB_No'] = str(Nic_PCB_no)
                    if ((('R154' in Nic_PCB_no) or ('r154' in Nic_PCB_no) or (Nic_PCB_no is not None) or (str(Nic_PCB_no[9:16]) == str(Nic_PCB_SFG_PREFIX))) and (not Nic_PCB_no.endswith('\x00'))):
                        test_result['Get_Nic_PCB_No'] = 'pass'
                    else:
                        test_result['Get_Nic_PCB_No'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker4g func in getting NIC PCB No: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

            # Get meter address
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Getting Meter Address, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    Meter_address = cases.get_Meter_address(str(METER_ADDRESS), com_port)
                    if Meter_address.get('status', 'fail') == 'fail':
                        meter_info['Meter_IP_Address'] = str(Meter_address.get('mtr_address', 'None'))
                    else:
                        meter_info['Meter_IP_Address'] = str(Meter_address.get('mtr_address', 'None'))
                    meter_addr2 = cases.get_Meter_address2(str(METER_ADDRESS), int(sr_num.get("sr_number", "None")), com_port)
                    if meter_addr2.get('status', 'fail') == 'pass':
                        test_result['Get_Meter_Address'] = 'pass'
                    else:
                        test_result['Get_Meter_Address'] = 'fail'
                    logging.debug(f"Meter Address: {Meter_address}, for com: {com_port}")
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker4g func in get meter address: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

            # Check 1P Calib cofficient
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Getting 1P Calibration Coefficients, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    calib_cofficient = cases.get_1p_calib_coffi(com_port)
                    if 'Fail' in calib_cofficient:
                        for key in ('CalibSign', 'FrequencyCoeff', 'VCoeff', 'ICoeff[0]', 'ICoeff[1]',
                                    'ActPowerCoeff[0]', 'ActPowerCoeff[1]', 'PhAngle[0]', 'PhAngle[1]'):
                            meter_info[key] = 'Fail'
                        test_result['Get_1p_calib_cofficient'] = 'fail'
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
                        if 'better' in meter_type.lower():
                            if (
                                ((float(calib_cofficient.get('FrequencyCoeff')) >= 0) and (float(calib_cofficient.get('FrequencyCoeff')) <= 2)) and
                                ((float(calib_cofficient.get('VCoeff')) >= 0) and (float(calib_cofficient.get('VCoeff')) <= 2)) and
                                ((float(calib_cofficient.get('ICoeff[0]')) >= 0) and (float(calib_cofficient.get('ICoeff[0]')) <= 2)) and
                                ((float(calib_cofficient.get('ICoeff[1]')) >= 0) and (float(calib_cofficient.get('ICoeff[1]')) <= 2)) and
                                ((float(calib_cofficient.get('ActPowerCoeff[0]')) >= 0) and (float(calib_cofficient.get('ActPowerCoeff[0]')) <= 2)) and
                                ((float(calib_cofficient.get('ActPowerCoeff[1]')) >= 0) and (float(calib_cofficient.get('ActPowerCoeff[1]')) <= 2)) and
                                ((float(calib_cofficient.get('PhAngle[0]')) >= 0) and (float(calib_cofficient.get('PhAngle[0]')) <= 1)) and
                                ((float(calib_cofficient.get('PhAngle[1]')) >= 0) and (float(calib_cofficient.get('PhAngle[1]')) <= 1))
                            ):
                                test_result['Get_1p_calib_cofficient'] = 'pass'
                                logging.debug(f"Pass in get 1p calib cofficient for com: {com_port}")
                            else:
                                test_result['Get_1p_calib_cofficient'] = 'fail'
                                logging.debug(f"Fail in get 1p calib cofficient for com: {com_port}")
                        else:
                            if ('wb' in data_dict.get('PROJECT', '').lower()) or ('tn' in data_dict.get('PROJECT', '').lower()):
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
                                    test_result['Get_1p_calib_cofficient'] = 'pass'
                                    logging.debug(f"Pass in get 1p calib cofficient for com: {com_port}")
                                else:
                                    test_result['Get_1p_calib_cofficient'] = 'fail'
                                    logging.debug(f"Fail in get 1p calib cofficient for com: {com_port}")
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
                                    test_result['Get_1p_calib_cofficient'] = 'pass'
                                    logging.debug(f"Pass in get 1p calib cofficient for com: {com_port}")
                                else:
                                    test_result['Get_1p_calib_cofficient'] = 'fail'
                                    logging.debug(f"Fail in get 1p calib cofficient for com: {com_port}")
                    logging.debug(f"1P Calibration Coefficients: {calib_cofficient}, for com: {com_port}")
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker4g func in check 1p calib cofficient: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

            # Get Internal Version
            if str(data_dict.get("INTERNAL_VERSION", 0)) == str(0):
                logging.info(f"Skipping Internal Version check as per configuration, for com: {com_port}")
                test_result['Get_Internal_Version'] = 'pass'
                meter_info['Internal_Version'] = '0'
            else:
                retryCnt = 3
                while (retryCnt):
                    logging.debug(f"Getting Internal Version, attempt: {4 - retryCnt}, for com: {com_port}")
                    try:
                        int_version = cases.get_internal_version_val(com_port)
                        if str(int_version.get("int_version", "0")) == str(data_dict.get("INTERNAL_VERSION", "0")):
                            test_result['Get_Internal_Version'] = 'pass'
                            meter_info['Internal_Version'] = str(int_version.get('int_version', 'None'))
                        else:
                            test_result['Get_Internal_Version'] = 'fail'
                            meter_info['Internal_Version'] = str(int_version.get('int_version', 'None'))
                        logging.debug(f"Internal Version: {int_version}, for com: {com_port}")
                        retryCnt = 0
                    except Exception as e:
                        logging.error(f"Error in MCT in worker4g func in get internal verison: {str(e)}, for com: {com_port}")
                        retryCnt = retryCnt - 1

            # Set time
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Setting Meter Time, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    Set_ip_time = cases.Set_time_val(com_port)
                    meter_info['Set_Meter_time'] = "now"
                    if Set_ip_time.get('status') == 'pass':
                        test_result['Set_Time'] = 'pass'
                    else:
                        test_result['Set_Time'] = 'fail'
                    logging.debug(f"Set Time Result: {Set_ip_time}, for com: {com_port}")
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker4g func in Setting meter time: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

            # Get meter time
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Verifying Meter Time, attempt: {4 - retryCnt} for com: {com_port}")
                try:
                    meter_time = cases.Verify_time_val(com_port)
                    logging.debug(f"Meter time: {meter_time}, for com: {com_port}")
                    if meter_time.get('status') == 'pass':
                        test_result['verify_time'] = 'pass'
                    else:
                        test_result['verify_time'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker4g func in get time: {str(e)} for com: {com_port}")
                    retryCnt = retryCnt - 1

            # Calib Unlock
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Performing Calibration Unlock, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    calib_unlock = cases.Calibration_unLock(com_port)
                    logging.debug(f"Calib unlock status: {calib_unlock}, for com: {com_port}")
                    if calib_unlock.get('status') == 'pass':
                        test_result['Calibration_Unlock'] = 'pass'
                    else:
                        test_result['Calibration_Unlock'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker4g func in calib unlock: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

            # Clear Energy
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Clearing Energy Values, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    Meter_energy = cases.Clear_Energy_Value(com_port)
                    logging.debug(f"Meter Energy: {Meter_energy} for com: {com_port}")
                    if Meter_energy.get('status') == 'pass':
                        test_result['Clear_Energy'] = 'pass'
                    else:
                        test_result['Clear_Energy'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker4g func in clear energy: {str(e)} for com: {com_port}")
                    retryCnt = retryCnt - 1

            # Set Payment mode
            retryCnt = 3
            while (retryCnt):
                logging.info(f"Setting Payment Mode, attempt: {4 - retryCnt}, for com: {com_port} ")
                try:
                    if str(data_dict.get("PAYMENT_MODE_SET", False)) == str(False):
                        logging.debug(f"Skipping Payment Mode setting as per configuration for com: {com_port}")
                        test_result['Payment_Mode'] = 'pass'
                        # Fixed vs. the original script: the skip branch used to
                        # never set a Payment_Mode_Value entry at all, which would
                        # have shifted every column after it out of line with the
                        # header row whenever payment mode was skipped. Always
                        # setting the key (even to 'None') keeps meter_info's key
                        # order identical to the header regardless of which
                        # branch runs.
                        meter_info['Payment_Mode_Value'] = 'None'
                    else:
                        Payment_mode = cases.Set_payment_mode(com_port, data_dict.get("PAYMENT_MODE", 1))
                        meter_info['Payment_Mode_Value'] = data_dict.get("PAYMENT_MODE", 1)
                        logging.debug(f"Set Payment Mode result: {Payment_mode} for com: {com_port}")
                        if Payment_mode.get('status') == 'pass':
                            test_result['Payment_Mode'] = 'pass'
                        else:
                            test_result['Payment_Mode'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in setting payment mode: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1
                    if retryCnt == 0:
                        meter_info.setdefault('Payment_Mode_Value', None)
                        test_result['Payment_Mode'] = 'fail'

            # Check Hardware version if meter type is not better meter
            if 'better' not in meter_type.lower():
                retryCnt = 3
                while (retryCnt):
                    logging.debug(f"Getting Hardware Version, attempt: {4 - retryCnt}, for com: {com_port}")
                    try:
                        check_hardware_version = cases.get_hardware_version(com_port)
                        logging.debug(f"Hardware version: {check_hardware_version}, for com: {com_port}")

                        if check_hardware_version.get('status') == 'pass':
                            meter_info['Hardware_version'] = int(check_hardware_version.get('hw_version', 0))
                            test_result['Get_HW_Version'] = 'pass'
                        else:
                            meter_info['Hardware_version'] = int(check_hardware_version.get('hw_version', 0))
                            test_result['Get_HW_Version'] = 'fail'
                        retryCnt = 0
                    except Exception as e:
                        logging.error(f"Error in MCT in worker4g func in getting hardware version: {str(e)}, for com: {com_port}")
                        if retryCnt == 0:
                            meter_info['Hardware_version'] = None
                            test_result['Get_HW_Version'] = 'fail'
                        retryCnt = retryCnt - 1

            # Check DLMS activation
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Checking DLMS Activation, attempt: {4 - retryCnt} for com: {com_port}, DLMS Type: {data_dict.get('DLMS_TYPE', 'old_dlms').lower()}")
                try:
                    CHECK_DLMS_ACTIVATION = cases.dlms_Activation_check_value(com_port, data_dict.get('DLMS_TYPE', 'old_dlms').lower())
                    logging.debug(f"DLMS Activation status: {CHECK_DLMS_ACTIVATION}, for com: {com_port}")
                    if CHECK_DLMS_ACTIVATION.get('status') == 'pass':
                        test_result['Verify_DLMS_Activation'] = 'pass'
                    else:
                        test_result['Verify_DLMS_Activation'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker4g func in checking DLMS activation: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

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
                        test_result['check_GPRS_connection'] = 'fail'
                    else:
                        test_result['check_GPRS_connection'] = 'pass'
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
                        test_result['check_GPRS_connection'] = 'fail'

            # Factory reset
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Performing Factory Reset, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    FactoryReset = cases.Factory_reset_val(com_port)
                    logging.debug(f"Factory reset result: {FactoryReset}, for com: {com_port}")
                    if FactoryReset.get('status') == 'pass':
                        test_result['Factory_Reset'] = 'pass'
                    else:
                        test_result['Factory_Reset'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker4g func in factory reset: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

            logging.info(f"Wait for meter start after factory reset: {data_dict.get("Fact_Reset_sleepTime", 10)}, for com: {com_port}")
            time.sleep(data_dict.get("Fact_Reset_sleepTime", 10))

            # Check num events
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Checking Number of Events after Factory Reset, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    check_num_event = cases.check_num_events(com_port)
                    logging.debug(f"Check num events result: {check_num_event}, for com: {com_port}")
                    if check_num_event.get('status') == 'pass':
                        test_result['Check_Num_Events'] = 'pass'
                    else:
                        test_result['Check_Num_Events'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker4g func in checking number of events: {str(e)}")
                    retryCnt = retryCnt - 1

        ser.close()

        # Overall_Result is computed once by run_mct_test() after any
        # No-Load-Test merge (there is none for img, but this keeps the
        # code path identical to worker_function1/merge_no_load_result).
        result_log[com_port] = build_log_entry(mac, meter_info, test_result, bookName, fileName, com_port)

        time.sleep(0.1)

        EndTime = datetime.datetime.now()
        logging.info(f"Test time for 4G MCT StartTime: {starttime}, for com: {com_port}")
        logging.info(f"Test time for 4G MCT EndTime: {EndTime}, for com: {com_port}")
        logging.info(f"Test time for 4G MCT Diff : {EndTime - starttime}, for com: {com_port}")

        fail_messages = build_fail_messages(com_port, test_result, fail_message_lookup)
        if fail_messages:
            result_queue.append(fail_messages)

    except Exception as e:
        msg = ["com port is unreachable:{}".format(com_port)]
        logging.error(f"Exception in worker_function_4g: {str(e)}")
        result_queue.append(msg)
        return


def worker_function1(data_dict, com_port, portID, result_queue, abort_flag, result_log):
    try:
        ser = serial.Serial(com_port, baudrate=9600, timeout=20)
        if not ser:
            msg = ["com port is unable to open: {}".format(com_port)]
            result_queue.append(msg)
            return 0

        cases = TestCase(ser, portID, data_dict.get("NIC_PCB_LENGTH", 27))
        toolName = data_dict.get("TOOL_TYPE", "RF").lower()
        mac = get_system_mac_address(toolName)

        meter_info = {}
        test_result = {}
        meter_type = data_dict.get("METER_TYPE", "Garud_1PH").lower()
        # bookName = meter_type.title() + "_" + toolName.upper() + "_LOG.xlsx"
        bookName = get_log_book_path(meter_type, toolName)
        fileName = toolName.upper() + "_DATA_LOG"
        starttime = datetime.datetime.now()
        Main_PCB_SFG_Prefix = data_dict.get("MAIN_PCB_SFG_PREFIX", "0000001")
        Nic_PCB_SFG_PREFIX = data_dict.get("NIC_PCB_SFG_PREFIX", "0000004")

        START_ADDRESS = 0x0100
        METER_ADDRESS = "255.255.255.255"

        Date_time = datetime.datetime.now()
        meter_info['Date_time'] = Date_time
        addDefaultMctLog(bookName, fileName, meter_type.lower(), toolName.lower())

        _, _, fail_message_lookup = get_mct_field_templates(meter_type, toolName)

        # Check com port status using check live version
        retryCnt = 3
        while retryCnt:
            logging.info(f"Checking COM port connectivity, attempt: {4 - retryCnt}, for com: {com_port}")
            try:
                check_port = cases.check_port(com_port)
                if 'Fail' == check_port:
                    msg = ["com port is unreachable: {}".format(com_port)]
                    result_queue.append(msg)
                    abort_flag.set()
                    logging.info(f"ser close for port : {com_port}")
                    ser.close()
                    return
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in MCT worker1 func in check com port connectivity: {str(e)}, for com: {com_port}")
                retryCnt -= 1

        # Verify meter serial number
        retryCnt = 3
        while (retryCnt):
            logging.debug(f"Verifying Meter Serial Number in MCT, attempt: {4 - retryCnt}, for com: {com_port}")
            try:
                sr_num = cases.Verify_Serial_number(com_port)
                if sr_num.get('status').lower() == 'fail':
                    meter_info['Duplicate_Serial_No'] = str(sr_num.get('sr_number', "None"))
                else:
                    meter_info['Duplicate_Serial_No'] = str(sr_num.get('sr_number', "None"))
                Sr_num2 = cases.Verify_Serial_number2(com_port)
                if Sr_num2.get('status') == 'pass':
                    test_result['Meter_Serial_Num'] = 'pass'
                else:
                    test_result['Meter_Serial_Num'] = 'fail'
                logging.debug(f"Meter Serial Number: {sr_num}, for com: {com_port}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in MCT in worker1 func in verify meter serial number: {str(e)}, for com: {com_port}")
                retryCnt = retryCnt - 1

        # Get live version
        retryCnt = 3
        while (retryCnt):
            logging.debug(f"Getting Live Version, attempt: {4 - retryCnt}, for com: {com_port}")
            try:
                version_live = cases.get_live_version_val(com_port)
                meter_info['Live_Version'] = str(version_live)
                if version_live == data_dict.get("LIVE_VERSION", 0000):
                    test_result['live_version'] = 'pass'
                else:
                    test_result['live_version'] = 'fail'
                logging.debug(f"Live Version: {version_live}, for com: {com_port}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in MCT in worker1 func in live version check: {str(e)}, for com: {com_port}")
                retryCnt = retryCnt - 1

        # Get pcb serial number
        retryCnt = 3
        while (retryCnt):
            logging.debug(f"Getting Meter PCB Serial Number, attempt: {4 - retryCnt}, for com: {com_port}")
            try:
                Pcb_serial_no = cases.Get_pcb_serial_num(com_port)
                meter_info['Meter_PCB_Serial_No'] = str(Pcb_serial_no)
                if (('R161' in Pcb_serial_no) or ('r161' in Pcb_serial_no) or (str(Pcb_serial_no[9:16]) == str(Main_PCB_SFG_Prefix))):
                    test_result['Get_Meter_PCB_No'] = 'pass'
                else:
                    test_result['Get_Meter_PCB_No'] = 'fail'
                logging.debug(f"Meter PCB Serial Number: {Pcb_serial_no}, for com: {com_port}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in MCT in worker1 func in get pcb serial number: {str(e)}, for com: {com_port}")
                retryCnt = retryCnt - 1

        rtt_result = db_connect.fetch_by_pcb_serial(Pcb_serial_no, toolName.lower())
        db_connect.close_connection()
        test_result['RTT_Check'] = 'pass' if rtt_result else 'fail'

        if not rtt_result:
            logging.info(
                f"Calibration failed for com: {com_port}, PCB: {Pcb_serial_no}, "
                f"Calibration overall_result: {rtt_result!r} -- skipping RTT test for this meter"
            )

        if rtt_result:
            # Get Nic PCB serial number
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Getting NIC PCB Serial Number, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    Nic_PCB_no = cases.Nic_PCB_No(com_port)
                    logging.debug(f"NIC PCB Serial Number: {Nic_PCB_no}, for com: {com_port}")
                    Nic_PCB_no = Nic_PCB_no.get("nic_pcb_number", None)
                    meter_info['Nic_PCB_No'] = str(Nic_PCB_no)
                    if ((Nic_PCB_no is not None) or ('R154' in Nic_PCB_no) or ('r154' in Nic_PCB_no) or (str(Nic_PCB_no[9:16] == str(Nic_PCB_SFG_PREFIX))) and (not Nic_PCB_no.endswith('\x00'))):
                        test_result['Get_Nic_PCB_No'] = 'pass'
                    else:
                        test_result['Get_Nic_PCB_No'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker1 func in getting NIC PCB No: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

            # Get meter address
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Getting Meter Address, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    Meter_address = cases.get_Meter_address(str(METER_ADDRESS), com_port)
                    if Meter_address.get('status', 'fail').lower() == 'fail':
                        meter_info['Meter_IP_Address'] = str(Meter_address.get('mtr_address', 'None'))
                    else:
                        meter_info['Meter_IP_Address'] = str(Meter_address.get('mtr_address', 'None'))
                    meter_addr2 = cases.get_Meter_address2(str(METER_ADDRESS), int(sr_num.get('sr_number', "None")), com_port)
                    if meter_addr2.get('status') == 'pass':
                        test_result['Get_Meter_Address'] = 'pass'
                    else:
                        test_result['Get_Meter_Address'] = 'fail'
                    logging.debug(f"Meter Address: {Meter_address}, for com: {com_port}")
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker1 func in get meter address: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

            # Check 1P Calib cofficient
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Getting 1P Calibration Coefficients, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    calib_cofficient = cases.get_1p_calib_coffi(com_port)
                    if 'Fail' in calib_cofficient:
                        for key in ('CalibSign', 'FrequencyCoeff', 'VCoeff', 'ICoeff[0]', 'ICoeff[1]',
                                    'ActPowerCoeff[0]', 'ActPowerCoeff[1]', 'PhAngle[0]', 'PhAngle[1]'):
                            meter_info[key] = 'Fail'
                        test_result['Get_1p_calib_cofficient'] = 'fail'
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
                                test_result['Get_1p_calib_cofficient'] = 'pass'
                                logging.debug(f"Pass in get 1p calib cofficient for com: {com_port}")
                            else:
                                test_result['Get_1p_calib_cofficient'] = 'fail'
                                logging.debug(f"Fail in get 1p calib cofficient for com: {com_port}")
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
                                    test_result['Get_1p_calib_cofficient'] = 'pass'
                                    logging.debug(f"Pass in get 1p calib cofficient for com: {com_port}")
                                else:
                                    test_result['Get_1p_calib_cofficient'] = 'fail'
                                    logging.debug(f"Fail in get 1p calib cofficient for com: {com_port}")
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
                                    test_result['Get_1p_calib_cofficient'] = 'pass'
                                    logging.debug(f"Pass in get 1p calib cofficient for com: {com_port}")
                                else:
                                    test_result['Get_1p_calib_cofficient'] = 'fail'
                                    logging.debug(f"Fail in get 1p calib cofficient for com: {com_port}")
                    logging.debug(f"1P Calibration Coefficients: {calib_cofficient}, for com: {com_port}")
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in worker1 func in check 1p calib cofficient: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

            # Get Internal Version
            if str(data_dict.get("INTERNAL_VERSION", 0)) == str(0):
                logging.info(f"Skipping Internal Version check as per configuration for com: {com_port}")
                test_result['Get_Internal_Version'] = 'pass'
                meter_info['Internal_Version'] = '0'
            else:
                retryCnt = 3
                while (retryCnt):
                    logging.debug(f"Getting Internal Version, attempt: {4 - retryCnt}, for com: {com_port}")
                    try:
                        int_version = cases.get_internal_version_val(com_port)
                        if str(int_version.get('int_version', '0')) == str(data_dict.get("INTERNAL_VERSION", 0)):
                            test_result['Get_Internal_Version'] = 'pass'
                            meter_info['Internal_Version'] = str(int_version.get('int_version', '0'))
                        else:
                            test_result['Get_Internal_Version'] = 'fail'
                            meter_info['Internal_Version'] = str(int_version.get('int_version', '0'))
                        logging.debug(f"Internal Version: {int_version}, for com: {com_port}")
                        retryCnt = 0
                    except Exception as e:
                        logging.error(f"Error in MCT in worker1 func in get internal verison: {str(e)}, for com: {com_port}")
                        retryCnt = retryCnt - 1

            # Set time
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Setting Meter Time, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    Set_ip_time = cases.Set_time_val(com_port)
                    meter_info['Set_Meter_time'] = "now"
                    if Set_ip_time.get('status') == 'pass':
                        test_result['Set_Time'] = 'pass'
                    else:
                        test_result['Set_Time'] = 'fail'
                    logging.debug(f"Set Time Result: {test_result['Set_Time']}")
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker1 func in Setting meter time: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

            # Get meter time
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Verifying Meter Time, attempt: {4 - retryCnt} for com: {com_port}")
                try:
                    meter_time = cases.Verify_time_val(com_port)
                    logging.debug(f"Meter time: {meter_time}, for com: {com_port}")
                    if meter_time.get('status') == 'pass':
                        test_result['verify_time'] = 'pass'
                    else:
                        test_result['verify_time'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker1 func in get time: {str(e)} for com: {com_port}")
                    retryCnt = retryCnt - 1

            # Calib Unlock
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Performing Calibration Unlock, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    calib_unlock = cases.Calibration_unLock(com_port)
                    logging.debug(f"Calib unlock status: {calib_unlock}, for com: {com_port}")
                    if calib_unlock.get('status') == 'pass':
                        test_result['Calibration_Unlock'] = 'pass'
                    else:
                        test_result['Calibration_Unlock'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker1 func in calib unlock: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

            # Clear Energy
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Clearing Energy Values, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    Meter_energy = cases.Clear_Energy_Value(com_port)
                    logging.debug(f"Meter Energy: {Meter_energy} for com: {com_port}")
                    if Meter_energy.get('status') == 'pass':
                        test_result['Clear_Energy'] = 'pass'
                    else:
                        test_result['Clear_Energy'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker1 func in clear energy: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

            # Set Payment mode
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Setting Payment Mode, attempt: {4 - retryCnt}, for com: {com_port} ")
                try:
                    if data_dict.get("PAYMENT_MODE_SET", False) == False:
                        logging.debug(f"Skipping Payment Mode set in MCT as per configuration for com: {com_port}")
                        test_result['Payment_Mode'] = 'pass'
                        meter_info['Payment_Mode_Value'] = 'None'
                    else:
                        Payment_mode = cases.Set_payment_mode(com_port, data_dict.get("PAYMENT_MODE", 1))
                        meter_info['Payment_Mode_Value'] = data_dict.get("PAYMENT_MODE", 1)
                        logging.debug(f"Set Payment Mode result: {Payment_mode} for com: {com_port}")
                        if Payment_mode.get('status') == 'pass':
                            test_result['Payment_Mode'] = 'pass'
                        else:
                            test_result['Payment_Mode'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in set payment mode: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1
                    if retryCnt == 0:
                        meter_info.setdefault('Payment_Mode_Value', None)
                        test_result['Payment_Mode'] = 'fail'

            # Get Hardware version if meter type is Garud
            if 'better' not in meter_type.lower():
                retryCnt = 3
                while (retryCnt):
                    logging.debug(f"Getting Hardware Version, attempt: {4 - retryCnt}")
                    try:
                        check_hardware_version = cases.get_hardware_version(com_port)
                        logging.debug(f"Hardware version: {check_hardware_version}, for com: {com_port}")
                        if check_hardware_version.get('status') == 'pass':
                            meter_info['Hardware_version'] = int(check_hardware_version.get('hw_version', None))
                            test_result['Get_HW_Version'] = 'pass'
                        else:
                            meter_info['Hardware_version'] = int(check_hardware_version.get('hw_version', None))
                            test_result['Get_HW_Version'] = 'fail'
                        retryCnt = 0
                    except Exception as e:
                        logging.error(f"Error in MCT in worker1 func in getting hardware version: {str(e)}, for com: {com_port}")
                        if retryCnt == 0:
                            meter_info['Hardware_version'] = None
                            test_result['Get_HW_Version'] = 'fail'
                        retryCnt = retryCnt - 1

            # Check DLMS activation
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Checking DLMS Activation, attempt: {4 - retryCnt} for com: {com_port}, DLMS Type: {data_dict.get('DLMS_TYPE', 'old_dlms').lower()}")
                try:
                    CHECK_DLMS_ACTIVATION = cases.dlms_Activation_check_value(com_port, data_dict.get('DLMS_TYPE', 'old_dlms').lower())
                    logging.debug(f"DLMS Activation status: {CHECK_DLMS_ACTIVATION}, for com: {com_port}")
                    if CHECK_DLMS_ACTIVATION.get('status') == 'pass':
                        test_result['Verify_DLMS_Activation'] = 'pass'
                    else:
                        test_result['Verify_DLMS_Activation'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker1 func in checking DLMS activation: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

            # Check GPRS connection
            if '4g' in toolName.lower():
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
                            test_result['check_GPRS_connection'] = 'fail'
                        else:
                            test_result['check_GPRS_connection'] = 'pass'
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
                            test_result['check_GPRS_connection'] = 'fail'


            # for starting current test by Energy
            starting_current_Energy = 0.0
            Energy_one_pulse = 0.0003125  # energy one pulse = (1/3200)
            time.sleep(data_dict.get("Bench_stabT_StartingC", 0))
            logging.info(f"Waiting For Bench Stablization before starting current Test, for com: {com_port}")

            # Get starting current value
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Measuring initial energy for starting current test, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    starting_current_initial_value = cases.hr_energy_register(com_port)
                    meter_info['Start_I_StartingEnergyIn10Min'] = str(starting_current_initial_value.get("energy", "None"))
                    logging.debug(f"Starting Current Test - Initial Energy: {starting_current_initial_value}, for com: {com_port}")
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in measuring initial energy for starting current test: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1
                    if retryCnt == 0:
                        meter_info['Start_I_StartingEnergyIn10Min'] = None

            logging.info("<<<<<<<<<<<............Waiting for 60s for starting current Test............>>>>>>>>>>>>>>")
            time.sleep(60)

            # Get starting current final value
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Measuring energy for starting current test, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    starting_current_final_value = cases.hr_energy_register(com_port)
                    meter_info['Final_I_StartingEnergyIn10Min'] = str(starting_current_final_value.get("energy", "None"))
                    logging.debug(f"Starting Current Test - Initial Energy: {starting_current_initial_value}, Final Energy: {starting_current_final_value}, for com: {com_port}")
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker1 func in measuring energy for starting current test: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1
                    if retryCnt == 0:
                        meter_info['Final_I_StartingEnergyIn10Min'] = None

            starting_current_Energy = float((starting_current_final_value.get("energy", "None") - starting_current_initial_value.get("energy", "None")) * 10.0)
            if (starting_current_Energy >= Energy_one_pulse):
                test_result['Verify_Starting_Current_Test'] = 'pass'
            else:
                test_result['Verify_Starting_Current_Test'] = 'fail'
            meter_info['I_StartingEnergyIn10Min'] = str(starting_current_Energy)
            meter_info['Stand_I_StartingEnergyIn10Min'] = str(Energy_one_pulse)

            # Factory reset
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Performing Factory Reset, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    FactoryReset = cases.Factory_reset_val(com_port)
                    logging.debug(f"Factory reset result: {FactoryReset}, for com: {com_port}")
                    if FactoryReset.get('status') == 'pass':
                        test_result['Factory_Reset'] = 'pass'
                    else:
                        test_result['Factory_Reset'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker1 func in factory reset: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

            time.sleep(data_dict.get("Fact_Reset_sleepTime", 10))

            # Check num events
            retryCnt = 3
            while (retryCnt):
                logging.debug(f"Checking Number of Events after Factory Reset, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    check_num_event = cases.check_num_events(com_port)
                    logging.debug(f"Check num events result: {check_num_event}, for com: {com_port}")
                    if check_num_event.get('status') == 'pass':
                        test_result['Check_Num_Events'] = 'pass'
                    else:
                        test_result['Check_Num_Events'] = 'fail'
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in MCT in worker1 func in checking number of events: {str(e)}, for com: {com_port}")
                    retryCnt = retryCnt - 1

        ser.close()

        # Overall_Result is intentionally NOT set here -- run_mct_test()
        # merges in the No-Load-Test (worker_function2) result for this
        # meter first (matched by PCB serial number, since the meter may be
        # moved to a different COM port on the second bench) and computes
        # Overall_Result once, from the combined result dict, so it always
        # ends up as the last column no matter which fields got merged in
        # after this phase finished.
        result_log[com_port] = build_log_entry(mac, meter_info, test_result, bookName, fileName, com_port)
        time.sleep(0.1)

        EndTime = datetime.datetime.now()
        logging.info(f"Before no load StartTime: {starttime}, for com: {com_port}")
        logging.info(f"Before no load EndTime: {EndTime}, for com: {com_port}")
        logging.info(f"Before no load time difference between start and end Diff : {EndTime - starttime}, for com: {com_port}")

        fail_messages = build_fail_messages(com_port, test_result, fail_message_lookup)
        if fail_messages:
            result_queue.append(fail_messages)

    except Exception as e:
        logging.error(f"Error in worker1 func: {str(e)}")
        msg = ["com port is unreachable:{}".format(com_port)]
        result_queue.append(msg)
        return


def worker_function2(data_dict, com_port, portID, result_queue, abort_flag, result_log):

    try:
        ser = serial.Serial(com_port, baudrate=9600, timeout=20)
        if not ser:
            msg = ["com port is unable to open: {}".format(com_port)]
            result_queue.append(msg)
            return 0

        cases = TestCase(ser, portID, data_dict.get("NIC_PCB_LENGTH", 27))
        toolName = data_dict.get("TOOL_TYPE", "RF").lower()
        mac = get_system_mac_address(toolName)

        meter_info = {}
        test_result = {}
        meter_type = data_dict.get("METER_TYPE", "Garud_1PH").lower()
        # bookName = meter_type.title() + "_" + toolName.upper() + "_LOG.xlsx"
        bookName = get_log_book_path(meter_type, toolName)
        fileName = toolName.upper() + "_DATA_LOG"
        starttime = datetime.datetime.now()
        Main_PCB_SFG_Prefix = data_dict.get("MAIN_PCB_SFG_PREFIX", "0000001")
        Nic_PCB_SFG_PREFIX = data_dict.get("NIC_PCB_SFG_PREFIX", "0000004")

        START_ADDRESS = 0x0100
        METER_ADDRESS = "255.255.255.255"

        addDefaultMctLog(bookName, fileName, meter_type.lower(), toolName.lower())
        _, _, fail_message_lookup = get_no_load_field_templates()

        logging.debug(f"Starting No Load Test for COM Port: {com_port}")
        retryCnt = 3
        while retryCnt:
            logging.debug(f"Checking COM Port connectivity for COM Port: {com_port}, Attempts: {4-retryCnt}")
            try:
                check_port = cases.check_port(com_port)
                if 'Fail' == check_port:
                    msg = ["com port is unreachable: {}".format(com_port)]
                    result_queue.append(msg)
                    abort_flag.set()
                    return
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in MCT in worker2 func in check com port: {str(e)}, for com: {com_port}")
                retryCnt -= 1

        # Get PCB Serial number -- this is the key used to match this
        # No-Load-Test entry back to the correct phase-1 entry, since the
        # meter may have been moved to a different COM port on this bench.
        retryCnt = 3
        while (retryCnt):
            logging.debug(f"Getting PCB Serial Number for COM Port: {com_port}, Attempts: {4-retryCnt}")
            try:
                Pcb_serial_no = cases.Get_pcb_serial_num(com_port)
                meter_info['Meter_PCB_Serial_No'] = str(Pcb_serial_no)
                retryCnt = 0
                logging.debug(f"Successfully got PCB Serial Number for COM Port: {com_port}, PCB Serial Number: {Pcb_serial_no}")
            except Exception as e:
                logging.error(f"Error in MCT in worker2 func in get pcb serrial number: {str(e)}, for com: {com_port}")
                retryCnt = retryCnt - 1

        # for No Load test by Energy
        No_load_Energy = 0.0
        Energy_one_pulse = 0.0003125  # energy one pulse = (1/3200)
        logging.info(f"Waiting For Bench Stablization before No Load Test and waiting time: {data_dict.get("Bench_stabT_StartingC", 10)}")
        time.sleep(data_dict.get("Bench_stabT_StartingC", 10))

        # Get Initial energy
        retryCnt = 3
        while (retryCnt):
            logging.debug(f"Getting initial energy register value for No Load Test for COM Port: {com_port}, Attempts left: {4-retryCnt}")
            try:
                starting_No_Load_initial_value = cases.hr_energy_register(com_port)
                meter_info['Start_No_Load_EnergyIn10Min'] = str(starting_No_Load_initial_value.get("energy", "None"))
                logging.debug(f"Successfully got initial energy register value for No Load Test for COM Port: {com_port}, Initial Energy Value: {starting_No_Load_initial_value}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in MCT in worker2 func in get Initial energy: {str(e)}, for com: {com_port}")
                retryCnt = retryCnt - 1
                if retryCnt == 0:
                    meter_info['Start_No_Load_EnergyIn10Min'] = None

        logging.info("<<<<<<<<<<<............Waiting for 60s for No Load Test............>>>>>>>>>>>>>>")
        time.sleep(60)

        # Get final energy after 60 seconds
        retryCnt = 3
        while (retryCnt):
            logging.debug(f"Getting final energy register value for No Load Test for COM Port: {com_port}, Attempts left: {4-retryCnt}")
            try:
                starting_No_Load_final_value = cases.hr_energy_register(com_port)
                meter_info['Final_No_Load_EnergyIn10Min'] = str(starting_No_Load_final_value.get("energy", "None"))
                logging.debug(f"Successfully got final energy register value for No Load Test for COM Port: {com_port}, Final Energy Value: {starting_No_Load_final_value}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in MCT in worker2 func in get energy after 60 sec: {str(e)}, for com: {com_port}")
                retryCnt = retryCnt - 1
                if retryCnt == 0:
                    meter_info['Final_No_Load_EnergyIn10Min'] = None

        No_load_Energy = float((starting_No_Load_final_value.get("energy", "None") - starting_No_Load_initial_value.get("energy", "None")) * 10.0)
        if (No_load_Energy < Energy_one_pulse):
            test_result['Verify_No_Load_Test'] = 'pass'
        else:
            test_result['Verify_No_Load_Test'] = 'fail'
        meter_info['No_Load_EnergyIn10Min'] = str(No_load_Energy)
        meter_info['Stand_No_Load_EnergyIn10Min'] = str(Energy_one_pulse)

        # Calib Unlock
        retryCnt = 3
        while (retryCnt):
            logging.debug("Performing Calibration Unlock for COM Port: {}, Attempts left: {}".format(com_port, retryCnt))
            try:
                calib_unlock = cases.Calibration_unLock(com_port)
                logging.debug(f"Successfully performed Calibration Unlock in No Load Test result: {calib_unlock}, for COM Port: {com_port}")
                if calib_unlock.get('status') == 'pass':
                    test_result['Calib_Unlock_No_Load'] = 'pass'
                else:
                    test_result['Calib_Unlock_No_Load'] = 'fail'
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in MCT in worker2 func in calibration unlock: {str(e)}, for com: {com_port}")
                retryCnt = retryCnt - 1

        # Clear Energy
        retryCnt = 3
        while (retryCnt):
            logging.debug(f"Clearing Energy Value for COM Port: {com_port}, Attempts: {4-retryCnt}")
            try:
                Meter_energy = cases.Clear_Energy_Value(com_port)
                logging.debug(f"Successfully cleared energy value in No Load Test: {Meter_energy}, for COM Port: {com_port}")
                if Meter_energy.get('status') == 'pass':
                    test_result['Clear_Energy_No_Load'] = 'pass'
                else:
                    test_result['Clear_Energy_No_Load'] = 'fail'
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in MCT in worker2 func in clear energy: {str(e)}, for com: {com_port}")
                retryCnt = retryCnt - 1

        ser.close()

        # Overall_Result is computed later by run_mct_test() after merging
        # into the matching phase-1 entry (see worker_function1's note).
        result_log[com_port] = build_log_entry(mac, meter_info, test_result, bookName, fileName, com_port)
        time.sleep(0.1)

        EndTime = datetime.datetime.now()
        logging.info(f"After no load test StartTime: {starttime}, for com: {com_port}")
        logging.info(f"After no load test EndTime: {EndTime}, for com: {com_port}")
        logging.info(f"After no load test Diff : {EndTime - starttime}, for com: {com_port}")

        fail_messages = build_fail_messages(com_port, test_result, fail_message_lookup)
        if fail_messages:
            result_queue.append(fail_messages)

    except Exception as e:
        msg = [f"com port is unreachable:{com_port}"]
        logging.error(f"Error in worker2 func for COM Port {com_port}: {str(e)}")
        result_queue.append(msg)
        return


# def merge_no_load_result(phase1_results, phase2_results):
#     """Combine each No-Load-Test (phase 2) entry into its matching phase-1
#     entry, matched by Meter_PCB_Serial_No (not COM port -- the meter can be
#     moved to a different COM port on the second bench, exactly like the
#     original list-based version's `l1[1][0]` / `l2[1][3]` index lookup, but
#     now by name instead of position so it can't silently match the wrong
#     field if either worker's field order ever changes)."""
#     unmatched = []
#     for com_port2, entry2 in phase2_results.items():
#         target_pcb = entry2['meter_info'].get('Meter_PCB_Serial_No')
#         matched_com = None
#         for com_port1, entry1 in phase1_results.items():
#             if str(entry1['meter_info'].get('Meter_PCB_Serial_No')) == str(target_pcb):
#                 matched_com = com_port1
#                 break

#         if matched_com is None:
#             logging.warning(f"No matching phase-1 result found for No-Load-Test PCB {target_pcb} (COM {com_port2})")
#             unmatched.append(com_port2)
#             continue

#         entry1 = phase1_results[matched_com]
#         for key in ('Start_No_Load_EnergyIn10Min', 'Final_No_Load_EnergyIn10Min',
#                     'No_Load_EnergyIn10Min', 'Stand_No_Load_EnergyIn10Min'):
#             entry1['meter_info'][key] = entry2['meter_info'].get(key)
#         entry1['result'].update(entry2['result'])

#     return unmatched


def merge_no_load_result(phase1_results, phase2_results):
    """Combine each No-Load-Test (phase 2) entry into its matching phase-1
    entry, matched by Meter_PCB_Serial_No (not COM port -- the meter can be
    moved to a different COM port on the second bench, exactly like the
    original list-based version's `l1[1][0]` / `l2[1][3]` index lookup, but
    now by name instead of position so it can't silently match the wrong
    field if either worker's field order ever changes).

    This does NOT use a blind `entry1['result'].update(entry2['result'])`.
    Three failure modes are guarded against explicitly instead of being
    silently absorbed by dict semantics:

    1. Ambiguous PCB match -- two phase-1 entries share the same PCB serial
       number (e.g. a duplicate/misread serial). The original `break` on
       first match silently picked one; this still merges into the first
       match for compatibility, but logs a warning so the collision isn't
       invisible.
    2. Double merge -- two different phase-2 entries both match the same
       phase-1 entry (the same "meter" tested twice on bench 2). The second
       merge would silently clobber the first's No-Load-Test data; this
       logs a warning when it happens.
    3. Pass/fail *value* mismatch on a shared key -- if a phase-2 result key
       ever collides with an existing phase-1 key (today the two step-name
       sets are disjoint, but nothing enforces that staying true), a plain
       `.update()` lets whichever value came later silently win, which could
       flip a real failure into a 'pass'. Here, a colliding key with
       different values is resolved by keeping 'fail' -- the safe answer --
       and logging the disagreement instead of guessing silently.
    """
    unmatched = []
    merged_into = {}  # matched_com -> list of com_port2 already merged into it

    for com_port2, entry2 in phase2_results.items():
        target_pcb = entry2['meter_info'].get('Meter_PCB_Serial_No')
        candidates = [
            com_port1 for com_port1, entry1 in phase1_results.items()
            if str(entry1['meter_info'].get('Meter_PCB_Serial_No')) == str(target_pcb)
        ]

        if not candidates:
            logging.warning(f"No matching phase-1 result found for No-Load-Test PCB {target_pcb} (COM {com_port2})")
            unmatched.append(com_port2)
            continue

        if len(candidates) > 1:
            logging.warning(
                f"PCB {target_pcb} (No-Load-Test COM {com_port2}) matches multiple phase-1 "
                f"entries {candidates} -- two meters appear to share a PCB serial number. "
                f"Merging into {candidates[0]}; verify this PCB manually."
            )
        matched_com = candidates[0]

        if matched_com in merged_into:
            logging.warning(
                f"Phase-1 entry {matched_com} already received a No-Load-Test merge from "
                f"COM {merged_into[matched_com]}; COM {com_port2} is merging into it again and "
                f"will overwrite that earlier merge's data."
            )
        merged_into.setdefault(matched_com, []).append(com_port2)

        entry1 = phase1_results[matched_com]

        for key in ('Start_No_Load_EnergyIn10Min', 'Final_No_Load_EnergyIn10Min',
                    'No_Load_EnergyIn10Min', 'Stand_No_Load_EnergyIn10Min'):
            entry1['meter_info'][key] = entry2['meter_info'].get(key)

        for key, value in entry2['result'].items():
            existing = entry1['result'].get(key)
            if existing is not None and existing != value:
                resolved = 'fail' if 'fail' in (existing, value) else value
                logging.warning(
                    f"Result step '{key}' for {matched_com} disagrees between phase-1 "
                    f"('{existing}') and phase-2 ('{value}') data; keeping '{resolved}' "
                    f"instead of silently letting one value overwrite the other."
                )
                entry1['result'][key] = resolved
            else:
                entry1['result'][key] = value

    return unmatched

def finalize_overall_results(results):
    """Compute Overall_Result for every entry from its (possibly merged)
    result dict, and set it last so it always lands as the final Excel
    column regardless of what got merged in beforehand."""
    for entry in results.values():
        entry['meter_info']['Overall_Result'] = 'fail' if 'fail' in entry['result'].values() else 'pass'


# Sentinel values written into the log when a step's real data was never
# recorded (worker crashed/aborted before reaching that step). A missing
# result step reads as 'fail', never a silent 'pass' -- untested must never
# look identical to tested-and-passed.
NOT_TESTED_METER_VALUE = None
NOT_TESTED_RESULT_VALUE = 'fail'


def fill_missing_fields(entry, meter_info_keys, result_keys):
    """Ensure every field in meter_info_keys/result_keys exists on `entry`,
    filling in NOT_TESTED_* defaults for anything a worker never got to
    write.

    This is what actually prevents the Excel "column mismatch" the old
    list-based script suffered from: if worker_function2 aborted (e.g.
    failed its own COM-port check) before ever writing a phase-2 entry,
    merge_no_load_result() has nothing to merge into the matching phase-1
    row, so that row would otherwise be missing the No-Load-Test fields
    entirely. add_log_xlsc() already writes by header *name* rather than
    position (see get_header_column_map), so a short entry no longer shifts
    later columns out of alignment the way the original positional writer
    did -- but a field that's simply absent from the dict still left a
    blank, unexplained cell. Calling this right before finalize_overall_results()
    guarantees every row has a value under every header, so a genuinely
    untested step shows up as an explicit 'fail' in the log instead of an
    empty cell someone has to notice and investigate."""
    for key in meter_info_keys:
        entry['meter_info'].setdefault(key, NOT_TESTED_METER_VALUE)
    for key in result_keys:
        entry['result'].setdefault(key, NOT_TESTED_RESULT_VALUE)


def run_mct_test(data_dict, active_port_list, upload_bench):
    parser = argparse.ArgumentParser()
    logging.info("Starting MCT Testing Script")

    parser.add_argument('-p', action="store", dest="hex_file",
                        help="programs new hex file")
    parser.add_argument("--id", action="store", dest="portID",
                      help="device id")

    args = parser.parse_args()
    if args.portID is None:
        args.portID = 4

    list_port = active_port_list

    results = []
    results1 = []
    phase1_results = {}   # worker_function1 / worker_function_4g, keyed by COM port
    phase2_results = {}   # worker_function2 (No Load Test), keyed by COM port
    abort_flag = threading.Event()

    toolName = data_dict.get("TOOL_TYPE", "RF").lower()
    meter_type = data_dict.get("METER_TYPE", "Garud_1PH").lower()
    # bookName = meter_type.title() + "_" + toolName.upper() + "_LOG.xlsx"
    bookName = get_log_book_path(meter_type, toolName)
    fileName = toolName.upper() + "_DATA_LOG"
    addDefaultMctLog(bookName, fileName, meter_type.lower(), toolName.lower())

    logging.info("Starting {} MCT Testing on ports: {}".format(toolName, list_port))
    threads = [StoppableThread(target=worker_function1, args=(data_dict, port_name, args.portID, results, abort_flag, phase1_results)) for port_name in list_port]

    for thread in threads:
        thread.start()
        time.sleep(1)  # Stagger thread starts slightly to avoid serial port contention
        

    for thread in threads:
        thread.join()
        time.sleep(1)  # Stagger thread starts slightly to avoid serial port contention

    easygui.msgbox("Swich the Bench for No Load Test", "Action Required for MCT")
    logging.info("Swich the Bench for No Load Test, Action Required for MCT")

    rtt_failed_ports = [
        port_name for port_name in list_port
        if phase1_results.get(port_name, {}).get('result', {}).get('RTT_Check') != 'pass'
    ]
    if rtt_failed_ports:
        logging.info(f"Skipping Neutral Calibration for PCT-failed ports: {rtt_failed_ports}")
    no_load_test_port_list = [port_name for port_name in list_port if port_name not in rtt_failed_ports]


    threads = [StoppableThread(target=worker_function2, args=(data_dict, port_name, args.portID, results1, abort_flag, phase2_results)) for port_name in no_load_test_port_list]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    unmatched_no_load = merge_no_load_result(phase1_results, phase2_results)
    if unmatched_no_load:
        logging.warning(f"No-Load-Test entries with no matching phase-1 meter: {unmatched_no_load}")
    results.extend(results1)

    # if ('rf' in toolName.lower()) or ('img' in toolName.lower()):
    #     logging.info("Starting RF/IMG MCT Testing on ports: {}".format(list_port))
    #     threads = [StoppableThread(target=worker_function1, args=(data_dict, port_name, args.portID, results, abort_flag, phase1_results)) for port_name in list_port]

    #     for thread in threads:
    #         thread.start()
    #         time.sleep(1)  # Stagger thread starts slightly to avoid serial port contention
            

    #     for thread in threads:
    #         thread.join()
    #         time.sleep(1)  # Stagger thread starts slightly to avoid serial port contention

    #     easygui.msgbox("Swich the Bench for No Load Test", "Action Required for MCT")
    #     logging.info("Swich the Bench for No Load Test, Action Required for MCT")

    #     rtt_failed_ports = [
    #         port_name for port_name in list_port
    #         if phase1_results.get(port_name, {}).get('result', {}).get('RTT_Check') != 'pass'
    #     ]
    #     if rtt_failed_ports:
    #         logging.info(f"Skipping Neutral Calibration for PCT-failed ports: {rtt_failed_ports}")
    #     no_load_test_port_list = [port_name for port_name in list_port if port_name not in rtt_failed_ports]
    

    #     threads = [StoppableThread(target=worker_function2, args=(data_dict, port_name, args.portID, results1, abort_flag, phase2_results)) for port_name in no_load_test_port_list]

    #     for thread in threads:
    #         thread.start()

    #     for thread in threads:
    #         thread.join()

    #     unmatched_no_load = merge_no_load_result(phase1_results, phase2_results)
    #     if unmatched_no_load:
    #         logging.warning(f"No-Load-Test entries with no matching phase-1 meter: {unmatched_no_load}")
    #     results.extend(results1)

    # elif toolName.lower() == "4g":
    #     logging.info("Starting 4G MCT Testing on ports: {}".format(list_port))
    #     threads = [StoppableThread(target=worker_function_4g, args=(data_dict, port_name, args.portID, results, abort_flag, phase1_results)) for port_name in list_port]
    #     for thread in threads:
    #         thread.start()

    #     for thread in threads:
    #         thread.join()

    # -----------------------------------------------------------------
    # Guarantee every requested port has a COMPLETE row before writing to
    # Excel -- this is the fix for the "column mismatch" problem: if
    # worker_function2 aborts early (e.g. fails its own COM-port check) it
    # never writes a phase-2 entry at all, so merge_no_load_result() has
    # nothing to merge into that meter's phase-1 row and the No-Load-Test
    # columns are simply missing for it. The same thing happens if a
    # worker crashes before ever calling result_log[com_port] = ... --
    # that port never gets an entry in phase1_results in the first place.
    #
    # get_mct_field_templates()/get_no_load_field_templates() are the same
    # template used to build the header row, so "every field the header
    # expects" and "every field we fill a default for" can never drift
    # apart. Any port missing entirely gets a placeholder entry (marked
    # fully_untested so the returned pass/fail summary can still say
    # 'unreachable' instead of 'fail'); any port with a partial entry gets
    # its missing fields defaulted in place.
    # -----------------------------------------------------------------
    meter_keys, result_keys, fail_message_lookup = get_mct_field_templates(meter_type, toolName)
    # is_rf_or_img = ('rf' in toolName.lower()) or ('img' in toolName.lower())
    nl_meter_keys, nl_result_keys, _ = get_no_load_field_templates()
    # if is_rf_or_img:
    #     nl_meter_keys, nl_result_keys, _ = get_no_load_field_templates()
    # else:
    #     nl_meter_keys, nl_result_keys = [], []

    for port_name in list_port:
        if port_name not in phase1_results:
            placeholder = build_log_entry(
                mac='NOT_TESTED', meter_info={}, test_result={},
                bookName=bookName, fileName=fileName, com_port=port_name,
            )
            placeholder['fully_untested'] = True
            phase1_results[port_name] = placeholder

        entry = phase1_results[port_name]
        fill_missing_fields(entry, meter_keys, result_keys)
        fill_missing_fields(entry, nl_meter_keys, nl_result_keys)
        # if is_rf_or_img:
        #     fill_missing_fields(entry, nl_meter_keys, nl_result_keys)

    # Overall_Result is computed once here, from each entry's (possibly
    # merged, now fully-populated) result dict, so it's always the last
    # column regardless of whether a No-Load-Test merge happened.
    finalize_overall_results(phase1_results)

    # Rebuild fail messages from the FINAL (merged + defaulted) result dict.
    #
    # build_fail_messages() inside worker_function1/worker_function2 only
    # sees each worker's own partial test_result at the moment *that
    # worker* finishes. A failure injected afterward -- e.g.
    # Verify_No_Load_Test defaulted to 'fail' by fill_missing_fields()
    # because this meter's PCB serial was never matched to a phase-2
    # (No-Load-Test) entry -- never got reported into `results`, so the
    # popup silently omitted a meter that the Excel log correctly marked
    # as failed. Rebuilding messages here from each entry's final result
    # dict closes that gap. Duplicate strings from the workers' own
    # earlier messages are harmless -- they get deduped by the
    # set(flat_results) call below.
    combined_fail_lookup = dict(fail_message_lookup)
    # if is_rf_or_img:
    _, _, nl_fail_lookup = get_no_load_field_templates()
    combined_fail_lookup.update(nl_fail_lookup)

    final_fail_messages = []
    for port_name, entry in phase1_results.items():
        if entry.get('fully_untested'):
            continue
        final_fail_messages.extend(
            build_fail_messages(port_name, entry['result'], combined_fail_lookup)
        )

    if final_fail_messages:
        results.append(final_fail_messages)

    for com_port_key, entry in phase1_results.items():
        try:
            add_log_xlsc(entry)
        except Exception:
            logging.info("unknown error in add logs in Excel")
            continue

    # Dictionary-based pass/fail summary keyed by COM port -- every port
    # that was asked for gets an entry (thanks to the placeholder fill-in
    # above), including ones that never produced any real result, which are
    # reported as 'unreachable' rather than a possibly-misleading 'fail'.
    mct_pass_fail_by_com = {}
    for port_name in list_port:
        entry = phase1_results[port_name]
        if entry.get('fully_untested'):
            mct_pass_fail_by_com[port_name] = 'unreachable'
        else:
            mct_pass_fail_by_com[port_name] = entry['meter_info'].get('Overall_Result', 'fail')

    if data_dict.get("IS_DATA_CONN", 1) == 1:
        df_frame = pd.read_excel(bookName)
        try:
            status = False
            error = ""
            if 'better' in meter_type.lower():
                if '4g' in toolName:
                    status, error = db_connect.upload_dataframe(df_frame, 'better', '4g')
                else:
                    status, error = db_connect.upload_dataframe(df_frame, 'better', 'rf')
            else:
                if '4g' in toolName:
                    status, error = db_connect.upload_dataframe(df_frame, 'garud', '4g')
                else:
                    status, error = db_connect.upload_dataframe(df_frame, 'garud', 'rf')
            if not status:
                logging.info(f"DB upload failed . Saved locally for retry. Error: {error}")
            else:
                if (len(phase1_results) != 0):  # if the result file is empty then don't upload to server
                    logging.info("Uploading MCT Test Results to Cloud Storage")


                    def upload_to_aws(local_folder, bucket, s3_file, sub_folder, file_time, folder_name1, local_file_path = None):
                        s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                                        aws_secret_access_key=SECRET_KEY)
                        local_path = os.path.join(MCT_FOLDER, s3_file)
                        logging.info(f"Uploaded file: {str(upload_bench + "_" + file_time + "_" + s3_file)}")
                        try:
                            if local_file_path is None:
                                local_file_path = s3_file
                            s3.upload_file(local_file_path, bucket, FOLDER_NAME + "/{0}/{1}/{2}/{3}".format(folder_name1, sub_folder, local_folder, str(upload_bench + "_" + file_time + "_" + s3_file)))
                            logging.info("Upload Successful")
                            os.remove(local_file_path)
                            return True
                        except NoCredentialsError:
                            logging.info("Credentials not available")
                            return False
                        except Exception as e:
                            logging.info(e)
                            logging.info("The file was not found")
                            return False

                    al = os.listdir(MCT_FOLDER)
                    txt = list(filter(lambda x: x[-5:] == '.xlsx', al))
                    if len(txt) == 0:
                        return mct_pass_fail_by_com

                    for j in range(len(txt)):
                        temp_time = datetime.datetime.now()
                        date_only = datetime.datetime.strftime(temp_time, '%Y-%m-%d')
                        time_only = datetime.datetime.strftime(temp_time, '%H_%M_%S')

                        sub_folder = "UNKNOWN"
                        xyx = str(txt[j])
                        if ("PCT" in xyx):
                            sub_folder = "PCT"
                        elif ("4g" in xyx.lower()):
                            sub_folder = "4G_MCT"
                        elif ("rf" in xyx.lower()):
                            sub_folder = "MCT"
                        elif ("img" in xyx.lower()):
                            sub_folder = "MCT"
                        elif ("rtt" in xyx.lower()):
                            sub_folder = "RTT"
                        else:
                            logging.info("improper file name given for tool type")
                            continue
                        logging.info(f"sub_folder = {sub_folder}")

                        folder_name1 = "UNKNOWN"
                        if "SM_1P" in xyx:
                            folder_name1 = "ISM_1P"
                        elif "SM_3P" in xyx:
                            folder_name1 = "ISM_3P"
                        elif "AP_3P" in xyx:
                            folder_name1 = "CAP_3P"
                        elif "CU_" in xyx:
                            folder_name1 = "DCU_"
                        elif ("garud" in xyx.lower()):
                            folder_name1 = "Garud"
                        elif ("better" in xyx.lower()):
                            folder_name1 = "Better_Meter"
                        else:
                            logging.info("improper file name given for Meter type")
                            continue
                        logging.info(f"Uploading file: {str(txt[j])} to bucket: {BUCKET_NAME} in folder: {FOLDER_NAME}/{folder_name1}/{date_only}")
                        local_path = os.path.join(MCT_FOLDER, txt[j])
                        uploaded = upload_to_aws(str(date_only), BUCKET_NAME, txt[j], sub_folder, time_only, folder_name1, local_file_path=local_path)
                        logging.info("MCT DATA SUCCESSFULLY UPLOADED TO CLOUD")
                else:
                    logging.info("Skipping to Upload the log file to server")
        except Exception as e:
            logging.error(f"Error writing DB log: {str(e)}")
    else:
        logging.info("Upload data to EMS db flag is disable")
        try:
            if (len(phase1_results) != 0):  # if the result file is empty then don't upload to server
                logging.info("Uploading MCT Test Results to Cloud Storage")

                

                def upload_to_aws(local_folder, bucket, s3_file, sub_folder, file_time, folder_name1, local_file_path = None):
                    s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                                    aws_secret_access_key=SECRET_KEY)
                    local_path = os.path.join(MCT_FOLDER, s3_file)
                    logging.info(f"Uploaded file: {str(upload_bench + "_" + file_time + "_" + s3_file)}")
                    try:
                        if local_file_path is None:
                            local_file_path = s3_file
                        s3.upload_file(local_file_path, bucket, FOLDER_NAME + "/{0}/{1}/{2}/{3}".format(folder_name1, sub_folder, local_folder, str(upload_bench + "_" + file_time + "_" + s3_file)))
                        logging.info("Upload Successful")
                        os.remove(local_file_path)
                        return True
                    except NoCredentialsError:
                        logging.info("Credentials not available")
                        return False
                    except Exception as e:
                        logging.info(e)
                        logging.info("The file was not found")
                        return False

                al = os.listdir(MCT_FOLDER)
                txt = list(filter(lambda x: x[-5:] == '.xlsx', al))
                logging.info(txt)
                if len(txt) == 0:
                    logging.info("file doesn't exist")
                    return mct_pass_fail_by_com

                for j in range(len(txt)):
                    temp_time = datetime.datetime.now()
                    date_only = datetime.datetime.strftime(temp_time, '%Y-%m-%d')
                    time_only = datetime.datetime.strftime(temp_time, '%H_%M_%S')

                    sub_folder = "UNKNOWN"
                    xyx = str(txt[j])
                    if ("PCT" in xyx):
                        sub_folder = "PCT"
                    elif ("4g" in xyx.lower()):
                        sub_folder = "4G_MCT"
                    elif ("rf" in xyx.lower()):
                        sub_folder = "MCT"
                    elif ("img" in xyx.lower()):
                        sub_folder = "MCT"
                    elif ("rtt" in xyx.lower()):
                        sub_folder = "RTT"
                    else:
                        logging.info("improper file name given for tool type")
                        continue
                    logging.info(f"sub_folder = {sub_folder}")

                    folder_name1 = "UNKNOWN"
                    if ("garud" in xyx.lower()):
                        folder_name1 = "Garud"
                    elif ("better" in xyx.lower()):
                        folder_name1 = "Better_Meter"
                    else:
                        logging.info("improper file name given for Meter type")
                        continue

                    logging.info(f"Uploading file: {str(txt[j])} to bucket: {BUCKET_NAME} in folder: {FOLDER_NAME}/{folder_name1}/{date_only}")
                    local_path = os.path.join(MCT_FOLDER, txt[j])
                    uploaded = upload_to_aws(str(date_only), BUCKET_NAME, txt[j], sub_folder, time_only, folder_name1, local_file_path=local_path)
            else:
                logging.info("Skipping to Upload the log file to server")
        except Exception as e:
            logging.error(f"Error Uploading log: {str(e)}")

    logging.info("MCT Testing Completed with results: {}".format(phase1_results))
    if results:
        # Flatten and remove duplicates
        flat_results = [item for sublist in results for item in sublist]
        unique_results = sorted(list(set(flat_results)))
        msg_text = "\n".join(unique_results)
        easygui.msgbox(msg_text, title="MCT Test Failures")   # <-- popup added
        
    # return {'COM157': 'pass'}
    return mct_pass_fail_by_com