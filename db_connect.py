import datetime
import json
import logging
import os
import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json


DB_CONFIG = {
    "host": PUT_YOUR_HOST_HERE,
    "port": PUT_YOUR_PORT_HERE,
    "database": PUT_YOUR_DATABASE_HERE,
    "user": PUT_YOUR_USER_HERE,
    "password": PUT_YOUR_PASSWORD_HERE,
}
TABLE_SCHEMA = PUT_YOUR_TABLE_SCHEMA_HERE

PENDING_FILE = PUT_YOUR_PENDING_FILE_PATH_HERE

_conn = None

COLUMN_MAPPING_BETTER_RF = {
    "MAC_ADDR": "mac_addr",
    "Index": "index",
    "Date-time": "date_time",
    "Meter_SERIAL_NUM": "meter_serial_num_orig",
    "Meter PCB Serial No": "meter_pcb_serial_no",
    "Nic PCB No": "nic_pcb_no",
    "Live Version": "live_version",
    "Internal Version": "internal_version",
    "CurrentV_with_Relay_On": "currentv_with_relay_on",
    "CurrentN_with_Relay_On": "currentn_with_relay_on",
    "Live_Tamper_with_Relay_On": "live_tamper_with_relay_on",
    "Set Time Value": "set_time_value",
    "Bootloader Version_1st": "bootloader_version_1st",
    "Bootloader Version_2nd": "bootloader_version_2nd",
    "Current rating": "current_rating",
    "Manufacturing Year": "manufacturing_year",
    "Payment Mode": "payment_mode",
    "Battery Voltage": "battery_voltage",
    "CurrentV_with_Relay_Off": "currentv_with_relay_off",
    "CurrentN_with_Relay_Off": "currentn_with_relay_off",
    "Live_Tamper_with_Relay_Off": "live_tamper_with_relay_off",
    "GPRS_Protocol_Value": "gprs_protocol_value",
    "Set Provision Channel": "set_provision_channel",
    "Get Provision Channel": "get_provision_channel",
    "Overall Result": "overall_result",
    "Factory Reset": "factory_reset",
    "Factory Reset_Retry_Count": "factory_reset_retry_count",
    "Calibration Unlock": "calibration_unlock",
    "Calibration Unlock_Retry_Count": "calibration_unlock_retry_count",
    "Meter Serial Num": "meter_serial_num",
    "Meter Serial Num_Retry_Count": "meter_serial_num_retry_count",
    "Get Meter PCB No": "get_meter_pcb_no",
    "Get Meter PCB No_Retry_Count": "get_meter_pcb_no_retry_count",
    "Get Nic PCB No": "get_nic_pcb_no",
    "Get Nic PCB No_Retry_Count": "get_nic_pcb_no_retry_count",
    "live version": "live_version_result",
    "live version_Retry_Count": "live_version_result_retry_count",
    "Get Internal Version": "get_internal_version",
    "Get Internal Version_Retry_Count": "get_internal_version_retry_count",
    "Set Relay Mode": "set_relay_mode",
    "Set Relay Mode_Retry_Count": "set_relay_mode_retry_count",
    "Verify Current with Relay On": "verify_current_with_relay_on",
    "Verify Current with Relay On_Retry_Count": "verify_current_with_relay_on_retry_count",
    "Relay Off": "relay_off",
    "Relay Off_Retry_Count": "relay_off_retry_count",
    "Set Time": "set_time",
    "Set Time_Retry_Count": "set_time_retry_count",
    "Verify 1st Bootloader Version": "verify_1st_bootloader_version",
    "Verify 1st Bootloader Version_Retry_Count": "verify_1st_bootloader_version_retry_count",
    "Verify 2nd Bootloader Version": "verify_2nd_bootloader_version",
    "Verify 2nd Bootloader Version_Retry_Count": "verify_2nd_bootloader_version_retry_count",
    "Set Current Rating": "set_current_rating",
    "Set Current Rating_Retry_Count": "set_current_rating_retry_count",
    "Set Manufacturing Year": "set_manufacturing_year",
    "Set Manufacturing Year_Retry_Count": "set_manufacturing_year_retry_count",
    "Set Payment Mode": "set_payment_mode",
    "Set Payment Mode_Retry_Count": "set_payment_mode_retry_count",
    "Verify Battery Voltage": "verify_battery_voltage",
    "Verify Battery Voltage_Retry_Count": "verify_battery_voltage_retry_count",
    "Verify Current with Relay Off": "verify_current_with_relay_off",
    "Verify Current with Relay Off_Retry_Count": "verify_current_with_relay_off_retry_count",
    "Relay On": "relay_on",
    "Relay On_Retry_Count": "relay_on_retry_count",
    "Set GPRS Protocol": "set_gprs_protocol",
    "Set GPRS Protocol_Retry_Count": "set_gprs_protocol_retry_count",
    "Get GPRS Protocol": "get_gprs_protocol",
    "Get GPRS Protocol_Retry_Count": "get_gprs_protocol_retry_count",
    "Open Tunnel Mode": "open_tunnel_mode",
    "Open Tunnel Mode_Retry_Count": "open_tunnel_mode_retry_count",
    "Set Provisioning to ch_9": "set_provisioning_to_ch_9",
    "Set Provisioning to ch_9_Retry_Count": "set_provisioning_to_ch_9_retry_count",
    "Meter PCB Serial Numebr Check": "meter_pcb_serial_number_check"
}

