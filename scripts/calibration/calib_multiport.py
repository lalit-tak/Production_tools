import os
import logging
import datetime
import time
import threading

import queue
from threading import Thread
import sys
import serial
import openpyxl
import pandas as pd
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtWidgets import QInputDialog, QMessageBox, QApplication
from scripts.calibration import db_connect

from scripts.Test_cases_verificationClass import TestCase
from colorama import Fore, Style, init
import boto3
from botocore.exceptions import NoCredentialsError

init(autoreset=True)

BUCKET_NAME = "PUT_YOUR_BUCKET_NAME_HERE"
FOLDER_NAME = "PUT_YOUR_FOLDER_NAME_HERE"
ACCESS_KEY = "PUT_YOUR_ACCESS_KEY_HERE"
SECRET_KEY = "PUT_YOUR_SECRET_KEY_HERE"

# ============================================================================
# DICTIONARY-BASED RESULT STORAGE
# ----------------------------------------------------------------------------
# The original script tracked every test step positionally: MeterInfo /
# result_list were built with .append() in a fixed hand-maintained order,
# CALIB_Fail_list / CALIB_Fail_list_list had to line up with result_list by
# index to produce readable failure text, and the two-phase (Phase
# Calibration + Neutral Calibration) merge matched meters up using raw list
# indices (l1[1][0], l2[1][2], l2[1][-1]). Any of those lists gaining/losing
# an entry silently shifted every column/message after it - exactly the bug
# class mct_multiport.py's own docstring calls out and fixes the same way.
#
# This version mirrors mct_multiport.py's approach directly:
#   meter_info : {'Meter_PCB_Serial_No': ..., 'CalibSign': ..., ...}
#   test_result: {'Phase_calibration': 'pass', 'Neutral_calibration': 'fail', ...}
#   phase_results / neutral_results : {com_port: {'mac', 'meter_info',
#                                                  'result', 'bookName',
#                                                  'fileName', 'com_port'}}
#                 <- keyed by COM port instead of being a plain list of
#                    entries, matching mct_multiport.py's phase1_results /
#                    phase2_results.
#
# run_calibration_test() returns a dict of {com_port: {'phase': 'pass'/
# 'fail', 'neutral': 'pass'/'fail'}} - the exact shape MainWindow's
# _on_test_finished already expects for "calibration_test" (one script
# run reporting into both the Phase and Neutral table columns).
# ============================================================================

# ============================================================================
# MAIN-THREAD DIALOG BRIDGE (replaces easygui/Tkinter)
# ----------------------------------------------------------------------------
# run_calibration_test() executes on a background QThread (FunctionThreadRunner
# in main.py) so the Qt event loop / elapsed timer keeps running during the
# test. It used to pop bench-power prompts and "Switch the Bench" messages
# via easygui, which wraps Tkinter. Tkinter is only safe on a process's main
# thread; showing it from a worker thread happened to survive the FIRST time
# (the first Tcl interpreter ever created in the process), but running
# calibration a second time in the same session spins up a NEW worker thread
# that touches Tcl again - Tcl's C-level thread affinity does not tolerate
# that, and it can hard-crash the whole process (Tcl_Panic / access
# violation) below the level Python's own try/except can catch. That is why
# the entire tool - not just the calibration test - closed on the second run.
#
# Fix: never touch Tkinter from a worker thread. Instead, the worker thread
# emits a Qt signal to this QObject, which was constructed on the main
# thread (at module import time, before any worker thread exists) and so
# always executes its slots there. PyQt's own dialogs (QInputDialog,
# QMessageBox) share the single Qt event loop and are safe to open any
# number of times, from any thread, for the life of the process. The
# emitting thread blocks on a Queue until the main thread's dialog returns.
# ============================================================================

class _MainThreadDialogBridge(QObject):
    _request_enterbox = pyqtSignal(str, str, object)  # msg, title, response_queue
    _request_msgbox = pyqtSignal(str, str, object)     # msg, title, response_queue

    def __init__(self):
        super().__init__()
        self._request_enterbox.connect(self._show_enterbox, Qt.QueuedConnection)
        self._request_msgbox.connect(self._show_msgbox, Qt.QueuedConnection)

    def enterbox(self, msg, title):
        """Blocks the CALLING (worker) thread until the user answers a
        text-entry dialog shown on the main thread. Returns the entered
        text, or None if the dialog was cancelled."""
        response_queue = queue.Queue(maxsize=1)
        self._request_enterbox.emit(msg, title, response_queue)
        return response_queue.get()

    def msgbox(self, msg, title):
        """Blocks the calling thread until an info dialog shown on the main
        thread is dismissed."""
        response_queue = queue.Queue(maxsize=1)
        self._request_msgbox.emit(msg, title, response_queue)
        response_queue.get()

    def _show_enterbox(self, msg, title, response_queue):
        parent = QApplication.activeWindow()
        text, ok = QInputDialog.getText(parent, title, msg)
        response_queue.put(text if ok else None)

    def _show_msgbox(self, msg, title, response_queue):
        parent = QApplication.activeWindow()
        QMessageBox.information(parent, title, msg)
        response_queue.put(None)


# Constructed here, at module import time - this module is imported from
# main.py's top-level imports, which always run on the main thread, well
# before any FunctionThreadRunner worker thread is spawned. That guarantees
# this QObject's thread affinity is the main thread for the life of the
# process, so every emit() below - no matter which worker thread calls it -
# delivers its dialog on the main thread.
_dialog_bridge = _MainThreadDialogBridge()


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
CALIB_FOLDER = os.path.join(LOGS_FOLDER, "CALIB")

# LOGS_FOLDER = "Logs"
# CALIB_FOLDER = os.path.join(LOGS_FOLDER, "CALIB")


def ensure_logs_folder():
    """Create the Logs folder if it doesn't exist yet. Safe to call every
    time a workbook path is needed - os.makedirs(..., exist_ok=True) is a
    no-op if the folder is already there. Mirrors mct_multiport.py's
    ensure_logs_folder()."""
    os.makedirs(LOGS_FOLDER, exist_ok=True)
    os.makedirs(CALIB_FOLDER, exist_ok=True)


def get_log_book_path(meter_type, project_name, tool_name):
    """Build the full path to this run's log workbook inside the Logs
    folder, the same way mct_multiport.py's get_log_book_path() does -
    one helper means the folder/name convention can't drift between the
    phase worker, the neutral worker, and run_calibration_test()."""
    ensure_logs_folder()
    return os.path.join(
        CALIB_FOLDER,
        f"{meter_type.title()}_{project_name.upper()}_{tool_name.upper()}_CALIB_LOG.xlsx",
    )


