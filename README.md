# 1-Ph FTT (FTT + Provisioning) Tool

Windows tool that runs the Final Test (FTT) on one or more 1-phase meters over serial/IrDA (one COM port per meter, one thread per port). Depending on `TOOL_TYPE` it also checks the MCT result and provisions the NIC / IMG gateway. Results go to an Excel log and, in the `4g`/`rf` flows, to PostgreSQL.

## Folder layout

| Path | Purpose |
|---|---|
| `img_ftt_provisioning.py` | Entry point. Loads config, shows the run loop and the summary popup. |
| `ftt_merger_tool.py` | Core logic: per-port test sequence (`main_function`), operator input and batch handling (`run`), Excel logging, IMG/RF provisioning hooks. |
| `Test_cases_verificationClass.py` | `TestCasePCTMCT`: one method per meter command (serial no, calibration, relay, GPRS, push settings, etc.). Each retries up to `RETRIES` times and returns pass/fail. |
| `config.py` | `Config`: reads `config.json`, decrypts and checksum-validates `config_file.enc`. |
| `config.json` | Port list, e.g. `{"port_list": [189]}`. |
| `config_file.enc` | Encrypted fixed configuration (tool type, project, versions, etc.). |
| `db_connect.py` | PostgreSQL helpers: MCT lookup by PCB serial (Athena DB) and result upload (EMS DB). |
| `provisioning_tool/` | IMG (Wirepas gateway) provisioning, logging, AWS upload. |
| `fg23_prov/` | RF NIC provisioning. Has its own `requirements.txt` and `README.md`. |


`gp_node` is an internal package and is not on PyPI. Install it from your internal source before running.

## Configuration

Two files are loaded at startup (`img_ftt_provisioning.py`). If either is missing or invalid the tool does not start a batch.

### `config.json` (plain JSON, per-station)

```json
{ "port_list": [189] }
```

| Key | Description |
|---|---|
| `port_list` | COM port numbers tested in one batch. Port `189` means `COM189`. The operator is asked to scan the matching `com189` for each entry. An empty list shows "COM Port is not selected". |

### `config_file.enc` (encrypted, fixed per product/project)

An encrypted file (Fernet, key derived with PBKDF2 from a password in `config.py`). It decrypts to `{"encrypted_data": ..., "checksum": ...}`; the inner data is decrypted again and its SHA-256 checksum is verified. A tampered or wrong file is rejected, and `TOOL_TYPE` must contain `ftt`. The decrypted JSON holds the keys below. Defaults are what the code uses when a key is absent.

**General**

| Key | Default | Description |
|---|---|---|
| `TOOL_TYPE` | `FTT` | Selects the flow. Containing `img`, `4g` or `rf` enables the MCT check; `img` adds IMG provisioning, `rf` (with `rf_prov`) adds RF provisioning, `4g` adds SIM and push-address steps. Also used in the log file name. |
| `PROJECT` | `wb` | Customer project: `gomati`, `saryu`, `manipur`, `wb`, `tn`, `tata_delhi`, `others`. Sets the meter serial number format entered by the operator and some calibration ranges. |
| `METER_TYPE` | `Garud_1PH` | Meter model (`garud_1ph`, or a name containing `better`). Selects calibration ranges and DB table. |
| `FTT_TEST_STATION` | empty | Station name used in the Excel file name. |
| `RETRIES` | 4 | Retries per meter command in `TestCasePCTMCT`. |
| `thread_time_delay` | 1 | Seconds between starting each port's thread. |
| `FTT_THREAD_TIMEOUT` | 300 | Seconds to wait for each port's thread before giving up. |

**Operator input validation**

| Key | Default | Description |
|---|---|---|
| `Main_PCB_SFG_Prefix` | `0000001` | Characters 10-16 of a valid meter PCB serial (alternative to the `R161` prefix). |
| `NIC_PCB_SFG_PREFIX` | `0000004` | Same for the NIC PCB serial (alternative to `R154`). |
| `NIC_PCB_LENGTH` | 27 | Length of the NIC PCB serial read from the meter. |

