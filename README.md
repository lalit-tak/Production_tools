# 1-Phase PCT (PCB Customisation Tool) – Multiport

Windows command-line tool that provisions and tests **1-phase smart meters (Garud / Better)** on several COM ports in parallel. For each meter it runs a fixed sequence of customisation and verification steps over the optical/IrDA port, optionally provisions the RF NIC to **Wirepas channel 9**, logs everything to Excel, and (optionally) uploads the log to a database and S3.

Current version: **2.22** (includes Tata Power Better-meter changes in *Verify Current*).

---

## Features

- One worker thread per COM port (multi-position fixture).
- Each step retries up to 3 times; the retry count is logged.
- Dictionary-based results: every value is written to the Excel column matching its header name, so columns never shift.
- Garud and Better meter variants (different bootloader and hardware-version steps).
- Optional RF NIC provisioning (tunnel mode, then channel 9) through `fg23_prov`.
- PCB serial re-entry check to catch label/meter mismatches.
- Excel log, optional PostgreSQL upload and S3 upload, rotating log file, and a colour-coded result summary popup.

## Repository layout

| File | Purpose |
|---|---|
| `pct_multiport.py` | Main entry point: input prompts, per-port test flow, logging, upload, result summary |
| `Test_cases_verificationClass.py` | `TestCasePCTMCT` class: the individual meter commands (reset, relay, current, versions, and so on) |
| `config.py` | Loads `config.json` and decrypts and validates `config_file.enc` |
| `config.json` | Fixture COM port numbers, e.g. `{"com_port": [157]}` |
| `config_file.enc` | Encrypted, checksummed test configuration (see below) |
| `db_connect.py` | PostgreSQL upload of the result DataFrame |
| `fg23_prov/` | NIC / Wirepas provisioning scripts (see `fg23_prov/README.md`) |

## Requirements

- Windows (uses `pywin32`, `ipconfig`, PowerShell) and Python 3.12 or newer (f-strings with nested quotes are used).
- The Polaris `gp_node` package (`gp_node.network.network_api`) must be importable.
- Python packages:

```bash
pip install pyserial openpyxl pandas colorama easygui pywin32 cryptography psycopg2-binary boto3
pip install -r fg23_prov/requirements.txt
```

## Configuration

### `config.json`: COM ports

```json
{ "com_port": [157, 158, 159, 160] }
```

Each number is a fixture position. Position *n* must be scanned with the matching `COM<number>`.

### `config_file.enc`: test parameters

An encrypted JSON that must contain `encrypted_data` and a matching `checksum`. After decryption it holds keys such as:

| Key | Meaning |
|---|---|
| `TOOL_TYPE` | Must contain `pct` (e.g. `rf_pct`) |
| `METER_TYPE` | `Garud_1PH` or `Better_...` |
| `LIVE_VERSION`, `INTERNAL_VERSION` | Expected firmware versions (`INTERNAL_VERSION = 0` skips the check) |
| `BOOTLOADER_VERSION`, `BOOTLOADER_VERSION_2` | Expected bootloader versions (the second is for Better meters) |
| `I_PHASE_MIN`, `I_PHASE_MAX`, `RETRIES` | Current limits with relay on |
| `CURRENT_RATING`, `MANUFACTURING_YEAR`, `PAYMENT_MODE` | Values to program |
| `Set_gprs_protocol` | GPRS protocol value |
| `IS_RF_CHANNEL_PROVISION` | `1` enables RF provisioning |
| `RF_CHANNEL` | Wirepas channel (default 9) |
| `Main_PCB_SFG_Prefix`, `NIC_PCB_SFG_PREFIX` | Accepted PCB serial prefixes |
| `IS_DATA_CONN` | `1` uploads to the DB and S3; `0` uploads to S3 only |
| `Factory_Reset`, `CURRENT_RATING_SET`, `MANUFACTURING_YEAR_SET`, `PAYMENT_MODE_SET`, `Set_Hardware_version`, `verify_battery_volt` | Set to `False` to skip that step |
| `Fact_Reset_sleepTime`, `thread_time_delay` | Delays in seconds |

### Credentials

Set the placeholders before running. **Never commit real credentials.**

- `pct_multiport.py`: `ACCESS_KEY`, `SECRET_KEY`, `bucket_name`, `folder_name`
- `db_connect.py`: `DB_CONFIG`, `TABLE_SCHEMA`, `PENDING_FILE`
- `config.py`: the password used to decrypt `config_file.enc`. Move it to an environment variable or a secret store before publishing the repo.

## Usage

```bash
python pct_multiport.py
```

The tool loops forever. Each pass handles one batch of meters on the fixture. Close the console window to exit.

---

## Test flow