def get_calib_phase_field_templates():
    """Named fields the PHASE CALIBRATION worker (worker_function_phase)
    populates. These key lists double as the Excel header order for this
    phase, so headers and data can't drift the way two independently
    hand-maintained lists (MeterInfo / CALIB_Fail_list) could in the
    original script."""
    # meter_info_keys = ['Date_time', 'Meter_IP_Address', 'Meter_PCB_Serial_No', 'Relay_Mode']
    meter_info_keys = ['Date_time', 'Meter_IP_Address', 'Meter_PCB_Serial_No']
    # result_keys = ['Get_Meter_Address', 'Set_Relay_Mode', 'Get_Meter_PCB_No', 'PCT_Check','Calibration_Unlock', 'Phase_calibration']
    result_keys = ['Get_Meter_Address', 'Get_Meter_PCB_No', 'PCT_Check','Calibration_Unlock', 'Phase_calibration']
    fail_messages = {
        'Get_Meter_Address': 'Fail in Get meter address',
        'Set_Relay_Mode': 'Fail in Set Relay Mode',
        'Get_Meter_PCB_No': 'Fail in Get Meter PCB No',
        'PCT_Check': 'Fail in PCT Check - meter has not passed PCT',
        'Calibration_Unlock': 'Fail in Calib Unlock',
        'Phase_calibration': 'Fail in Phase Calibration',
    }
    return meter_info_keys, result_keys, fail_messages


def get_calib_neutral_field_templates():
    """Named fields the NEUTRAL CALIBRATION worker
    (worker_function_neutral_calib_coff) populates.

    NOTE: the original script appended these values in an order that
    didn't actually match its own declared header row (CalibSign then
    immediately '0','1' meant for FrequencyCoeff's min/max, before
    FrequencyCoeff's own value even appeared) - a real instance of
    exactly the column-misalignment bug this whole refactor eliminates.
    Here every value is assigned to its own explicitly named dict key
    instead, so it lands under the correct Excel header regardless of
    what order the code happens to compute it in."""
    meter_info_keys = [
        'Meter_PCB_Serial_No',
        'CalibSign',
        'FrequencyCoeff_min', 'FrequencyCoeff_max', 'FrequencyCoeff',
        'VCoeff_min', 'VCoeff_max', 'VCoeff',
        'ICoeff[0]_min', 'ICoeff[0]_max', 'ICoeff[0]',
        'ICoeff[1]_min', 'ICoeff[1]_max', 'ICoeff[1]',
        'ActPowerCoeff[0]_min', 'ActPowerCoeff[0]_max', 'ActPowerCoeff[0]',
        'ActPowerCoeff[1]_min', 'ActPowerCoeff[1]_max', 'ActPowerCoeff[1]',
        'PhAngle[0]_min', 'PhAngle[0]_max', 'PhAngle[0]',
        'PhAngle[1]_min', 'PhAngle[1]_max', 'PhAngle[1]',
    ]
    result_keys = ['Neutral_calibration', 'Get_1p_calib_cofficient', 'CalibSign_Status']
    fail_messages = {
        'Neutral_calibration': 'Fail in Neutral Calibration',
        'Get_1p_calib_cofficient': 'Fail in get 1p calib cofficent',
        'CalibSign_Status': 'Fail in get 1p CalibSign',
    }
    return meter_info_keys, result_keys, fail_messages


def build_log_entry(mac, meter_info, test_result, bookName, fileName, com_port=None):
    """Bundle one port's results into a single dictionary instead of the
    old positional 5-item list built by result_log_dump(). Keys are
    self-describing, and com_port travels with the entry so
    run_calibration_test() can key its return value by COM port without
    needing a second parallel structure. Identical shape to
    mct_multiport.py's build_log_entry()."""
    return {
        'mac': mac,
        'meter_info': meter_info,
        'result': test_result,
        'bookName': bookName,
        'fileName': fileName,
        'com_port': com_port,
    }


def build_fail_messages(com_port, test_result, fail_message_lookup):
    """Named-key replacement for the old `CALIB_Fail_list[idx] for idx in
    fail_indexes` pattern - there is no positional index to keep in sync
    with result_list any more, so a step's failure text can never attach
    to the wrong step."""
    messages = []
    for step_key, value in test_result.items():
        if value == 'fail':
            text = fail_message_lookup.get(step_key, f"Fail in {step_key}")
            messages.append("COM Port: {}, {}".format(com_port, text))
    return messages


def verify_log_xlsc(bookName, fileName):
    loc = bookName
    try:
        wb = openpyxl.load_workbook(loc)
        sheet = wb.active
        _ = sheet.cell(row=1, column=1).value
    except Exception:
        logging.info("LOG XL file not found, creating one for you")
        wb = openpyxl.Workbook()
        wb.create_sheet(index=0, title=fileName)
        sheet = wb.active
        logging.info(f"sheet name = {sheet.title}")
        del wb['Sheet']
        wb.save(loc)
        logging.info("New xlsc file created")
        return False
    else:
        return True


def get_header_column_map(sheet):
    """Read the header row (row 1) into {header_name: column_index}.
    Writing a row then becomes a name -> column lookup instead of relying
    on dict insertion order lining up with header order. Identical to
    mct_multiport.py's get_header_column_map()."""
    header_map = {}
    for col_idx, cell in enumerate(sheet[1], start=1):
        if cell.value is not None:
            header_map[cell.value] = col_idx
    return header_map


def add_log_xlsc(log_entry):
    """Append one row to the log workbook from a dictionary-shaped
    log_entry (see build_log_entry). Every value is written to the column
    matching its own key/header name - looked up by name, not position -
    so a row's data can never land under the wrong header even after a
    Phase+Neutral merge. If a key isn't in the header yet, the sheet is
    extended with a new column instead of silently dropping the value.
    Identical to mct_multiport.py's add_log_xlsc()."""
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
#         import sys
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
#     except Exception:
#         logging.error("MAC address lookup failed")
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
    logging.info(f"In Calibration, MAC Address of system: {mac}")
    return mac


def addDefaultCalibLog(bookName, fileName):
    """Create the log workbook (if missing) and write its header row.
    Headers come from get_calib_phase_field_templates() +
    get_calib_neutral_field_templates(), so they always match the keys
    the workers will populate - no separate hand-maintained header list
    to keep in sync. Identical pattern to mct_multiport.py's
    addDefaultMctLog()."""
    if verify_log_xlsc(bookName, fileName):
        return

    logging.info("xlsx file for log not found. creating one to store test report")

    phase_meter_keys, phase_result_keys, _ = get_calib_phase_field_templates()
    neutral_meter_keys, neutral_result_keys, _ = get_calib_neutral_field_templates()

    # dict.fromkeys() dedupes while preserving order - both templates
    # declare 'Meter_PCB_Serial_No' (it's how the two phases get merged),
    # so a plain concatenation would create two columns with the same
    # header name; get_header_column_map() would then only ever resolve
    # to the LAST one, silently leaving the first always blank.
    meter_info_keys = list(dict.fromkeys(phase_meter_keys + neutral_meter_keys + ['Overall_Result']))
    result_keys = list(dict.fromkeys(phase_result_keys + neutral_result_keys))

    wb = openpyxl.load_workbook(bookName)
    sheet = wb[fileName]

    headers = ['MAC_ADDR', 'Index'] + meter_info_keys + result_keys
    for col_idx, header in enumerate(headers, start=1):
        sheet.cell(row=1, column=col_idx).value = header

    wb.save(bookName)
    logging.info("New xlsx file created with headers")


