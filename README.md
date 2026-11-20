# 1P Node Shell – Test Bench UI

PyQt5 desktop application that drives the production test bench for 1-phase smart meters.
It tests many meters in parallel (one per COM port), shows live PASS/FAIL per port, writes
Excel logs/reports and uploads them to AWS S3.

## Folder layout

| Path | Purpose |
|---|---|
| `main.py` | Main window (PyQt5): toolbar buttons, per-port result table, timers, Excel report, S3 upload |
| `config.json` | Bench config: `com_ports`, `DLMS_DONGLE_PORTS`, `bench_number` |
| `config_file.enc` | Encrypted project/test configuration (loaded by `utility/config.py`) |
| `utility/` | `config.py` (config loading/decryption), `communication.py` (serial/HDLC), `ui_logger.py` (logging) |
| `scripts/Test_cases_verificationClass.py` | `TestCase` class – every single meter command used by the tests |
| `scripts/check_com/check_ports.py` | Check Ports test |
| `scripts/calibration/calib_multiport.py` | Phase + Neutral calibration |
| `scripts/mct/mct_multiport.py` | MCT test (No-load / Starting current) |
| `scripts/rtt/rtt.py` | RTT (RF) test for meters |
| `scripts/rtt/img_testing.py`, `gprs_testing.py`, `factory_mode.py`, `provisioning.py`, `wirepas_provisioning.py` | RTT-image / NIC gateway testing (flash, RF, SIM1/SIM2) |
| `scripts/dlms/` | `DLMS_ACTIVATION_TOOL_FOR_BENCH_V_1.21.exe` + its `config.json` |
| `*/db_connect.py` | PostgreSQL helpers for meter/project info |
| `assets/` | Logo and icons |

## Setup


* Install the internal `gp_node` package separately (not on PyPI).
* Edit `config.json` (COM ports, dongle ports, bench number).
* Fill in the S3 settings (`S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET_NAME`, `S3_FOLDER_NAME`) in `main.py`.

## Configuration files

The app uses three config files. All are read at startup.

### 1. `config.json` – bench / hardware settings (plain JSON, in the app folder)
Loaded by `main.py` (`load_config`). Edit per bench.

| Key | Meaning |
|---|---|
| `com_ports` | List of COM ports (e.g. `"COM7"`) that become the rows of the result table |
| `DLMS_DONGLE_PORTS` | Two dongle port numbers used by the DLMS tool, default `[3, 4]` |
| `bench_number` | Bench ID; used in the report file name `Test_Report_<bench>.xlsx` and as the S3 upload prefix |

```json
{
  "com_ports": ["COM7", "COM8", "COM9"],
  "DLMS_DONGLE_PORTS": [3, 4],
  "bench_number": "3"
}
```

### 2. `config_file.enc` – encrypted project / test configuration
Loaded by `load_data_config("config_file.enc")` → `utility/config.py` (`Config.check_encrypted_json`) and exposed
in the app as `DATA_CONFIG` / `data_config`. It must sit in the folder you launch `python main.py` from.

* **Format:** first 16 bytes = salt, rest = Fernet token (key via PBKDF2-HMAC-SHA256, 390000 iterations).
  The decrypted JSON holds `encrypted_data` (Fernet-encrypted payload) and a `checksum` (SHA-256 of the payload).
  If decryption or the checksum fails, the config is empty (`{}`) and the app logs an error – an edited or wrong file is rejected.
* **Passwords:** `Config.PASSWORD` and `Config.CHECKSUMPASS` in `utility/config.py` are placeholders
  (`PUT_ENC_PASSWORD`, `PUT_CHECKSUM_PASSWORD`) – set the real values to match how the file was generated.

Keys read from the decrypted config (found in the code):