COLUMN_MAPPING_GARUD_RF = {
    "MAC_ADDR": "mac_addr",
    "Index": "index",
    "Date-time": "date_time",
    "Meter_SERIAL_NUM": "meter_serial_num_orig",
    "Meter PCB Serial No": "meter_pcb_serial_no",
    "Nic PCB No": "nic_pcb_no",
    "Live Version": "live_version",
    "Internal Version": "internal_version",
    "CurrentV_with_Relay_On": "currentv_with_relay_on",
    "CurrentN_with_Relay_On": "currentn_with_relay_on",
    "Live_Tamper_with_Relay_On": "live_tamper_with_relay_on",
    "Set Time": "set_time",
    "Bootloader Version": "bootloader_version",
    "Current rating": "current_rating",
    "Manufacturing Year": "manufacturing_year",
    "Payment Mode": "payment_mode",
    "Hw Version": "hw_version",
    "Battery Voltage": "battery_voltage",
    "CurrentV_with_Relay_Off": "currentv_with_relay_off",
    "CurrentN_with_Relay_Off": "currentn_with_relay_off",
    "Live_Tamper_with_Relay_Off": "live_tamper_with_relay_off",
    "GPRS_Protocol_Value": "gprs_protocol_value",
    "Set Provision Channel": "set_provision_channel",
    "Get Provision Channel": "get_provision_channel",
    "Overall Result": "overall_result",
    "Factory Reset": "factory_reset",
    "Factory Reset_Retry_Count": "retry_count_1",
    "Calibration Unlock": "calibration_unlock",
    "Calibration Unlock_Retry_Count": "retry_count_2",
    "Meter Serial Num": "meter_serial_num",
    "Meter Serial Num_Retry_Count": "retry_count_3",
    "Get Meter PCB No": "get_meter_pcb_no",
    "Get Meter PCB No_Retry_Count": "retry_count_4",
    "Get Nic PCB No": "get_nic_pcb_no",
    "Get Nic PCB No_Retry_Count": "retry_count_5",
    "live version": "live_version_result",
    "live version_Retry_Count": "retry_count_6",
    "Get Internal Version": "get_internal_version",
    "Get Internal Version_Retry_Count": "retry_count_7",
    "Set Relay Mode": "set_relay_mode",
    "Set Relay Mode_Retry_Count": "retry_count_8",
    "Verify Current with Relay On": "verify_current_with_relay_on",
    "Verify Current with Relay On_Retry_Count": "retry_count_9",
    "Relay Off": "relay_off",
    "Relay Off_Retry_Count": "retry_count_10",
    "Set Time": "set_time",
    "Set Time_Retry_Count": "retry_count_11",
    "Verify Bootloader Version": "verify_bootloader_version",
    "Verify Bootloader Version_Retry_Count": "retry_count_12",
    "Set Current Rating": "set_current_rating",
    "Set Current Rating_Retry_Count": "retry_count_13",
    "Set Manufacturing Year": "set_manufacturing_year",
    "Set Manufacturing Year_Retry_Count": "retry_count_14",
    "Set Payment Mode": "set_payment_mode",
    "Set Payment Mode_Retry_Count": "retry_count_15",
    "Set Hw Version": "set_hw_version",
    "Set Hw Version_Retry_Count": "retry_count_16",
    "Verify Battery Voltage": "verify_battery_voltage",
    "Verify Battery Voltage_Retry_Count": "retry_count_17",
    "Verify Current with Relay Off": "verify_current_with_relay_off",
    "Verify Current with Relay Off_Retry_Count": "retry_count_18",
    "Relay On": "relay_on",
    "Relay On_Retry_Count": "retry_count_19",
    "Set GPRS Protocol": "set_gprs_protocol",
    "Set GPRS Protocol_Retry_Count": "retry_count_20",
    "Get GPRS Protocol": "get_gprs_protocol",
    "Get GPRS Protocol_Retry_Count": "retry_count_21",
    "Open Tunnel Mode": "open_tunnel_mode",
    "Open Tunnel Mode_Retry_Count": "retry_count_22",
    "Set Provisioning to ch_9": "set_provisioning_to_ch_9",
    "Set Provisioning to ch_9_Retry_Count": "retry_count_23",
    "Meter PCB Serial Numebr Check": "meter_pcb_serial_number_check",
}