def prompt_bench_power(prompt_text, title="Bench Power", min_value=1199.4, max_value=1200.6):
    """Popup-based replacement for the original input()-based bench power
    prompt (`float(input("Enter Bench Power..."))`). Loops until a valid
    numeric value within [min_value, max_value] is entered via a real
    dialog instead of blocking on stdin - necessary because
    run_calibration_test() runs on a background QThread with no attached
    console, where input() would hang forever with no visible prompt at all.

    Uses _dialog_bridge, which shows the dialog on the main Qt thread and
    blocks this (worker) thread until it's answered - see
    _MainThreadDialogBridge's docstring for why that replaced the previous
    easygui/Tkinter-based version."""
    while True:
        raw_value = _dialog_bridge.enterbox(
            msg=f"{prompt_text}\n\nValid range: {min_value} - {max_value}",
            title=title,
        )
        if raw_value is None:
            # Cancel/closed the dialog - re-prompt rather than silently
            # proceeding with no value, matching the original loop's
            # "never exits without a valid entry" behavior.
            _dialog_bridge.msgbox("A bench power value is required to continue.", title)
            continue
        try:
            value = float(raw_value)
        except ValueError:
            _dialog_bridge.msgbox(f"'{raw_value}' is not a valid number. Please try again.", title)
            continue

        logging.info(f"Input for {title}: {value}")
        if min_value <= value <= max_value:
            return value

        _dialog_bridge.msgbox(
            f"{value} is out of range. Please enter a value between {min_value} and {max_value}.",
            title,
        )


class StoppableThread(Thread):
    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()



def get_cofficient_range(tool_name, meter_name):
    if 'better' in meter_name.lower():
        coffient_dict = {
            "FrequencyCoeff_min": 0,
            "FrequencyCoeff_max": 2,
            "VCoeff_min": 0,
            "VCoeff_max": 2,
            "ICoeff_0_min": 0,
            "ICoeff_0_max": 2,
            "ICoeff_1_min": 0,
            "ICoeff_1_max": 2,
            "ActPowerCoeff_0_min": 0,
            "ActPowerCoeff_0_max": 2,
            "ActPowerCoeff_1_min": 0,
            "ActPowerCoeff_1_max": 2,
            "PhAngle_0_min": 0,
            "PhAngle_0_max": 2,
            "PhAngle_1_min": 0,
            "PhAngle_1_max": 2
            }
    else:
        if ('wb' in tool_name.lower()) or ('tn' in tool_name.lower()):
            coffient_dict = {
                "FrequencyCoeff_min": 0.99,
                "FrequencyCoeff_max": 1.1,
                "VCoeff_min": 0.00044,
                "VCoeff_max": 0.00047,
                "ICoeff_0_min": 0.00000350,
                "ICoeff_0_max": 0.00000400,
                "ICoeff_1_min": 0.000000190,
                "ICoeff_1_max": 0.000000240,
                "ActPowerCoeff_0_min": 0.00000000150,
                "ActPowerCoeff_0_max": 0.00000000200,
                "ActPowerCoeff_1_min": 0.0000000000900,
                "ActPowerCoeff_1_max": 0.0000000000950,
                "PhAngle_0_min": 0.13,
                "PhAngle_0_max": 0.15,
                "PhAngle_1_min": 0.11,
                "PhAngle_1_max": 0.14
                }
        else:
            coffient_dict = {
                "FrequencyCoeff_min": 0.99,
                "FrequencyCoeff_max": 1.1,
                "VCoeff_min": 0.00044,
                "VCoeff_max": 0.00047,
                "ICoeff_0_min": 0.00000350,
                "ICoeff_0_max": 0.00000400,
                "ICoeff_1_min": 0.000000340,
                "ICoeff_1_max": 0.000000400,
                "ActPowerCoeff_0_min": 0.00000000150,
                "ActPowerCoeff_0_max": 0.00000000200,
                "ActPowerCoeff_1_min": 0.000000000150,
                "ActPowerCoeff_1_max": 0.000000000200,
                "PhAngle_0_min": 0.13,
                "PhAngle_0_max": 0.15,
                "PhAngle_1_min": 0.11,
                "PhAngle_1_max": 0.14
                }
    return coffient_dict