| Key | Used for |
|---|---|
| `TOOL_TYPE` | Test mode shown in the header dropdown |
| `PROJECT` | Project (e.g. `gomati`, `saryu`, `manipur`, `wb`, `tn`, `tn_public`, `public`); selects the MQTT broker for RTT and the calibration coefficient ranges |
| `METER_TYPE` | Meter type (e.g. Garud, "better" meter, 4G) – picks the MCT worker variant and checks |
| `LIVE_VERSION`, `INTERNAL_VERSION` | Expected firmware versions (shown in header and verified by the tests) |
| `MAIN_PCB_SFG_PREFIX`, `NIC_PCB_SFG_PREFIX` | Expected prefixes of the main-PCB / NIC-PCB serial numbers |
| `NIC_PCB_LENGTH` | Expected NIC PCB serial length |
| `PAYMENT_MODE`, `PAYMENT_MODE_SET` | Payment mode to set (default 1) and whether to set it |
| `DLMS_TYPE` | `old_dlms` or `new_dlms`. With `new_dlms` the DLMS column, button and stats are removed from the UI |
| `IS_DATA_CONN` | Whether GPRS/data connection is checked |
| `DEBUG_LOG_ENABLE` | Enables debug-level logging (accepts true/false, 1/0, yes/no) |
| `Bench_stabT_StartingPhaseT` | Wait before phase calibration (s, default 30) |
| `Bench_stabT_StartingneutralCalib`, `StabT_phaseCalib`, `StabT_neutralCalib` | Stabilisation times for the calibration stages |
| `Bench_stabT_StartingC` | Wait before the starting-current / no-load measurement (s) |
| `Fact_Reset_sleepTime` | Wait after factory reset (s, default 10) |
| `RTT_TIME` | How long RTT listens for MQTT RF broadcasts |

Keys used by the NIC / gateway test (`gprs_testing.py`, `img_testing.py`):
`port_list`, `thread_delay`, `thread_timeout`, `gprs_test_retry`, `network_address`, `network_channel`,
`authentication_key`, `encryption_key`, `test_router_address`, `rf_rx_rssi_dbm`, `rf_tx_rssi_dbm`,
`sim1_apn/user/pwd/pin/puk`, `sim2_apn/user/pwd/pin/puk`.

### 3. `scripts/dlms/config.json` – DLMS exe settings (auto-generated)
Rewritten by the app before every DLMS run (`write_dlms_exe_config`) from the active ports and
`DLMS_DONGLE_PORTS`; do not edit by hand.

```json
{ "port_list1": [19], "port_list2": [1], "dongle1": 3, "dongle2": 4 }
```
`port_list1/2` are the COM port numbers (without the `COM` prefix) split over the two dongles.

### Hard-coded settings in code
* **S3:** `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET_NAME`, `S3_FOLDER_NAME` in `main.py` (and the per-test scripts) are placeholders – fill them in and keep real keys out of version control.
* **MQTT brokers** per project are defined in `get_mqtt_broker_config()` in `scripts/rtt/rtt.py`.
* **DLMS exe path** (`DLMS_EXE_PATH`) in `main.py`.

## Run

```bash
python main.py
```

## Overall UI flow

1. **New Batch** – clears table/timers; pick the mode and active ports.
2. Run the tests from the toolbar: Check Ports → Calibration → RTT → DLMS → MCT.
   While one runs its button turns purple and the others are disabled.
3. Each test runs one worker per COM port; results come back as `pass`/`fail` per port.
4. A row is PASS only when every test column is pass; the row is written to `Test_Report_<bench>.xlsx`.
5. When all tests finish, the report is uploaded to S3 and the batch timer stops.

Result columns: **Phase, Neutral, RTT, DLMS, MCT** (Calibration fills Phase + Neutral).

---

## Test-case flow (test by test)

General rule: steps run in order and most retry several times; if a mandatory step fails the
port is marked fail with a fail message and skipped for the remaining steps. Other ports
continue independently.

### 1. Check Ports (`check_ports.py`)
1. Open the serial port – fail → `unable to open port`.
2. `check_port` connectivity check (with retries) → `port_open`.
3. `Get_pcb_serial_num` – read and validate the PCBA serial number → `pcba_serial`.
4. Port PASS only if both checks pass; the serial number is shown in the table.

### 2. Calibration (`calib_multiport.py`) – two bench stages
The operator is prompted to set bench power (valid range 1199.4 – 1200.6) before each stage.
Phase and Neutral results are merged per meter by **PCB serial number** (the meter may move to a
different COM port on the second bench); `Overall_Result` is computed once from both.

**2a. Phase calibration** (`worker_function_phase` → *Phase* column)
1. Wait for bench stabilisation (`Bench_stabT_StartingPhaseT`, default 30 s).
2. Check COM port.
3. Get meter address (`Get_Meter_Address`).
4. Get PCB serial number (`Get_Meter_PCB_No`) – merge key.
5. PCT check.
6. Calibration unlock (`Calibration_Unlock`).
7. Set relay mode – on/off, event log (`Set_Relay_Mode`).
8. Start phase calibration (`Phase_calibration`).