COLUMN_MAPPING_BETTER = {
    "MAC_ADDR": "mac_addr",
    "Index": "index",
    "Date-time": "date_time",
    "Meter_SERIAL_NUM": "meter_serial_num_orig",
    "Meter PCB Serial No": "meter_pcb_serial_no",
    "Nic PCB No": "nic_pcb_no",
    "Live Version": "live_version",
    "Internal Version": "internal_version",
    "CurrentV_with_Relay_On": "currentv_with_relay_on",
    "CurrentN_with_Relay_On": "currentn_with_relay_on",
    "Live_Tamper_with_Relay_On": "live_tamper_with_relay_on",
    "Set Time Value": "set_time_value",
    "Bootloader Version_1st": "bootloader_version_1st",
    "Bootloader Version_2nd": "bootloader_version_2nd",
    "Current rating": "current_rating",
    "Manufacturing Year": "manufacturing_year",
    "Payment Mode": "payment_mode",
    "Battery Voltage": "battery_voltage",
    "CurrentV_with_Relay_Off": "currentv_with_relay_off",
    "CurrentN_with_Relay_Off": "currentn_with_relay_off",
    "Live_Tamper_with_Relay_Off": "live_tamper_with_relay_off",
    "GPRS_Protocol_Value": "gprs_protocol_value",
    "Overall Result": "overall_result",
    "Factory Reset": "factory_reset",
    "Factory Reset_Retry_Count": "factory_reset_retry_count",
    "Calibration Unlock": "calibration_unlock",
    "Calibration Unlock_Retry_Count": "calibration_unlock_retry_count",
    "Meter Serial Num": "meter_serial_num",
    "Meter Serial Num_Retry_Count": "meter_serial_num_retry_count",
    "Get Meter PCB No": "get_meter_pcb_no",
    "Get Meter PCB No_Retry_Count": "get_meter_pcb_no_retry_count",
    "Get Nic PCB No": "get_nic_pcb_no",
    "Get Nic PCB No_Retry_Count": "get_nic_pcb_no_retry_count",
    "live version": "live_version_result",
    "live version_Retry_Count": "live_version_result_retry_count",
    "Get Internal Version": "get_internal_version",
    "Get Internal Version_Retry_Count": "get_internal_version_retry_count",
    "Set Relay Mode": "set_relay_mode",
    "Set Relay Mode_Retry_Count": "set_relay_mode_retry_count",
    "Verify Current with Relay On": "verify_current_with_relay_on",
    "Verify Current with Relay On_Retry_Count": "verify_current_with_relay_on_retry_count",
    "Relay Off": "relay_off",
    "Relay Off_Retry_Count": "relay_off_retry_count",
    "Set Time": "set_time",
    "Set Time_Retry_Count": "set_time_retry_count",
    "Verify 1st Bootloader Version": "verify_1st_bootloader_version",
    "Verify 1st Bootloader Version_Retry_Count": "verify_1st_bootloader_version_retry_count",
    "Verify 2nd Bootloader Version": "verify_2nd_bootloader_version",
    "Verify 2nd Bootloader Version_Retry_Count": "verify_2nd_bootloader_version_retry_count",
    "Set Current Rating": "set_current_rating",
    "Set Current Rating_Retry_Count": "set_current_rating_retry_count",
    "Set Manufacturing Year": "set_manufacturing_year",
    "Set Manufacturing Year_Retry_Count": "set_manufacturing_year_retry_count",
    "Set Payment Mode": "set_payment_mode",
    "Set Payment Mode_Retry_Count": "set_payment_mode_retry_count",
    "Verify Battery Voltage": "verify_battery_voltage",
    "Verify Battery Voltage_Retry_Count": "verify_battery_voltage_retry_count",
    "Verify Current with Relay Off": "verify_current_with_relay_off",
    "Verify Current with Relay Off_Retry_Count": "verify_current_with_relay_off_retry_count",
    "Relay On": "relay_on",
    "Relay On_Retry_Count": "relay_on_retry_count",
    "Set GPRS Protocol": "set_gprs_protocol",
    "Set GPRS Protocol_Retry_Count": "set_gprs_protocol_retry_count",
    "Get GPRS Protocol": "get_gprs_protocol",
    "Get GPRS Protocol_Retry_Count": "get_gprs_protocol_retry_count",
    "Meter PCB Serial Numebr Check": "meter_pcb_serial_number_check"
}

