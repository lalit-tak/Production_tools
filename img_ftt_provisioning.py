# FLOW CHANGE: rtt_data / mct_data / Communication are no longer used here.
# The MCT check is now run directly inside ftt_merger_tool.main_function()
# (for 'img', '4g', and 'rf' tool types), reusing the PCB serial number
# FTT's own cases.Get_pcb_serial_num() command reads -- instead of this
# file reading the PCB serial separately via raw bytes (get_pcb_serial(),
# now removed) as a pre-stage before FTT was allowed to start.
import ftt_merger_tool
import time
import os
from multiprocessing import Process, Queue, freeze_support
import logging
from logging.handlers import TimedRotatingFileHandler
import json
import re
import tkinter as tk
from tkinter import scrolledtext
from tkinter import font
from colorama import Fore, Style, init
from config import Config
import subprocess
import traceback
from provisioning_tool.ftt_prov_logging import setup_logger
setup_logger(enable_file_log=True)
init(autoreset=True)

# ---------------- LOGGING ----------------
# logging.basicConfig(
#     filename="IMG_FTT_PROVISIONING.txt",
#     level=logging.DEBUG,
#     format="%(asctime)s - %(levelname)s - %(message)s",
#     encoding="utf-8"
# )

# ---------------- GUI ----------------

def show_summary_all(results, tool_type="rf_ftt"):
    mct_applicable = any(t in tool_type.lower() for t in ('img', '4g', 'rf'))
    root = tk.Tk()
    if mct_applicable:
        root.title("MCT + FTT Summary")
    else:
        root.title("FTT Summary")

    # Window size
    w, h = 900, 600
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.resizable(False, False)

    tk.Label(root, text="SUMMARY", font=("Arial", 20, "bold")).pack(pady=10)

    # ---------- MAIN CONTAINER ----------
    main_frame = tk.Frame(root)
    main_frame.pack(fill="both", expand=True)

    # ---------- TEXT FRAME ----------
    text_frame = tk.Frame(main_frame)
    text_frame.pack(fill="both", expand=True, padx=20)

    text = scrolledtext.ScrolledText(
        text_frame,
        width=110,
        height=20,
        font=("Courier New", 12)
    )
    text.pack(fill="both", expand=True)

    # ---------- DEFINE FONTS & TAGS ----------
    bold_font = font.Font(text, text.cget("font"))
    bold_font.configure(weight="bold")

    text.tag_configure("bold", font=bold_font)
    text.tag_configure("overall_pass", foreground="green", font=bold_font)
    text.tag_configure("overall_fail", foreground="red", font=bold_font)

    # ---------- BUTTON ----------
    btn_frame = tk.Frame(root)
    btn_frame.pack(fill="x", pady=10)

    tk.Button(
        btn_frame,
        text="OK",
        font=("Arial", 16, "bold"),
        command=root.destroy
    ).pack()

    # ---------- HANDLE dict OR list ----------
    records = results.values() if isinstance(results, dict) else results

    for r in records:
        # Section header
        text.insert(
            tk.END,
            f"\n{'=' * 20} {r['com_port']} {'=' * 20}\n",
            "bold"
        )
        if mct_applicable:
            # MCT (all tool types) and IMG Provisioning (img tool types
            # only) each get their own pass/fail (+ reason on fail) row,
            # instead of being folded into ftt_reason. RTT is intentionally
            # not shown here -- it isn't actually being checked in this
            # flow, so surfacing a status for it is misleading.
            mct = r.get("mct", "fail").upper()
            ftt = r["ftt"].upper()
            overall = r["overall"].upper()

            # MCT
            text.insert(tk.END, "MCT          : ")
            text.insert(tk.END, f"{mct}\n")
            if mct == "FAIL":
                text.insert(tk.END, f"MCT Reason   : {r.get('mct_reason', '')}\n")

            # FTT
            text.insert(tk.END, "FTT          : ")
            text.insert(tk.END, f"{ftt}\n")
            if ftt == "FAIL":
                text.insert(tk.END, f"FTT Reason   : {r.get('ftt_reason', '')}\n")

            # IMG Provisioning
            if 'img' in tool_type.lower():
                provisioning = r.get("provisioning", "fail").upper()
                text.insert(tk.END, "Provisioning : ")
                text.insert(tk.END, f"{provisioning}\n")
                if provisioning == "FAIL":
                    text.insert(tk.END, f"Provisioning Reason: {r.get('PROVISIONING_FAIL_REASON', '')}\n")
        else:
            ftt = r["ftt"].upper()
            overall = r["overall"].upper()

            text.insert(tk.END, "FTT          : ")
            text.insert(tk.END, f"{ftt}\n")
            if ftt == "FAIL":
                text.insert(tk.END, f"FTT Reason   : {r.get('ftt_reason', '')}\n")

        # Overall (colored)
        text.insert(tk.END, "Overall      : ", "bold")
        if overall.lower() == "pass":
            text.insert(tk.END, f"{overall}\n", "overall_pass")
        else:
            text.insert(tk.END, f"{overall}\n", "overall_fail")

    text.config(state="disabled")
    root.mainloop()