def worker_function_phase(data_dict, com_port, portID, result_queue, abort_flag, result_log):
    """Phase Calibration worker. Populates named meter_info/test_result
    dicts instead of positional MeterInfo/result_list, then stores the
    combined entry in result_log[com_port] (a dict, matching
    mct_multiport.py's phase1_results) instead of appending a 5-item
    list to a shared list."""
    logging.info(
        f"Waiting {data_dict.get('Bench_stabT_StartingPhaseT', 30)}s For Bench Stablization before Calibration Started"
    )
    time.sleep(data_dict.get("Bench_stabT_StartingPhaseT", 30))

    try:
        ser = serial.Serial(com_port, baudrate=9600, timeout=20)
        if not ser:
            result_queue.append(["com port is unable to open: {}".format(com_port)])
            return

        cases = TestCase(ser, portID, data_dict.get("NIC_PCB_LENGTH", 27))
        toolName = data_dict.get("TOOL_TYPE", "RF").lower()
        mac = get_system_mac_address(toolName)

        meter_info = {}
        test_result = {}
        meter_type = data_dict.get("METER_TYPE", "Garud_1PH").lower()
        project_name = data_dict.get("PROJECT", 'up').lower()
        bookName = get_log_book_path(meter_type, project_name, toolName)
        fileName = toolName.upper() + "_DATA_LOG"
        starttime = datetime.datetime.now()
        MAIN_PCB_SFG_PREFIX = data_dict.get("MAIN_PCB_SFG_PREFIX", "0000001")
        METER_ADDRESS = "255.255.255.255"

        meter_info['Date_time'] = datetime.datetime.now()
        addDefaultCalibLog(bookName, fileName)
        _, _, fail_message_lookup = get_calib_phase_field_templates()

        # Check COM port open/closed
        retryCnt = 3
        while retryCnt:
            logging.debug(f"Checking COM port connectivity, attempt: {4 - retryCnt}, for com: {com_port}")
            try:
                check_port = cases.check_port(com_port)
                if 'Fail' == check_port:
                    result_queue.append(["com port is unreachable: {}".format(com_port)])
                    abort_flag.set()
                    logging.debug(f"ser close for port : {com_port}")
                    ser.close()
                    return
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in calibration in checking COM port connectivity: {e}")
                retryCnt -= 1

        # Get Meter Address
        retryCnt = 3
        while retryCnt:
            logging.debug(f"Getting Meter Address, attempt: {4 - retryCnt}, for com: {com_port}")
            try:
                Meter_address = cases.get_Meter_address(str(METER_ADDRESS), com_port)
                if Meter_address.get('status', 'fail') == 'fail':
                    meter_info['Meter_IP_Address'] = str(Meter_address.get('mtr_address', 'None'))
                    test_result['Get_Meter_Address'] = 'fail'
                else:
                    meter_info['Meter_IP_Address'] = str(Meter_address.get('mtr_address', 'None'))
                    test_result['Get_Meter_Address'] = 'pass'
                logging.debug(f"Meter Address for {com_port}: {Meter_address}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in calibration in get meter address: {e}")
                retryCnt -= 1

        # Get PCB Serial number - this is the key later used to match
        # this Phase entry with its Neutral counterpart, since the meter
        # may move to a different COM port on the second bench.
        retryCnt = 3
        while retryCnt:
            logging.debug(f"Getting Meter PCB Serial Number, attempt: {4 - retryCnt}, for com: {com_port}")
            try:
                Pcb_serial_no = cases.Get_pcb_serial_num(com_port)
                meter_info['Meter_PCB_Serial_No'] = str(Pcb_serial_no)
                if (('R161' in Pcb_serial_no) or ('r161' in Pcb_serial_no)
                        or (str(Pcb_serial_no[9:16]) == str(MAIN_PCB_SFG_PREFIX))):
                    test_result['Get_Meter_PCB_No'] = 'pass'
                else:
                    test_result['Get_Meter_PCB_No'] = 'fail'
                logging.debug(f"Meter PCB Serial Number: {Pcb_serial_no}, for com: {com_port}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in calibration in get PCB Serial Number: {e}")
                retryCnt -= 1


        pct_result = db_connect.fetch_by_pcb_serial(Pcb_serial_no, meter_type)
        test_result['PCT_Check'] = 'pass' if pct_result else 'fail'

        if not pct_result:
            logging.info(
                f"PCT Check failed for com: {com_port}, PCB: {Pcb_serial_no}, "
                f"PCT overall_result: {pct_result!r} -- skipping Calib Unlock "
                f"and Phase Calibration for this meter"
            )

        if pct_result:
            # Calib Unlock
            retryCnt = 3
            while retryCnt:
                logging.debug(f"Performing Calibration Unlock, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    calib_unlock = cases.Calibration_unLock(com_port)
                    test_result['Calibration_Unlock'] = 'pass' if calib_unlock.get('status') == 'pass' else 'fail'
                    logging.debug(f"Calibration unlock result: {calib_unlock}, for com: {com_port}")
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in calibration in performing calibration unlock: {e}, for COM: {com_port}")
                    retryCnt -= 1

            # # Set Relay Mode (On/Off, Event Log)
            # retryCnt = 3
            # while (retryCnt):
            #     logging.debug(f"Set Relay Mode for com: {com_port}, attempt: {4-retryCnt}")
            #     try:
            #         relay_mode = cases.Set_Meter_RelayMode(0, com_port)
            #         if relay_mode.get("status").lower() =='fail':
            #             meter_info['Relay_Mode'] = ''
            #             test_result['Set_Relay_Mode'] = 'fail'
            #         else:
            #             meter_info['Relay_Mode'] = '0'
            #             test_result['Set_Relay_Mode'] = 'pass'
            #         logging.debug(f"Set Relay Mode for com: {com_port}, response: {relay_mode}")
            #         # retryCnt = 0
            #         break
            #     except Exception as e:
            #         logging.error(f"Error in Set Relay Mode for com: {com_port}, error: {str(e)}")
            #         retryCnt = retryCnt-1
            #         if retryCnt == 0:
            #             meter_info['Relay_Mode'] = ''
            #             test_result['Set_Relay_Mode'] = 'fail'

            # Start Phase Calibration
            retryCnt = 3
            while retryCnt:
                logging.debug(f"Performing Phase Calibration, attempt: {4 - retryCnt}, for com: {com_port}")
                try:
                    phase_calib = cases.start_phase_calib(com_port)
                    test_result['Phase_calibration'] = 'pass' if phase_calib.get('status') == 'pass' else 'fail'
                    logging.debug(f"Phase Calibration Result: {phase_calib}, for com: {com_port}")
                    retryCnt = 0
                except Exception as e:
                    logging.error(f"Error in calibration in Phase Calibration: {str(e)}")
                    retryCnt -= 1

        ser.close()

        # Overall_Result is intentionally NOT set here - run_calibration_test()
        # merges in the Neutral Calibration (worker_function_neutral_calib_coff)
        # result for this meter first (matched by Meter_PCB_Serial_No, since
        # the meter may be moved to a different COM port on the second bench)
        # and computes Overall_Result once, from the combined result dict.
        result_log[com_port] = build_log_entry(mac, meter_info, test_result, bookName, fileName, com_port)
        time.sleep(0.1)

        EndTime = datetime.datetime.now()
        logging.info(f"Phase Calibration StartTime: {starttime}, EndTime: {EndTime}, Diff: {EndTime - starttime}")

        fail_messages = build_fail_messages(com_port, test_result, fail_message_lookup)
        if fail_messages:
            result_queue.append(fail_messages)

    except Exception as e:
        logging.error(f"Error in worker_function_phase for COM {com_port}: {e}")
        result_queue.append(["com port is unreachable:{}".format(com_port)])
        return


def worker_function_neutral_calib_coff(data_dict, com_port, portID, result_queue, abort_flag, result_log):
    """Neutral Calibration worker. Same dict-based approach as
    worker_function_phase - see that function's docstring and the module
    docstring for the overall pattern."""
    logging.info(
        f"Waiting {data_dict.get('Bench_stabT_StartingneutralCalib', 30)}s "
        f"For Bench Stablization before Neutral Calibration"
    )
    time.sleep(data_dict.get("Bench_stabT_StartingneutralCalib", 30))

    try:
        ser = serial.Serial(com_port, baudrate=9600, timeout=20)
        if not ser:
            result_queue.append(["com port is unable to open: {}".format(com_port)])
            return

        cases = TestCase(ser, portID, data_dict.get("NIC_PCB_LENGTH", 27))
        toolName = data_dict.get("TOOL_TYPE", "RF").lower()
        mac = get_system_mac_address(toolName)

        meter_info = {}
        test_result = {}
        meter_type = data_dict.get("METER_TYPE", "Garud_1PH").lower()
        project_name = data_dict.get("PROJECT", 'up').lower()
        bookName = get_log_book_path(meter_type, project_name, toolName)
        fileName = toolName.upper() + "_DATA_LOG"
        starttime = datetime.datetime.now()
        MAIN_PCB_SFG_PREFIX = data_dict.get("MAIN_PCB_SFG_PREFIX", "0000001")

        addDefaultCalibLog(bookName, fileName)
        _, _, fail_message_lookup = get_calib_neutral_field_templates()

        logging.info(f"Starting Neutral Calibration for COM Port: {com_port}")

        # Check COM port status
        retryCnt = 3
        while retryCnt:
            logging.info(f"Checking COM Port connectivity for {com_port}, attempts left: {retryCnt}")
            try:
                check_port = cases.check_port(com_port)
                if 'Fail' == check_port:
                    result_queue.append(["com port is unreachable: {}".format(com_port)])
                    abort_flag.set()
                    return
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in calibration in checking COM port connectivity: {e}")
                retryCnt -= 1

        # Get PCB Serial Number - the matching key back to the Phase entry
        retryCnt = 3
        while retryCnt:
            logging.debug(f"Getting PCB Serial Number for {com_port}, attempts left: {retryCnt}")
            try:
                Pcb_serial_no = cases.Get_pcb_serial_num(com_port)
                meter_info['Meter_PCB_Serial_No'] = str(Pcb_serial_no)
                retryCnt = 0
                logging.debug(f"PCB Serial Number for {com_port}: {Pcb_serial_no}")
            except Exception as e:
                logging.debug(f"Error in calibration in getting PCB serial number before neutral calibration: {e}")
                retryCnt -= 1

        # Start Neutral Calibration
        retryCnt = 3
        while retryCnt:
            logging.info(f"Performing Neutral Calibration, attempt: {4 - retryCnt}, for com: {com_port}")
            try:
                neutral_calib = cases.start_nuetral_calib(com_port)
                test_result['Neutral_calibration'] = 'pass' if neutral_calib.get('status') == 'pass' else 'fail'
                logging.debug(f"Neutral Calibration Result: {test_result['Neutral_calibration']}, for com: {com_port}")
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in Neutral Calibration: {str(e)}, for com: {com_port}")
                retryCnt -= 1

        logging.info(
            f"Waiting for calibration completion after Neutral Calibration: "
            f"{data_dict.get('StabT_neutralCalib', 30)}"
        )
        time.sleep(data_dict.get("StabT_neutralCalib", 30))

        # Check 1P Calib Coefficient - every computed value below is
        # assigned to its own explicitly named meter_info key (see
        # get_calib_neutral_field_templates()'s docstring for why this
        # matters), rather than appended positionally.
        retryCnt = 3
        while retryCnt:
            logging.debug(f"Getting 1P Calibration Coefficients, attempt: {4 - retryCnt}, for com: {com_port}")
            try:
                calib_cofficient = cases.get_1p_calib_coffi(com_port)
                calib_cofficient_val = get_cofficient_range(project_name, meter_type)
                logging.debug(f"1P Calibration Coefficients for {com_port}: {calib_cofficient}, updated ranges: {calib_cofficient_val}")

                if 'Fail' in calib_cofficient:
                    for key in ('CalibSign', 'FrequencyCoeff', 'VCoeff', 'ICoeff[0]', 'ICoeff[1]',
                                'ActPowerCoeff[0]', 'ActPowerCoeff[1]', 'PhAngle[0]', 'PhAngle[1]'):
                        meter_info[key] = 'Fail'
                    test_result['Get_1p_calib_cofficient'] = 'fail'
                    test_result['CalibSign_Status'] = 'fail'
                    meter_info['FrequencyCoeff_min'] = f'{calib_cofficient_val.get("FrequencyCoeff_min")}'
                    meter_info['FrequencyCoeff_max'] = f'{calib_cofficient_val.get("FrequencyCoeff_max")}'
                    meter_info['VCoeff_min'] = f'{calib_cofficient_val.get("VCoeff_min")}'
                    meter_info['VCoeff_max'] = f'{calib_cofficient_val.get("VCoeff_max")}'
                    meter_info['ICoeff[0]_min'] = f'{calib_cofficient_val.get("ICoeff[0]_min")}'
                    meter_info['ICoeff[0]_max'] = f'{calib_cofficient_val.get("ICoeff[0]_max")}'
                    meter_info['ICoeff[1]_min'] = f'{calib_cofficient_val.get("ICoeff[1]_min")}'
                    meter_info['ICoeff[1]_max'] = f'{calib_cofficient_val.get("ICoeff[1]_max")}'
                    meter_info['ActPowerCoeff[0]_min'] = f'{calib_cofficient_val.get("ActPowerCoeff[0]_min")}'
                    meter_info['ActPowerCoeff[0]_max'] = f'{calib_cofficient_val.get("ActPowerCoeff[0]_max")}'
                    meter_info['ActPowerCoeff[1]_min'] = f'{calib_cofficient_val.get("ActPowerCoeff[1]_min")}'
                    meter_info['ActPowerCoeff[1]_max'] = f'{calib_cofficient_val.get("ActPowerCoeff[1]_max")}'
                    meter_info['PhAngle[0]_min'] = f'{calib_cofficient_val.get("PhAngle[0]_min")}'
                    meter_info['PhAngle[0]_max'] = f'{calib_cofficient_val.get("PhAngle[0]_max")}'
                    meter_info['PhAngle[1]_min'] = f'{calib_cofficient_val.get("PhAngle[1]_min")}'
                    meter_info['PhAngle[1]_max'] = f'{calib_cofficient_val.get("PhAngle[1]_max")}'
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
                        meter_info['FrequencyCoeff_min'] = '0'
                        meter_info['FrequencyCoeff_max'] = '2'
                        meter_info['VCoeff_min'] = '0'
                        meter_info['VCoeff_max'] = '2'
                        meter_info['ICoeff[0]_min'] = '0'
                        meter_info['ICoeff[0]_max'] = '2'
                        meter_info['ICoeff[1]_min'] = '0'
                        meter_info['ICoeff[1]_max'] = '2'
                        meter_info['ActPowerCoeff[0]_min'] = '0'
                        meter_info['ActPowerCoeff[0]_max'] = '2'
                        meter_info['ActPowerCoeff[1]_min'] = '0'
                        meter_info['ActPowerCoeff[1]_max'] = '2'
                        meter_info['PhAngle[0]_min'] = '0'
                        meter_info['PhAngle[0]_max'] = '2'
                        meter_info['PhAngle[1]_min'] = '0'
                        meter_info['PhAngle[1]_max'] = '2'
                        # NOTE: preserved verbatim from the original script -
                        # the "better" branch's coefficient range check
                        # always appended 'pass' on either outcome (a
                        # pre-existing quirk, not something introduced by
                        # this refactor).
                        # test_result['Get_1p_calib_cofficient'] = 'pass'
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
                        test_result['CalibSign_Status'] = (
                            'pass' if str(calib_cofficient.get('CalibSign')) == str(2882400171) else 'fail'
                        )
                    else:
                        # is_wb = 'wb' in project_name.lower()
                        is_wb = False
                        if ('wb' in project_name.lower()) or ('tn' in project_name.lower()):
                            is_wb = True
                        else:
                            is_wb = False
                        if is_wb:
                            ranges = {
                                'FrequencyCoeff': ('0.99', '1.1'),
                                'VCoeff': ('0.00044', '0.00047'),
                                'ICoeff[0]': ('0.00000350', '0.00000400'),
                                'ICoeff[1]': ('0.000000190', '0.000000240'),
                                'ActPowerCoeff[0]': ('0.00000000150', '0.00000000200'),
                                'ActPowerCoeff[1]': ('0.0000000000900', '0.0000000000950'),
                                'PhAngle[0]': ('0.13', '0.15'),
                                'PhAngle[1]': ('0.11', '0.14'),
                            }
                        else:
                            ranges = {
                                'FrequencyCoeff': ('0.99', '1.1'),
                                'VCoeff': ('0.00044', '0.00047'),
                                'ICoeff[0]': ('0.00000350', '0.00000400'),
                                'ICoeff[1]': ('0.000000340', '0.000000400'),
                                'ActPowerCoeff[0]': ('0.00000000150', '0.00000000200'),
                                'ActPowerCoeff[1]': ('0.000000000150', '0.000000000200'),
                                'PhAngle[0]': ('0.13', '0.15'),
                                'PhAngle[1]': ('0.11', '0.14'),
                            }
                        for key, (lo, hi) in ranges.items():
                            meter_info[f'{key}_min'] = lo
                            meter_info[f'{key}_max'] = hi

                        in_range = True
                        for key, (lo, hi) in ranges.items():
                            value = float(calib_cofficient.get(key))
                            if not (float(lo) <= value <= float(hi)):
                                in_range = False
                                break
                        test_result['Get_1p_calib_cofficient'] = 'pass' if in_range else 'fail'
                        test_result['CalibSign_Status'] = (
                            'pass' if str(calib_cofficient.get('CalibSign')) == str(2882400171) else 'fail'
                        )

                
                retryCnt = 0
            except Exception as e:
                logging.error(f"Error in 1p calib coefficient for COM {com_port}: {e}")
                retryCnt -= 1

        ser.close()

        # Overall_Result is computed later by run_calibration_test() after
        # merging into the matching Phase entry (see worker_function_phase's
        # note).
        result_log[com_port] = build_log_entry(mac, meter_info, test_result, bookName, fileName, com_port)
        time.sleep(0.1)

        EndTime = datetime.datetime.now()
        logging.info(f"Neutral Calibration StartTime: {starttime}, EndTime: {EndTime}, Diff: {EndTime - starttime}")

        fail_messages = build_fail_messages(com_port, test_result, fail_message_lookup)
        if fail_messages:
            result_queue.append(fail_messages)

    except Exception as e:
        logging.error(f"Error in worker_function_neutral_calib_coff for COM {com_port}: {e}")
        result_queue.append(["com port is unreachable:{}".format(com_port)])
        return


def merge_calib_results(phase_results, neutral_results):
    """Combine each Neutral Calibration entry into its matching Phase
    entry, matched by Meter_PCB_Serial_No (not COM port - the meter can
    be moved to a different COM port on the second bench). Directly
    mirrors mct_multiport.py's merge_no_load_result(), including its
    three explicit safety guards instead of a blind
    `entry1['result'].update(entry2['result'])`:

    1. Ambiguous PCB match - two Phase entries share the same PCB serial
       number. Merges into the first match for compatibility, but logs a
       warning so the collision isn't invisible.
    2. Double merge - two different Neutral entries both match the same
       Phase entry. Logs a warning instead of silently letting the
       second merge clobber the first's data.
    3. Pass/fail value mismatch on a shared key - resolved by keeping
       'fail' (the safe answer) and logging the disagreement, rather than
       letting whichever value came later silently win.
    """
    unmatched = []
    merged_into = {}  # matched_com -> list of neutral com_ports already merged into it

    for com_port2, entry2 in neutral_results.items():
        target_pcb = entry2['meter_info'].get('Meter_PCB_Serial_No')
        candidates = [
            com_port1 for com_port1, entry1 in phase_results.items()
            if str(entry1.get('meter_info', {}).get('Meter_PCB_Serial_No','')) == str(target_pcb)
        ]

        if not candidates:
            logging.warning(
                f"No matching Phase result found for Neutral Calibration PCB "
                f"{target_pcb} (COM {com_port2})"
            )
            unmatched.append(com_port2)
            continue

        if len(candidates) > 1:
            logging.warning(
                f"PCB {target_pcb} (Neutral Calibration COM {com_port2}) matches multiple "
                f"Phase entries {candidates} - two meters appear to share a PCB serial "
                f"number. Merging into {candidates[0]}; verify this PCB manually."
            )
        matched_com = candidates[0]

        if matched_com in merged_into:
            logging.warning(
                f"Phase entry {matched_com} already received a Neutral Calibration merge "
                f"from COM {merged_into[matched_com]}; COM {com_port2} is merging into it "
                f"again and will overwrite that earlier merge's data."
            )
        merged_into.setdefault(matched_com, []).append(com_port2)

        entry1 = phase_results[matched_com]
        entry1['meter_info'].update(entry2['meter_info'])

        for key, value in entry2['result'].items():
            existing = entry1['result'].get(key)
            if existing is not None and existing != value:
                resolved = 'fail' if 'fail' in (existing, value) else value
                logging.warning(
                    f"Result step '{key}' for {matched_com} disagrees between Phase "
                    f"('{existing}') and Neutral ('{value}') data; keeping '{resolved}' "
                    f"instead of silently letting one value overwrite the other."
                )
                entry1['result'][key] = resolved
            else:
                entry1['result'][key] = value

    return unmatched


def finalize_overall_results(results):
    """Compute Overall_Result for every entry from its (possibly merged)
    result dict, and set it last so it always lands as the final Excel
    column regardless of what got merged in beforehand. Identical to
    mct_multiport.py's finalize_overall_results()."""
    for entry in results.values():
        entry['meter_info']['Overall_Result'] = 'fail' if 'fail' in entry['result'].values() else 'pass'


# Sentinel values written into the log when a step's real data was never
# recorded (worker crashed/aborted before reaching that step). A missing
# result step reads as 'fail', never a silent 'pass' - untested must
# never look identical to tested-and-passed. Identical to
# mct_multiport.py's NOT_TESTED_* constants.
NOT_TESTED_METER_VALUE = None
NOT_TESTED_RESULT_VALUE = 'fail'


def fill_missing_fields(entry, meter_info_keys, result_keys):
    """Ensure every field in meter_info_keys/result_keys exists on
    `entry`, filling in NOT_TESTED_* defaults for anything a worker
    never got to write. Identical to mct_multiport.py's
    fill_missing_fields() - see that function's docstring for why this
    is what actually prevents the Excel "column mismatch" problem."""
    for key in meter_info_keys:
        entry['meter_info'].setdefault(key, NOT_TESTED_METER_VALUE)
    for key in result_keys:
        entry['result'].setdefault(key, NOT_TESTED_RESULT_VALUE)

def run_calibration_test(data_dict, active_port_list, upload_bench):
    """Entry point called by MainWindow (via FunctionThreadRunner, exactly
    the way run_mct_test() is called) as:

        results = run_calibration_test(data_dict, ports, bench_number)

    Returns {com_port: {'phase': 'pass'/'fail', 'neutral': 'pass'/'fail'}}
    - the exact shape MainWindow._on_test_finished already expects for
    "calibration_test" (one script run reporting into both the Phase and
    Neutral table columns).

    NOTE - two deliberate deviations from the original interactive
    run(), required to make this callable from a background thread with
    no attached console (a QThread has no stdin):
      1. Ports are passed in directly (active_port_list) instead of
         auto-scanned from serial.tools.list_ports.comports() - matching
         run_mct_test(data_dict, active_port_list, upload_bench)'s
         signature exactly.
      2. The interactive input() prompts for bench power are replaced
         with data_dict-sourced values (Bench_Power_Phase /
         Bench_Power_Neutral) - input() would hang forever with no
         visible prompt when called from a background thread. Set these
         two keys in your config if you need them validated/logged; the
         validation range check (1199.4-1200.6) from the original
         prompts is no longer enforced here since there's no interactive
         loop to re-prompt on an out-of-range value.

    The "Switch the Bench for Neutral Calibration" prompt between the
    Phase and Neutral rounds, and the bench-power prompts, all go through
    _dialog_bridge so they render on the main Qt thread - see
    _MainThreadDialogBridge's docstring.
    """
    logging.info("Starting CALIBRATION Testing Script")
    portID = data_dict.get("portID", 4)
    list_port = list(active_port_list)

    results = []
    results1 = []
    phase_results = {}    # worker_function_phase, keyed by COM port
    neutral_results = {}  # worker_function_neutral_calib_coff, keyed by COM port
    abort_flag = threading.Event()

    toolName = data_dict.get("TOOL_TYPE", "RF").lower()
    meter_type = data_dict.get("METER_TYPE", "Garud_1PH").lower()
    project_name = data_dict.get("PROJECT", 'up').lower()
    bookName = get_log_book_path(meter_type, project_name, toolName)
    fileName = toolName.upper() + "_DATA_LOG"
    addDefaultCalibLog(bookName, fileName)

    # phase_power = prompt_bench_power("Enter Bench Power for Phase Calibration", title="Phase Calibration Bench Power")
    phase_power = prompt_bench_power("Enter Bench Power for Phase Calibration", title="Phase Calibration Bench Power")

    logging.info(f"Enter Bench Power for Phase Calibration (1199.4 - 1200.6): {phase_power}")
    logging.info(f"Starting CALIBRATION Testing on ports: {list_port}")

    threads = [
        StoppableThread(target=worker_function_phase, args=(data_dict, port_name, portID, results, abort_flag, phase_results))
        for port_name in list_port
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    logging.info(f"Waiting {data_dict.get('StabT_phaseCalib', 30)}s for phase calibration completion")
    time.sleep(data_dict.get("StabT_phaseCalib", 30))

    _dialog_bridge.msgbox("Swich the Bench for Neutral Calibration", "Action Required for Calibration")
    logging.info("Swich the Bench for Neutral Calibration Action Required for Calibration")

    pct_failed_ports = [
        port_name for port_name in list_port
        if phase_results.get(port_name, {}).get('result', {}).get('PCT_Check') != 'pass'
    ]
    if pct_failed_ports:
        logging.info(f"Skipping Neutral Calibration for PCT-failed ports: {pct_failed_ports}")
    neutral_port_list = [port_name for port_name in list_port if port_name not in pct_failed_ports]


    neutral_power = prompt_bench_power("Enter Bench Power for Neutral Calibration", title="Neutral Calibration Bench Power")
    logging.info(f"Enter Bench Power for Neutral Calibration (1199.4 - 1200.6): {neutral_power}")

    threads = [
        StoppableThread(target=worker_function_neutral_calib_coff, args=(data_dict, port_name, portID, results1, abort_flag, neutral_results))
        for port_name in neutral_port_list
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    merge_calib_results(phase_results, neutral_results)
    results.extend(results1)

    # Guarantee every requested port has a COMPLETE row before writing to
    # Excel/returning results - same "placeholder + fill_missing_fields"
    # approach as mct_multiport.py's run_mct_test(), so a port that never
    # got a Phase entry at all (worker crashed before ever calling
    # result_log[com_port] = ...) still gets a definitive fail rather
    # than being silently missing.
    phase_meter_keys, phase_result_keys, _ = get_calib_phase_field_templates()
    neutral_meter_keys, neutral_result_keys, _ = get_calib_neutral_field_templates()
    all_meter_keys = list(dict.fromkeys(phase_meter_keys + neutral_meter_keys))
    all_result_keys = list(dict.fromkeys(phase_result_keys + neutral_result_keys))

    for port_name in list_port:
        if port_name not in phase_results:
            placeholder = build_log_entry(
                mac='NOT_TESTED', meter_info={}, test_result={},
                bookName=bookName, fileName=fileName, com_port=port_name,
            )
            placeholder['fully_untested'] = True
            phase_results[port_name] = placeholder

        entry = phase_results[port_name]
        fill_missing_fields(entry, all_meter_keys, all_result_keys)

    finalize_overall_results(phase_results)

    for com_port_key, entry in phase_results.items():
        try:
            add_log_xlsc(entry)
        except Exception:
            logging.info("unknown error in add logs in Excel")
            continue

    # Dictionary-based pass/fail summary keyed by COM port, split into
    # the two columns MainWindow._on_test_finished expects for
    # "calibration_test": {'phase': ..., 'neutral': ...}. Every port
    # that was asked for gets an entry, including ones that never
    # produced any real result (reported as 'fail' for both, via the
    # placeholder + fill_missing_fields step above).
    calib_pass_fail_by_com = {}
    for port_name in list_port:
        entry = phase_results[port_name]
        result = entry['result']
        coeff_ok = (
            result.get('Get_1p_calib_cofficient', 'fail') == 'pass'
            and result.get('CalibSign_Status', 'fail') == 'pass'
        )
        phase_ok = coeff_ok and result.get('Phase_calibration', 'fail') == 'pass'
        neutral_ok = coeff_ok and result.get('Neutral_calibration', 'fail') == 'pass'
        calib_pass_fail_by_com[port_name] = {
            'phase': 'pass' if phase_ok else 'fail',
            'neutral': 'pass' if neutral_ok else 'fail',
        }

    if data_dict.get("IS_DATA_CONN", 1) == 1:
        try:
            df_frame = pd.read_excel(bookName)
            
            if 'better' in meter_type.lower():
                status, error = db_connect.upload_dataframe(df_frame, 'better')
            else:
                status, error = db_connect.upload_dataframe(df_frame, 'garud')
            if not status:
                logging.info(f"DB upload failed. Saved locally for retry. Error: {error}")

            else:
                if(len(phase_results) != 0):       # if the result file is empty then don't upload to server
                    logging.info("Uploading CALIBRATION Test Results to Cloud Storage")

                    # for uploADING DATA OF CALIBRATION TO DIRECT CLOUD
                # ****************************************************************************************


                    def upload_to_aws(local_folder, bucket, s3_file,sub_folder, file_time,folder_name1, local_file_path=None):
                        if local_file_path is None:
                            local_file_path = s3_file
                        s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                                        aws_secret_access_key=SECRET_KEY)
                        logging.info(f"Uploaded file: {str(upload_bench + "_" + file_time + "_" + s3_file)}")

                        try:
                            s3.upload_file(local_file_path, bucket, FOLDER_NAME +  "/{0}/{1}/{2}/{3}".format(folder_name1,sub_folder,local_folder, str(upload_bench + "_" + file_time + "_" + s3_file)))
                            logging.info("Upload Successful")
                            os.remove(local_file_path)
                            return True
                        except NoCredentialsError:
                            logging.error("Credentials not available")
                            return False
                        except Exception as e:
                            logging.error(str(e))
                            logging.error("The file was not found")
                            return False
                    

                    al = os.listdir(CALIB_FOLDER)
                    txt = list(filter(lambda x: x[-5:] == '.xlsx',al))
                    logging.info(f"{txt}")
                    if len(txt) == 0:
                        logging.info("file doesn't exist")#/dev/gp-gateway"
                        return#args.baud_rate = 9600

                    for j in range(len(txt)):    
                        # today = date.today()
                        # print("Today date is: ", today)

                        temp_time = datetime.datetime.now()
                        logging.info(f"time = {temp_time}")
                        date_only = datetime.datetime.strftime(temp_time, '%Y-%m-%d')
                        time_only = datetime.datetime.strftime(temp_time, '%H_%M_%S')
                        logging.info(f"time is: {time_only}")
                        logging.info(f"date is: {date_only}")



                        sub_folder = "UNKNOWN"
                        xyx =  str(txt[j])
                        # print "args.new_name",xyx
                        # print xyx.find("RTT")
                        if("PCT" in xyx):
                            sub_folder = "PCT"
                        elif("calib" in xyx.lower()):
                            sub_folder = "CALIBRATION"
                        elif("rtt" in xyx.lower()):
                            sub_folder = "RTT"    
                        else:
                            logging.info("improper file name given for tool type")
                            continue
                        logging.info (f"sub_folder = {sub_folder}")

                        # print (xyx.find("AP"))
                        folder_name1 = "UNKNOWN"
                        if "SM_1P" in xyx:
                            folder_name1 = "ISM_1P"
                        elif "SM_3P" in xyx:
                            folder_name1 = "ISM_3P"
                        elif "AP_3P" in xyx:
                            folder_name1 = "CAP_3P"
                        elif "CU_" in xyx:
                            folder_name1 = "DCU_"  
                        elif("garud" in xyx.lower()):
                            folder_name1 = "Garud"   
                        elif("better" in xyx.lower()):
                            folder_name1 = "Better_Meter"      
                        else:
                            logging.info("improper file name given for Meter type")
                            continue
                        logging.info(f"folder_name1 = {folder_name1}")

                        local_path = os.path.join(CALIB_FOLDER, txt[j])
                        logging.info(f"Uploading file: {str(txt[j])} to bucket: {BUCKET_NAME} in folder: {FOLDER_NAME}/{folder_name1}/{date_only}, local_path: {local_path}")
                        uploaded = upload_to_aws(str(date_only), BUCKET_NAME, txt[j],sub_folder, time_only,folder_name1, local_file_path=local_path)
                        logging.info("CALIBRATION DATA SUCCESSFULLY UPLOADED TO CLOUD")


                    # ****************************************************************************************************************
                else:
                    print("Skipping to Upload the log file to server")
        
        except Exception as e:
            logging.error(f"Error writing DB log: {e}")
    else:
        logging.info("Upload data to EMS db flag is disable")
        if(len(phase_results) != 0):       # if the result file is empty then don't upload to server
            logging.info("Uploading CALIBRATION Test Results to Cloud Storage")

            # for uploADING DATA OF CALIBRATION TO DIRECT CLOUD
        # ****************************************************************************************

            def upload_to_aws(local_folder, bucket, s3_file,sub_folder, file_time,folder_name1, local_file_path=None):
                s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                                aws_secret_access_key=SECRET_KEY)
                logging.info(f"Uploaded file: {str(upload_bench + "_" + file_time + "_" + s3_file)}")

                try:
                    if local_file_path is None:
                        local_file_path = s3_file
                    s3.upload_file(local_file_path, bucket, FOLDER_NAME +  "/{0}/{1}/{2}/{3}".format(folder_name1,sub_folder,local_folder, str(upload_bench + "_" + file_time + "_" + s3_file)))
                    logging.info("Upload Successful")
                    os.remove(local_file_path)
                    return True
                except NoCredentialsError:
                    logging.error("Credentials not available")
                    return False
                except Exception as e:
                    logging.error(e)
                    logging.error("The file was not found")
                    return False
            

            al = os.listdir(CALIB_FOLDER)
            txt = list(filter(lambda x: x[-5:] == '.xlsx',al))
            logging.info(f"{txt}")
            if len(txt) == 0:
                logging.info("file doesn't exist")#/dev/gp-gateway"
                return#args.baud_rate = 9600

            for j in range(len(txt)):    
                # today = date.today()
                # print("Today date is: ", today)

                temp_time = datetime.datetime.now()
                logging.info(f"time = {temp_time}")
                date_only = datetime.datetime.strftime(temp_time, '%Y-%m-%d')
                time_only = datetime.datetime.strftime(temp_time, '%H_%M_%S')
                logging.info(f"time is: {time_only}")
                logging.info(f"date is: {date_only}")



                sub_folder = "UNKNOWN"
                xyx =  str(txt[j])
                # print "args.new_name",xyx
                # print xyx.find("RTT")
                if("PCT" in xyx):
                    sub_folder = "PCT"
                elif("calib" in xyx.lower()):
                    sub_folder = "CALIBRATION"
                elif("rtt" in xyx.lower()):
                    sub_folder = "RTT"    
                else:
                    logging.info("improper file name given for tool type")
                    continue
                logging.info(f"sub_folder = {sub_folder}")

                # print (xyx.find("AP"))
                folder_name1 = "UNKNOWN"
                if "SM_1P" in xyx:
                    folder_name1 = "ISM_1P"
                elif "SM_3P" in xyx:
                    folder_name1 = "ISM_3P"
                elif "AP_3P" in xyx:
                    folder_name1 = "CAP_3P"
                elif "CU_" in xyx:
                    folder_name1 = "DCU_"  
                elif("garud" in xyx.lower()):
                    folder_name1 = "Garud"   
                elif("better" in xyx.lower()):
                    folder_name1 = "Better_Meter"      
                else:
                    logging.info("improper file name given for Meter type")
                    continue
                logging.info(f"folder_name1 = {folder_name1}")

                local_path = os.path.join(CALIB_FOLDER, txt[j])
                logging.info(f"Uploading file: {str(txt[j])} to bucket: {BUCKET_NAME} in folder: {FOLDER_NAME}/{folder_name1}/{date_only}, local_path: {local_path}")
                uploaded = upload_to_aws(str(date_only), BUCKET_NAME, txt[j],sub_folder, time_only,folder_name1, local_file_path=local_path)
                # uploaded = upload_to_aws(str(date_only), BUCKET_NAME, txt[j],sub_folder, time_only,folder_name1 )
                logging.info("CALIBRATION DATA SUCCESSFULLY UPLOADED TO CLOUD")


            # ****************************************************************************************************************
        else:
            logging.info("Skipping to Upload the log file to server")

    logging.debug(f"Calibration Testing Completed with results: {phase_results}")
    if results:
        flat_results = [item for sublist in results for item in sublist]
        unique_results = sorted(list(set(flat_results)))
        msg_text = "\n".join(unique_results)
        _dialog_bridge.msgbox(msg_text, "Calibration Test Failures")
        logging.info(f"Calibration failures: {msg_text}")
    logging.info(f"Calibration Testing Completed: {calib_pass_fail_by_com}")
    return calib_pass_fail_by_com
    # return {'COM157': {'phase': 'pass', 'neutral': 'fail'}}