COLUMN_MAPPING_GARUD = {
    "MAC_ADDR": "mac_addr",
    "Index": "index",
    "Date-time": "date_time",
    "Meter_SERIAL_NUM": "meter_serial_num_orig",
    "Meter PCB Serial No": "meter_pcb_serial_no",
    "Nic PCB No": "nic_pcb_no",
    "Live Version": "live_version",
    "Internal Version": "internal_version",
    "CurrentV_with_Relay_On": "currentv_with_relay_on",
    "CurrentN_with_Relay_On": "currentn_with_relay_on",
    "Live_Tamper_with_Relay_On": "live_tamper_with_relay_on",
    "Set Time": "set_time",
    "Bootloader Version": "bootloader_version",
    "Current rating": "current_rating",
    "Manufacturing Year": "manufacturing_year",
    "Payment Mode": "payment_mode",
    "Hw Version": "hw_version",
    "Battery Voltage": "battery_voltage",
    "CurrentV_with_Relay_Off": "currentv_with_relay_off",
    "CurrentN_with_Relay_Off": "currentn_with_relay_off",
    "Live_Tamper_with_Relay_Off": "live_tamper_with_relay_off",
    "GPRS_Protocol_Value": "gprs_protocol_value",
    "Overall Result": "overall_result",
    "Factory Reset": "factory_reset",
    "Factory Reset_Retry_Count": "retry_count_1",
    "Calibration Unlock": "calibration_unlock",
    "Calibration Unlock_Retry_Count": "retry_count_2",
    "Meter Serial Num": "meter_serial_num",
    "Meter Serial Num_Retry_Count": "retry_count_3",
    "Get Meter PCB No": "get_meter_pcb_no",
    "Get Meter PCB No_Retry_Count": "retry_count_4",
    "Get Nic PCB No": "get_nic_pcb_no",
    "Get Nic PCB No_Retry_Count": "retry_count_5",
    "live version": "live_version_result",
    "live version_Retry_Count": "retry_count_6",
    "Get Internal Version": "get_internal_version",
    "Get Internal Version_Retry_Count": "retry_count_7",
    "Set Relay Mode": "set_relay_mode",
    "Set Relay Mode_Retry_Count": "retry_count_8",
    "Verify Current with Relay On": "verify_current_with_relay_on",
    "Verify Current with Relay On_Retry_Count": "retry_count_9",
    "Relay Off": "relay_off",
    "Relay Off_Retry_Count": "retry_count_10",
    "Set Time": "set_time",
    "Set Time_Retry_Count": "retry_count_11",
    "Verify Bootloader Version": "verify_bootloader_version",
    "Verify Bootloader Version_Retry_Count": "retry_count_12",
    "Set Current Rating": "set_current_rating",
    "Set Current Rating_Retry_Count": "retry_count_13",
    "Set Manufacturing Year": "set_manufacturing_year",
    "Set Manufacturing Year_Retry_Count": "retry_count_14",
    "Set Payment Mode": "set_payment_mode",
    "Set Payment Mode_Retry_Count": "retry_count_15",
    "Set Hw Version": "set_hw_version",
    "Set Hw Version_Retry_Count": "retry_count_16",
    "Verify Battery Voltage": "verify_battery_voltage",
    "Verify Battery Voltage_Retry_Count": "retry_count_17",
    "Verify Current with Relay Off": "verify_current_with_relay_off",
    "Verify Current with Relay Off_Retry_Count": "retry_count_18",
    "Relay On": "relay_on",
    "Relay On_Retry_Count": "retry_count_19",
    "Set GPRS Protocol": "set_gprs_protocol",
    "Set GPRS Protocol_Retry_Count": "retry_count_20",
    "Get GPRS Protocol": "get_gprs_protocol",
    "Get GPRS Protocol_Retry_Count": "retry_count_21",
    "Meter PCB Serial Numebr Check": "meter_pcb_serial_number_check",
}