### Operator flow

1. **Startup:** load `config.json`, then decrypt and validate `config_file.enc`. If either fails, the tool prints an error and exits.
2. **Scan each position (for every COM port in `config.json`):**
   1. Enter the COM port (it must equal `COM<n>` for that position).
   2. Enter the Meter PCB serial number. It must start with `R161`, or have the configured prefix at characters 9–16. It must be longer than 12 characters and end in 8 digits; the last 8 digits become the meter serial number.
   3. Enter the NIC PCB serial number. It must start with `R154` or `R144`, or have the configured NIC prefix.
3. Press **Enter** to start. One thread per port is launched, staggered by `thread_time_delay`.
4. All threads finish, then the operator **re-enters each Meter PCB serial number** (PCB verification).
5. Results are written to Excel, uploaded (if enabled), and a summary popup is shown.

### Per-meter test sequence (`main_function`)

```text
Open COM port (9600 baud, IrDA, port ID 4)
        │
        ▼
Check COM port reachable  ──fail──► "com port is unreachable" (port reported, abort flag set)
        │
        ▼
 1. Factory Reset                    (skippable)
 2. Calibration Unlock
 3. Set Meter Serial Number          (last 8 digits of PCB serial)
 4. Set Meter PCB Serial Number
 5. Set NIC PCB Number
 6. Verify Live Version              (compare with LIVE_VERSION)
 7. Verify Internal Version          (skipped when INTERNAL_VERSION = 0)
 8. Set Relay Mode
 9. Verify Current – Relay ON        (I_PHASE_MIN..I_PHASE_MAX, extra retries with 3 s delay)
10. Relay OFF
11. Set Time
12. Verify Bootloader Version        Garud: 1 check │ Better: 1st and 2nd checks
13. Set Current Rating               (skippable)
14. Set Manufacturing Year           (skippable)
15. Set Payment Mode                 (skippable)
16. Set Hardware Version             (Garud only, skippable)
17. Verify Battery Voltage           (skippable)
    wait 2 s for the current to settle
18. Verify Current – Relay OFF       (expects 0 A)
19. Relay ON
20. Set GPRS Protocol
21. Get / Verify GPRS Protocol
    wait 2 s
22. RF provisioning (only if TOOL_TYPE=rf_pct and IS_RF_CHANNEL_PROVISION=1):
      a. Open Tunnel Mode (3 attempts, sends end bytes between failures)
      b. Provision NIC to channel 9 (30 s timeout)
      c. Send end bytes to close tunnel mode
        │
        ▼
Close port ─► fill any untested step as "fail" ─► store result for this COM port
```

- Every step is tried up to **3 times**. The attempt count is stored as `<Step>_Retry_Count`.
- A step that never ran is recorded as **fail**. An untested step never looks like a pass.
- A step that is skipped by config is recorded as `pass` with a retry count of `0`.

### After all ports finish

1. **PCB serial re-entry check:** the re-entered Meter PCB serial must equal the serial stored in the meter. A match gives `Meter PCB Serial Numebr Check = pass`. A mismatch gives `fail`.
2. **Overall Result:** `pass` only if no step in the result is `fail` (including the PCB check). Otherwise `fail`.
3. **Excel log:** one row per meter is appended to `<MeterType>_<TOOL>_LOG.xlsx`, sheet `<TOOL>_DATA_LOG`. Columns are matched by header name, and the file is created with headers if missing.
4. **Upload:**
   - `IS_DATA_CONN = 1`: upload the DataFrame to PostgreSQL (`better`/`garud` × `rf`/`4g`). If that succeeds, upload the `.xlsx` to S3 and delete the local copy.
   - `IS_DATA_CONN = 0`: upload to S3 only.
5. **Summary popup and console report:** totals for Total / Passed / Failures / Unreachable, with per-port messages and elapsed time.

### Result values

| Outcome | Meaning |
|---|---|
| `PASS: COM<n>` | All steps and the PCB check passed |
| `COM Port: <n>, Fail in <step>` | A specific step failed |
| `COM Port: <n>, Fail in PCB Serial No Mismatch ...` | Re-entered serial differs from the one in the meter |
| `com port is unreachable:<port>` | Port could not be opened or the meter did not respond |

## Logs

- `Logs/PCT.log`: rotates daily and keeps 7 days.
- `<MeterType>_<TOOL>_LOG.xlsx`: per-meter test report. This file is removed after a successful S3 upload.

## Notes

- The log header `Set Time Value` (the time written) is separate from the `Set Time` pass/fail column. Both are kept so they don't overwrite each other.
- `fg23_prov/` is based on the Wirepas NIC provisioning scripts. See `fg23_prov/README.md`.