**Expected meter values**

| Key | Default | Description |
|---|---|---|
| `LIVE_VERSION` | 0 | Expected live firmware version; compared in the final Live version status step. |
| `INTERNAL_VERSION` | 0 | Expected internal version. `0` means any version is accepted. |
| `DLMS_TYPE` | `old_dlms` | DLMS activation check type. |
| `MANUFACTURING_NAME_SET` | 1 | `1` runs the Set/Get Manufacturing Name steps, `0` skips them. |
| `MANUFACTURING_NAME` | 1 | Manufacturing name value written to and read back from the meter. |
| `Bench_StabT_VolI` | 0 | Seconds to wait for the bench to stabilise before the voltage influence test. |
| `Voltage_Influence_minV` / `Voltage_Influence_maxV` | 0.0 | Allowed voltage range for the voltage influence test. |

**Provisioning**

| Key | Default | Description |
|---|---|---|
| `rf_prov` | 1 | For `rf` tools, `1` runs RF NIC provisioning and adds its log columns. |
| `BROKER` | empty | For `img` tools, selects MQTT broker, user and NTP host (`GOMATI`, `SARYU`, `MANIPUR`, `WB`, `TN`, `TATA_DELHI`). Also checked against the provisioned MQTT username. |
| `GATEWAY_TEXT_PREFIX` | `IMG` | Prefix of the gateway ID (prefix + IMG ID). |
| `NETWORK_CHANNEL` | `1` | Wirepas network channel used for IMG provisioning. |
| `REBOOT_TIME_SEC` | `300` | Reboot time passed to IMG provisioning. |
| `baudrate` | empty | Serial baud rate for IMG provisioning. |
| `GW_CORE_VER`, `GW_MAIN_VER`, `GW_SINK_APP_VER`, `GW_MODEM_FIRMWARE_VER`, `GW_METER_LIB_VER` | none (required for `img`) | Expected gateway versions; each is compared with the value read back after provisioning. |

**Data handling**

| Key | Default | Description |
|---|---|---|
| `MCT_PREVIOUS` | 15 | Only referenced in commented-out code; no effect now. |
| `IS_DATA_CONN` | 1 | `1` uploads results to the database. |
| `IS_OFFLINE` | 1 | Controls the offline handling paths around the upload; check `ftt_merger_tool.py` (around lines 2639-2870) before changing. |

The key list comes from reading the code, not the actual `.enc` contents, so the real file may hold extra keys. To view or edit it, decrypt with `Config().decrypt_json('config_file.enc')`, then decrypt `encrypted_data` with `Config().decrypt_data(data, 'FTT1P')`.

### Other settings

- Database credentials are currently hardcoded in `db_connect.py`. Move them to environment variables or the encrypted config before sharing the code.

## Run

```
python img_ftt_provisioning.py
```

Output: `<Meter_type>_<TOOL_TYPE>_<station>_LOG.xlsx` (one row per meter) and the log files from `setup_logger`.

## Test case flow

### Batch flow (operator + tool)

1. Tool starts, loads `config.json`, then decrypts and validates `config_file.enc`. On failure it stops with an error.
2. Reads the BIOS serial number (PowerShell) as the station ID.
3. Operator presses Enter to start a batch.
4. For each configured COM port, the operator enters:
   - the COM port (must match the expected position, e.g. `com189`)
   - the meter serial number (format depends on `PROJECT`, e.g. `PPL1234567` for WB, `PO12345678` for Gomati/Saryu/TN, `MN1P232345` for Manipur)
   - the meter PCB serial number (`R161...` or SFG prefix match)
   - the NIC PCB serial number (`R154...` or SFG prefix match)