def start_connection():
    global _conn

    if _conn and not _conn.closed:
        return _conn

    try:
        _conn = psycopg2.connect(connect_timeout=5, **DB_CONFIG)
        _conn.autocommit = False
        logging.info("Database connection started")
        return _conn
    except Exception as exc:
        _conn = None
        logging.error("Database connection failed: %s", exc)
        return None

def close_connection():
    global _conn

    if _conn and not _conn.closed:
        try:
            _conn.close()
            logging.info("Database connection closed")
        except Exception as exc:
            logging.error("Error while closing database connection: %s", exc)
    _conn = None

def _get_connection():
    if _conn is None or _conn.closed:
        return start_connection()
    return _conn

def _build_payload(log):
    return {
        "mac_address": log[0] if len(log) > 0 else None,
        "meter_info": list(log[1]) if len(log) > 1 else [],
        "test_result": list(log[2]) if len(log) > 2 else [],
        "book_name": log[3] if len(log) > 3 else None,
        "file_name": log[4] if len(log) > 4 else None,
        "created_at": datetime.datetime.now().isoformat(),
    }

def _table_columns(cursor, table_name):
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """,
        (TABLE_SCHEMA, table_name),
    )
    return [row[0] for row in cursor.fetchall()]

def _insert_payload(cursor, payload):
    columns = _table_columns(cursor)
    payload_column = next(
        (
            column
            for column in ("payload", "data", "json_data", "result_json", "MCT_data")
            if column in columns
        ),
        None,
    )

    if payload_column:
        insert_columns = [payload_column]
        values = [Json(payload)]
    else:
        insert_columns = [column for column in payload.keys() if column in columns]
        values = [Json(payload[column]) if isinstance(payload[column], list) else payload[column] for column in insert_columns]

    if not insert_columns:
        raise RuntimeError(
            'No matching columns found in "{}"."{}" for MCT upload'.format(
                TABLE_SCHEMA, TABLE_NAME
            )
        )

    query = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({})").format(
        sql.Identifier(TABLE_SCHEMA),
        sql.Identifier(TABLE_NAME),
        sql.SQL(", ").join(map(sql.Identifier, insert_columns)),
        sql.SQL(", ").join(sql.Placeholder() * len(insert_columns)),
    )
    cursor.execute(query, values)

def upload_log(log):
    payload = _build_payload(log)
    conn = _get_connection()

    if conn is None:
        _queue_payload(payload)
        return False

    try:
        with conn.cursor() as cursor:
            _insert_payload(cursor, payload)
        conn.commit()
        logging.info("MCT row uploaded to database")
        return True
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        logging.error("MCT database upload failed, queued locally: %s", exc)
        _queue_payload(payload)
        return False

def upload_dataframe(df_frame, meter_type, module_type):
    if 'better' in meter_type:
        if  module_type == 'rf':
            mapping = COLUMN_MAPPING_BETTER_RF
        else:
            mapping = COLUMN_MAPPING_BETTER
        TABLE_NAME = "BETTER1P_PCT"
    else:
        if  module_type == 'rf':
            mapping = COLUMN_MAPPING_GARUD_RF
        else:
            mapping = COLUMN_MAPPING_GARUD
        TABLE_NAME = "GARUD1P_PCT"
    missing_cols = [col for col in mapping if col not in df_frame.columns]
    if missing_cols:
        error_msg = f"DataFrame is missing expected columns: {missing_cols}"
        logging.error(error_msg)
        return False, error_msg

    df_renamed = df_frame.rename(columns=mapping)
    df_renamed["date"] = datetime.date.today()

    conn = _get_connection()
    if conn is None:
        error_msg = "Database connection not available"
        logging.error(error_msg)
        return False, error_msg
    try:
        with conn.cursor() as cursor:
            db_columns = _table_columns(cursor, TABLE_NAME)
            db_columns_lower = {c.lower(): c for c in db_columns}  # map lower -> real name

            insert_columns = [col for col in mapping.values() if col in db_columns]

            if "date" in db_columns_lower and "date" not in insert_columns:
                insert_columns.append(db_columns_lower["date"])  # use real column name/casing

            if not insert_columns:
                error_msg = (
                    f'No matching mapped columns found in "{TABLE_SCHEMA}"."{TABLE_NAME}" '
                    f"for dataframe upload"
                )
                logging.error(error_msg)
                return False, error_msg

            query = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({})").format(
                sql.Identifier(TABLE_SCHEMA),
                sql.Identifier(TABLE_NAME),
                sql.SQL(", ").join(map(sql.Identifier, insert_columns)),
                sql.SQL(", ").join(sql.Placeholder() * len(insert_columns)),
            )

            for _, row in df_renamed.iterrows():
                values = [
                    Json(row[col]) if isinstance(row[col], (list, dict)) else row.get(col, None) if col != db_columns_lower.get("date") else row["date"]
                    for col in insert_columns
                ]
                cursor.execute(query, values)

        conn.commit()
        logging.info("Uploaded %d rows to %s.%s table", len(df_renamed), TABLE_SCHEMA, TABLE_NAME)
        return True, None

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        error_msg = str(exc)
        logging.error("Dataframe upload failed: %s", error_msg)
        return False, error_msg

def _queue_dataframe(df_frame, source_label):
    """Fallback: queue dataframe rows locally as JSON lines if DB upload fails."""
    try:
        with open(PENDING_FILE, "a", encoding="utf-8") as pending_file:
            for record in df_frame.to_dict(orient="records"):
                record["_source"] = source_label
                pending_file.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:
        logging.error("Failed to queue dataframe locally: %s", exc)

def _queue_payload(payload):
    with open(PENDING_FILE, "a", encoding="utf-8") as pending_file:
        pending_file.write(json.dumps(payload, default=str) + "\n")

def upload_pending():
    if not os.path.exists(PENDING_FILE):
        return 0

    conn = _get_connection()
    if conn is None:
        return 0

    uploaded_count = 0
    remaining = []

    with open(PENDING_FILE, "r", encoding="utf-8") as pending_file:
        for line in pending_file:
            line = line.strip()
            if not line:
                continue

            try:
                payload = json.loads(line)
                with conn.cursor() as cursor:
                    _insert_payload(cursor, payload)
                conn.commit()
                uploaded_count += 1
            except Exception as exc:
                try:
                    conn.rollback()
                except Exception:
                    pass
                logging.error("Pending MCT database upload still failed: %s", exc)
                remaining.append(line)

    if remaining:
        with open(PENDING_FILE, "w", encoding="utf-8") as pending_file:
            pending_file.write("\n".join(remaining) + "\n")
    else:
        os.remove(PENDING_FILE)

    if uploaded_count:
        logging.info("Uploaded %s pending MCT database rows", uploaded_count)
    return uploaded_count

def execute_query():
    conn = _get_connection()
    if conn is None:
        print("Database connection is not available")
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM "Prod"."MCT" LIMIT 10;')
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            # for i, row in enumerate(rows, 1):
            #     print(f"Row {i}: {row}")

    except psycopg2.Error as exc:
        print("Database error:", str(exc))
    except Exception as exc:
        print("Error:", str(exc))