**2b. Neutral calibration** (`worker_function_neutral_calib_coff` → *Neutral* column)
1. Check COM port.
2. Get PCB serial number (merge key).
3. Start neutral calibration.
4. Read the 1P calibration coefficients and check each against its allowed (low, high) range
   (depends on project / meter type) → `Get_1p_calib_cofficient`.

### 3. RTT – meter RF test (`rtt.py` → *RTT* column)
1. Check COM port.
2. Verify meter serial number (`Get_Meter_Serial_Num`).
3. Get PCB serial number (`Get_PCB_Serial_Num`).
4. Calibration check (`Calibration_Check`).
5. Get meter address (`Get_Meter_Address`).
6. Set GPRS host (`Set_GPRS_Host`) and GPRS credentials (`Set_GPRS_Cred`) from the MQTT broker config.
7. Meter reset (`Reset`).
8. **Listen to MQTT RF broadcasts** for the timeout window. A meter passes only if its address was
   actually heard (comms OK but not heard → "Meter Failed in RTT").
9. Results written to the RTT log Excel and uploaded to S3.

### 4. RTT image / NIC gateway test (`img_testing.py` + `gprs_testing.py`)
One process per port, plus an Excel-writer process and a result popup.
1. Read PCB serial number and run the calibration check ("Fail (Not Connected)" if unreachable).
2. Read NIC PCB serial number and enable debug print.
3. Enter factory mode (HDLC challenge/response, baud-rate switch) and read NIC version info.
4. External flash test.
5. RF test (RX/TX RSSI against acceptance criteria, using the Wirepas network parameters).
6. Cellular test on **SIM1**, then **SIM2** (retries per SIM; IMEI/IMSI recorded).
7. Overall PASS only if RF + SIM1 + SIM2 pass; image version is logged; result goes to Excel and S3.

### 5. DLMS activation (`DLMS_ACTIVATION_TOOL_FOR_BENCH_V_1.21.exe` → *DLMS* column)
1. `write_dlms_exe_config` writes the active ports and dongle ports to `scripts/dlms/config.json`.
2. The exe is launched as a subprocess (no CLI args) and its output is captured.
3. The last bracketed list in the output is parsed: `succesfully activated in com port: N` → pass;
   `Failed in DLMS Activation in COM Port: N`, or a port missing from the list → fail.

### 6. MCT test (`mct_multiport.py` → *MCT* column)
Common pre-checks for every variant:
1. Check COM port (live version).
2. Verify meter serial number (`Meter_Serial_Num`).
3. Get live version (`live_version`).
4. Get PCB serial number (`Get_Meter_PCB_No`).
5. RTT check (`RTT_Check`).

Then, depending on meter type, one of these workers runs:

**A. Standard worker (`worker_function1`)**
1. Get NIC PCB number
2. Get meter address
3. 1P calibration coefficient range check
4. Get internal version
5. Set time
6. Verify time
7. Calibration unlock
8. Clear energy
9. Set payment mode
10. Hardware version (not for "better" meters)
11. DLMS activation check
12. GPRS / SIM connection check (for GPRS meters)
13. **Starting current**: wait `Bench_stabT_StartingC`, read energy register, wait 60 s, read again and verify the change (`Verify_Starting_Current_Test`)
14. Factory reset, then wait `Fact_Reset_sleepTime`
15. Check number of events

**B. No-load worker (`worker_function2`, second bench stage)**
1. Check port
2. Get PCB serial (key to merge with worker A's entry)
3. Wait `Bench_stabT_StartingC`
4. Read energy register, wait 60 s, read again – energy must not advance (`Verify_No_Load_Test`)
5. Calibration unlock (`Calib_Unlock_No_Load`)
6. Clear energy (`Clear_Energy_No_Load`)

Merged with worker A by PCB serial, then `Overall_Result` is computed.

**C. 4G worker (`worker_function_4g`)**
Same as A steps 1–12 (no starting-current step), then factory reset → wait → check number of events.

After the run, results are written to the MCT log Excel and uploaded to S3.

---

## Outputs
* `logs/` – per-test Excel log books (RTT, MCT, Calibration, RTT-image) and application logs.
* `Test_Report_<bench>.xlsx` – overall per-bench report (one row per port, all test statuses).
* S3 upload of the report/logs after each cycle.

## Notes
* Windows only (`pywin32`, COM ports, `.exe` DLMS tool).
* Do not commit real AWS keys; `config_file.enc` holds the encrypted project settings.