5. Operator presses Enter again; one thread per port starts `main_function`, staggered by `thread_time_delay`.
6. Threads are joined (timeout `FTT_THREAD_TIMEOUT`, default 300 s).
7. Meter serial numbers are re-entered/re-scanned to confirm the printed number matches the one inside the meter (`Verify_Serial_No_Mismatch`).
8. Results are written to Excel (and uploaded to the DB), then the summary popup shows MCT / FTT / Provisioning / Overall per COM port.
9. Loop returns to step 3.

### Per-meter test sequence (`main_function`)

Each step retries up to 3 times. A step records `pass`/`fail` plus a `_Retry_Count` column. Any step that never ran is logged as `fail`.

| # | Step | Pass condition |
|---|---|---|
| 1 | Open COM port, get live version | Port answers; live version recorded. Otherwise the port is reported unreachable. |
| 2 | Get meter PCB serial number | Equals the PCB serial the operator entered. |
| 3 | MCT check (`img`, `4g`, `rf` only) | Latest MCT row for that PCB serial in the Athena DB has `overall_result = pass`. On fail, the port is aborted (no FTT log row). |
| 4 | Verify serial number (duplicate check) | Meter does not still hold a default serial (`98765432` / `987654` or an `R161`/`R154` PCB-style value). |
| 5 | Calibration unlock | EEPROM unlock writes return `ok`. |
| 6 | Set meter serial number | Command returns `ok`. |
| 7 | Get serial number after set | Matches the number entered. |
| 8 | Calibration lock | EEPROM lock write returns `ok`. |
| 9 | Check calibration lock status | Status is `sw calib locked, hw locked`. |
| 10 | Verify meter address | Address read matches the address derived from the serial number. |
| 11 | Verify DLMS activation | DLMS activation check returns 0 (type from `DLMS_TYPE`). |
| 12 | Verify clear energy | Active, apparent and reactive import energy all equal 0. |
| 13 | Get NIC PCB number | Prefix `R154`/`R144`, or SFG prefix matches. |
| 14 | Get internal version | A version string is returned. |
| 15 | Verify meter calibration | Read the 1-phase calibration coefficients; each must be inside the range for the meter type and project (`better`, `wb`/`tn`, or default). |
| 16 | Set GPRS protocol | Command returns `ok`. |
| 17 | Get GPRS protocol | Value equals `0xAC14` (TCP). |
| 18 | Voltage influence test | Voltage reading is within range. |
| 19 | Set / get manufacturing name | Run only if `MANUFACTURING_NAME_SET` is on. Value is set and read back. |
| 20 | Provisioning, by tool type | **RF** (`rf_prov = 1`): set tunnel mode, provision NIC, read back channel. **IMG**: set debug print mode, provision the IMG gateway, then check `GW_CORE/MAIN/SINK_APP/MODEM_FIRMWARE/METER_LIB` versions, broker username and both SIM ICCIDs. IMG provisioning runs only if all earlier steps passed. |
| 21 | 4G only | Check GPRS connection (SIM active, signal > 20), set/get periodic push IPv6, push interval, and event push IPv6. |
| 22 | Factory reset | Command returns `ok`. |
| 23 | Live version status | Live version matches the expected version. |

Overall result per port: `pass` only if MCT (when applicable) and FTT both pass; for `img`, provisioning must also pass.

### Result and failure handling

- Failure text is built per step from named keys, e.g. `Fail in Calib Lock`. Provisioning failures show in their own row in the popup, not duplicated under FTT.
- Aborted ports (COM unreachable, PCB serial unreadable, MCT fail) show a message and no Excel row.
- Known quirks kept from the original script: the re-read serial check writes `'Fail'` (capital F) so it is never counted as a failure, and the failure message prints as `COM Port <message>: <com_port>` (arguments swapped).

## Troubleshooting

- `com port is unreachable`: check cable/IrDA head and that the COM number matches `config.json`.
- `Wrong Encrypted Serial Config file Selected` / `Fixed Serial config is currepted`: the `.enc` file is wrong, tampered with, or `TOOL_TYPE` lacks `ftt`.
- `Database connection not available`: the EMS/Athena Postgres hosts must be reachable from this PC.