# ---------------- UTIL ----------------
def load_json_with_comments(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(r'//.*', '', content)
    content = re.sub(r'#.*', '', content)
    return json.loads(content)

# ---------------- FTT ----------------
def run_ftt_sequential(temp_com_port_list, serial_cfg, cpu_serial_num, results):
    # FLOW CHANGE: no more `results` (rtt_results) argument passed into
    # ftt_merger_tool.run() -- MCT is now checked inside FTT itself, using
    # the PCB serial number FTT reads via its own command-based call, so
    # there's nothing to hand it in advance any more. run() now returns
    # 'rtt'/'rtt_reason' (mirroring 'mct'/'mct_reason') per port in ftt_res,
    # computed from whether that port's inline MCT check (for 'img'/'4g'/'rf'
    # tool types) passed.
    ftt_res = ftt_merger_tool.run(serial_cfg, temp_com_port_list, cpu_serial_num)
    logging.info(f"FTT Result: {ftt_res}")
    for com in temp_com_port_list:
        com_po = "com" + str(com)
        results[com_po]["ftt"] = ftt_res.get(com_po, "").get("result", "fail")
        results[com_po]['ftt_reason'] = ftt_res.get(com_po, "").get("reason", "")
        results[com_po]["rtt"] = ftt_res.get(com_po, "").get("rtt", "fail")
        results[com_po]['rtt_reason'] = ftt_res.get(com_po, "").get("rtt_reason", "")
        # 'mct'/'provisioning' are new -- surfaced as their own pass/fail
        # rows in the summary popup instead of being folded into ftt_reason.
        results[com_po]["mct"] = ftt_res.get(com_po, "").get("mct", "fail")
        results[com_po]['mct_reason'] = ftt_res.get(com_po, "").get("mct_reason", "")
        results[com_po]["provisioning"] = ftt_res.get(com_po, "").get("provisioning", "fail")
        results[com_po]['PROVISIONING_FAIL_REASON'] = ftt_res.get(com_po, "").get("PROVISIONING_FAIL_REASON", "")
        # results[com_po]["ftt"] = "pass"
        # results[com_po]['ftt_reason'] = ""
    return results

def run_main(serial_config, temp_serial_config, cpu_serial_num):
    # serial_config = load_json_with_comments("serial_config.json")
    com_port_list = temp_serial_config.get("port_list", [])
    results = {}
    tool_type = serial_config.get("TOOL_TYPE", "rf_ftt").lower()
    is_img = 'img' in tool_type
    mct_applicable = any(t in tool_type for t in ('img', '4g', 'rf'))
    if not com_port_list:
        if mct_applicable:
            show_summary_all([{"com_port": "COM Port is not selected","rtt": "fail",'rtt_reason':"", "mct": "fail", "mct_reason": "", "ftt": "fail","ftt_reason": "", "provisioning": "fail" if is_img else "pass", "PROVISIONING_FAIL_REASON": "","overall": "fail"}], tool_type)
        else:
            show_summary_all([{"com_port": "COM Port is not selected", "rtt": "pass",'rtt_reason':"", "ftt": "fail","ftt_reason": "","overall": "fail"}], tool_type)

    else:
        if mct_applicable:
            for com_port in com_port_list:
                com_po = "com" + str(com_port)
                results[com_po] = {}
                results[com_po] = {
                    "com_port": com_po,
                    "rtt": "fail",
                    'rtt_reason': "",
                    "mct": "fail",
                    "mct_reason": "",
                    "ftt": "fail",
                    "ftt_reason": "",
                    "provisioning": "fail" if is_img else "pass",
                    "PROVISIONING_FAIL_REASON": "",
                    "overall": "fail"
                    }
        else:
            for com_port in com_port_list:
                com_po = "com" + str(com_port)
                results[com_po] = {}
                results[com_po] = {
                    "com_port": com_po,
                    "rtt": "pass",
                    'rtt_reason': "",
                    "ftt": "fail",
                    "ftt_reason": "",
                    "overall": "fail"
                    }

        # print(results)
        # FLOW CHANGE: the old STAGE 1 (run_parallel_test: raw-byte PCB read
        # -> MCT -> RTT, all before FTT was allowed to start) is gone. MCT is
        # now checked inline inside FTT itself (ftt_merger_tool.main_function,
        # 'img'/'4g'/'rf' tool types), reusing the PCB serial number FTT
        # already reads via its own command -- no separate hardware read.
        logging.info(f"Starting FTT test...")
        # IMG Provisioning now runs INLINE inside FTT itself
        # (ftt_merger_tool.main_function's img_provisioning branch, gated on
        # all earlier FTT steps having passed) instead of as a separate
        # stage here. So results[com_po]["ftt"]/["ftt_reason"] already
        # reflect a provisioning failure for 'img' tool types -- there is no
        # more standalone provisioning stage/result to run or track in this
        # file (run_provision_sequential and the provisioning_tool.img_ftt
        # import have both been removed).
        results = run_ftt_sequential(com_port_list, serial_config, cpu_serial_num, results)

        # STAGE 2 (final overall pass/fail)
        logging.info(f"COM Port wise result: {results}")
        if mct_applicable:
            for com_port in com_port_list:
                com_po = "com" + str(com_port)
                results[com_po]["overall"] = (
                    "pass"
                    if results[com_po]["rtt"].lower() == "pass"
                    and results[com_po]["mct"].lower() == "pass"
                    and results[com_po]["ftt"].lower() == "pass"
                    else "fail"
                )
        else:
            for com_port in com_port_list:
                com_po = "com" + str(com_port)
                results[com_po]["overall"] = (
                    "pass"
                    if results[com_po]["ftt"].lower() == "pass"
                    else "fail"
                )

        show_summary_all(list(results.values()), tool_type)


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
        logging.error(f"Error in getting bios serial number: {str(e)}")
        return "1111111111"

# ---------------- MAIN ----------------
if __name__ == "__main__":
    freeze_support() 
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
        if serial_config_status:
            print(Fore.GREEN + "Configuration Parameters is Loaded...")
            print(Fore.GREEN + Style.RESET_ALL)
            cpu_serial_num = get_bios_serial()
            print(serial_config)
            logging.info(f"CPU Serial Number: {cpu_serial_num}")
            while True:
                print ("<<<<<<<<<<<<<<<<<<<<<<<<<<<<............... 1-Ph FTT(FTT + Provisioning) Tool V 1.38.....................>>>>>>>>>>>>>>>>>>>")
                logging.info ("<<<<<<<<<<<<<<<<<<<<<<<<<<<<............... 1-Ph FTT(FTT + Provisioning) Tool V 1.38.....................>>>>>>>>>>>>>>>>>>>")
                input("Press Enter to Start the Tool.......")
                logging.info("\n-----------Start new batch--------------")
                try:
                    run_main(serial_config, port_json, cpu_serial_num)
                except Exception as e:
                    # Without this, any error in a batch closed the exe window
                    # with no popup and no trace of what went wrong.
                    logging.exception(f"Unhandled error in batch: {e}")
                    print(Fore.RED + f"Unhandled error in batch: {e}")
                    traceback.print_exc()
        else:
            print(Fore.RED + "Fixed Serial config is currepted")
            time.sleep(2)
    print("Closing FTT Tool..")
    time.sleep(3)