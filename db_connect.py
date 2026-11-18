import datetime
import json
import logging
import threading
import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json


DB_CONFIG = {
    "host": "PUT_YOUR_EMS_HOST_HERE",
    "port": "PUT_YOUR_EMS_PORT_HERE",
    "database": "PUT_YOUR_EMS_DATABASE_HERE",
    "user": "PUT_YOUR_EMS_USER_HERE",
    "password": "PUT_YOUR_EMS_PASSWORD_HERE",
}
TABLE_SCHEMA = "PUT_YOUR_EMS_SCHEMA_HERE"

DB_CONFIG_ATHENA = {
    "host": "PUT_YOUR_ATHENA_HOST_HERE",
    "port": "PUT_YOUR_ATHENA_PORT_HERE",
    "database": "PUT_YOUR_ATHENA_DATABASE_HERE",
    "user": "PUT_YOUR_ATHENA_USER_HERE",
    "password": "PUT_YOUR_ATHENA_PASSWORD_HERE",
}
TABLE_SCHEMA_ATHENA = "PUT_YOUR_ATHENA_SCHEMA_HERE"

_conn = None
_athena_con = None
# Guards _conn/_athena_con so concurrent per-COM-port threads can't each
# see "no connection yet" at the same time and all open their own
# psycopg2.connect() simultaneously. It is also held while using the shared
# connection, since psycopg2 connections aren't safe for concurrent use
# from multiple threads.
_conn_lock = threading.Lock()

COLUMN_MAPPING_IMG = {
    "Serial No": "serial_no",
    "Date_Time": "date_time",
    "PCB Serial No": "pcb_serial_no",
    "NIC PCB Serial No": "nic_pcb_serial_no",
    "Meter Serial No": "meter_serial_no",
    "PCB Serial No Test Status": "pcb_serial_no_test_status",
    "NIC PCB Serial No Test Status": "nic_pcb_serial_no_test_status",
    "Meter Serial No Test Status": "meter_serial_no_test_status",
    "Meter Live Version": "meter_live_version",
    "Meter Live Version Status": "meter_live_version_status",
    "Meter Internal Version": "meter_internal_version",
    "Meter Internal Version Status": "meter_internal_version_status",
    "IMG ID": "img_id",
    "Gateway ID": "gateway_id",
    "Set Debug Print Mode": "set_debug_print_mode",
    "WIREPAS_GW_ID": "wirepas_gw_id",
    "WIREPAS_NODE_ADDRESS": "wirepas_node_address",
    "WIREPAS_GW_KEY_ENC_KEY": "wirepas_gw_key_enc_key",
    "WIREPAS_MTR_AUTH_KEY": "wirepas_mtr_auth_key",
    "WIREPAS_MTR_ENC_KEY": "wirepas_mtr_enc_key",
    "WIREPAS_MTR_BAUD_RATE": "wirepas_mtr_baud_rate",
    "WIREPAS_MTR_DLMS_MODE": "wirepas_mtr_dlms_mode",
    "WIREPAS_NODE_ROLE": "wirepas_node_role",
    "WIREPAS_ENCRYPTION_KEY": "wirepas_encryption_key",
    "WIREPAS_AUTHENTICATION_KEY": "wirepas_authentication_key",
    "WIREPAS_NETWORK_ADDRESS": "wirepas_network_address",
    "WIREPAS_NETWORK_CHANNEL": "wirepas_network_channel",
    "WIREPAS_SINK_ADDRESS": "wirepas_sink_address",
    "WIREPAS_SIM_SELECTION": "wirepas_sim_selection",
    "WIREPAS_SIM1_PDP_TYPE": "wirepas_sim1_pdp_type",
    "WIREPAS_SIM1_BAND_LOCK": "wirepas_sim1_band_lock",
    "WIREPAS_SIM2_PDP_TYPE": "wirepas_sim2_pdp_type",
    "WIREPAS_SIM2_BAND_LOCK": "wirepas_sim2_band_lock",
    "WIREPAS_MQTT_HOSTNAME": "wirepas_mqtt_hostname",
    "WIREPAS_MQTT_PORT": "wirepas_mqtt_port",
    "WIREPAS_MQTT_USERNAME": "wirepas_mqtt_username",
    "WIREPAS_MQTT_PASSWORD": "wirepas_mqtt_password",
    "WIREPAS_RESET_HOUR": "wirepas_reset_hour",
    "WIREPAS_RESET_MINUTE": "wirepas_reset_minute",
    "WIREPAS_NTP_ADDR": "wirepas_ntp_addr",
    "WIREPAS_TZ_OFFSET_MIN": "wirepas_tz_offset_min",
    "WIREPAS_KEEPALIVE_INTVL_S": "wirepas_keepalive_intvl_s",
    "GW_IMEI": "gw_imei",
    "GW_SIM1_IMSI": "gw_sim1_imsi",
    "GW_SIM1_ICCID": "gw_sim1_iccid",
    "GW_SIM2_IMSI": "gw_sim2_imsi",
    "GW_SIM2_ICCID": "gw_sim2_iccid",
    "GW_CORE_VER": "gw_core_ver",
    "GW_CORE_VER Status": "gw_core_ver_status",
    "GW_MAIN_VER": "gw_main_ver",
    "GW_MAIN_VER Status": "gw_main_ver_status",
    "GW_SINK_APP_VER": "gw_sink_app_ver",
    "GW_SINK_APP_VER Status": "gw_sink_app_ver_status",
    "GW_MODEM_FIRMWARE_VER": "gw_modem_firmware_ver",
    "GW_MODEM_FIRMWARE_VER Status": "gw_modem_firmware_ver_status",
    "GW_METER_LIB_VER": "gw_meter_lib_ver",
    "GW_METER_LIB_VER Status": "gw_meter_lib_ver_status",
    "IMG Provisioning Status": "img_provisioning_status",
    "Disable Debug Mode": "disable_debug_mode",
    "Factory Reset": "factory_reset",
    "Overall Status": "overall_status",
    "Total Test Time (s)": "total_test_time_s"
}

COLUMN_MAPPING_GARUD_RF = {
    "MAC_ADDR": "mac_addr",
    "Index": "index",
    "Date_time": "date_time",
    "Original_Serial_Number": "original_serial_number",
    "Live_version": "live_version",
    "Duplicate_Serial_No": "duplicate_serial_no",
    "Check_Calib_Lock_Status_Result": "check_calib_lock_status_result",
    "Original_meter_address": "original_meter_address",
    "Active_Energy": "active_energy",
    "Apparent_Energy": "apparent_energy",
    "Reactive_Energy": "reactive_energy",
    "Meter_PCB_Serial_No": "meter_pcb_serial_no",
    "NIC_PCB_No": "nic_pcb_no",
    "Internal_Version": "internal_version",
    "CalibSign": "calib_sign",
    "FrequencyCoeff": "frequency_coeff",
    "VCoeff": "v_coeff",
    "ICoeff[0]": "i_coeff_0",
    "ICoeff[1]": "i_coeff_1",
    "ActPowerCoeff[0]": "act_power_coeff_0",
    "ActPowerCoeff[1]": "act_power_coeff_1",
    "PhAngle[0]": "ph_angle_0",
    "PhAngle[1]": "ph_angle_1",
    "GPRS_Protocol_Value": "gprs_protocol_value",
    "Voltage_Influence_Test_Voltage": "voltage_influence_test_voltage",
    "OVER_ALL_RESULT": "overall_result",
    "get_duplicate_serial_num": "get_duplicate_serial_num",
    "get_duplicate_serial_num_Retry_Count": "retry1",
    "Calibration_Unlock": "calibration_unlock",
    "Calibration_Unlock_Retry_Count": "retry2",
    "set_original_Meter_Serial_No": "set_original_meter_serial_no",
    "set_original_Meter_Serial_No_Retry_Count": "retry3",
    "get_serial_num_after_set": "get_serial_num_after_set",
    "get_serial_num_after_set_Retry_Count": "retry4",
    "Calib_Lock": "calib_lock",
    "Calib_Lock_Retry_Count": "retry5",
    "Check_Calib_Lock_Status": "check_calib_lock_status",
    "Check_Calib_Lock_Status_Retry_Count": "retry6",
    "Verify_meter_address": "verify_meter_address",
    "Verify_meter_address_Retry_Count": "retry7",
    "Verify_DLMS_Activation": "verify_dlms_activation",
    "Verify_DLMS_Activation_Retry_Count": "retry8",
    "Verify_Clear_Energy": "verify_clear_energy",
    "Verify_Clear_Energy_Retry_Count": "retry9",
    "Get_Meter_PCB_Serial_No": "get_meter_pcb_serial_no",
    "Get_Meter_PCB_Serial_No_Retry_Count": "retry10",
    "Get_NIC_PCB_No": "get_nic_pcb_no",
    "Get_NIC_PCB_No_Retry_Count": "retry11",
    "Get_Internal_Version": "get_internal_version",
    "Get_Internal_Version_Retry_Count": "retry12",
    "Verify_Meter_Calibration": "verify_meter_calibration",
    "Verify_Meter_Calibration_Retry_Count": "retry13",
    "Set_GPRS_Protocol": "set_gprs_protocol",
    "Set_GPRS_Protocol_Retry_Count": "retry14",
    "Get_GPRS_Protocol": "get_gprs_protocol",
    "Get_GPRS_Protocol_Retry_Count": "retry15",
    "Verify_Voltage_Influence_Test": "verify_voltage_influence_test",
    "Verify_Voltage_Influence_Test_Retry_Count": "retry16",
    "Set Provisioning Channel": "set_provisioning_channel",
    "Set Provisioning Channel Status": "set_provisioning_channel_status",
    "Get Provisioning Channel": "get_provisioning_channel",
    "Check Provisioning Parameters Status": "check_provisioning_parameters_status",
    "factory_reset": "factory_reset",
    "factory_reset_Retry_Count": "retry17",
    "Verify_Serial_No_Mismatch": "verify_serial_no_mismatch",
    "Verify_Serial_No_Mismatch_Retry_Count": "retry18",
    "Live_version_Status": "live_version_result",
    "Live_version_Status_Retry_Count": "retry19",
}

COLUMN_MAPPING_GARUD = {
    "MAC_ADDR": "mac_addr",
    "Index": "index",
    "Date_time": "date_time",
    "Original_Serial_Number": "original_serial_number",
    "Live_version": "live_version",
    "Duplicate_Serial_No": "duplicate_serial_no",
    "Check_Calib_Lock_Status_Result": "check_calib_lock_status_result",
    "Original_meter_address": "original_meter_address",
    "Active_Energy": "active_energy",
    "Apparent_Energy": "apparent_energy",
    "Reactive_Energy": "reactive_energy",
    "Meter_PCB_Serial_No": "meter_pcb_serial_no",
    "NIC_PCB_No": "nic_pcb_no",
    "Internal_Version": "internal_version",
    "CalibSign": "calib_sign",
    "FrequencyCoeff": "frequency_coeff",
    "VCoeff": "v_coeff",
    "ICoeff[0]": "i_coeff_0",
    "ICoeff[1]": "i_coeff_1",
    "ActPowerCoeff[0]": "act_power_coeff_0",
    "ActPowerCoeff[1]": "act_power_coeff_1",
    "PhAngle[0]": "ph_angle_0",
    "PhAngle[1]": "ph_angle_1",
    "GPRS_Protocol_Value": "gprs_protocol_value",
    "Voltage_Influence_Test_Voltage": "voltage_influence_test_voltage",
    "OVER_ALL_RESULT": "overall_result",
    "get_duplicate_serial_num": "get_duplicate_serial_num",
    "get_duplicate_serial_num_Retry_Count": "retry1",
    "Calibration_Unlock": "calibration_unlock",
    "Calibration_Unlock_Retry_Count": "retry2",
    "set_original_Meter_Serial_No": "set_original_meter_serial_no",
    "set_original_Meter_Serial_No_Retry_Count": "retry3",
    "get_serial_num_after_set": "get_serial_num_after_set",
    "get_serial_num_after_set_Retry_Count": "retry4",
    "Calib_Lock": "calib_lock",
    "Calib_Lock_Retry_Count": "retry5",
    "Check_Calib_Lock_Status": "check_calib_lock_status",
    "Check_Calib_Lock_Status_Retry_Count": "retry6",
    "Verify_meter_address": "verify_meter_address",
    "Verify_meter_address_Retry_Count": "retry7",
    "Verify_DLMS_Activation": "verify_dlms_activation",
    "Verify_DLMS_Activation_Retry_Count": "retry8",
    "Verify_Clear_Energy": "verify_clear_energy",
    "Verify_Clear_Energy_Retry_Count": "retry9",
    "Get_Meter_PCB_Serial_No": "get_meter_pcb_serial_no",
    "Get_Meter_PCB_Serial_No_Retry_Count": "retry10",
    "Get_NIC_PCB_No": "get_nic_pcb_no",
    "Get_NIC_PCB_No_Retry_Count": "retry11",
    "Get_Internal_Version": "get_internal_version",
    "Get_Internal_Version_Retry_Count": "retry12",
    "Verify_Meter_Calibration": "verify_meter_calibration",
    "Verify_Meter_Calibration_Retry_Count": "retry13",
    "Set_GPRS_Protocol": "set_gprs_protocol",
    "Set_GPRS_Protocol_Retry_Count": "retry14",
    "Get_GPRS_Protocol": "get_gprs_protocol",
    "Get_GPRS_Protocol_Retry_Count": "retry15",
    "Verify_Voltage_Influence_Test": "verify_voltage_influence_test",
    "Verify_Voltage_Influence_Test_Retry_Count": "retry16",
    "factory_reset": "factory_reset",
    "factory_reset_Retry_Count": "retry17",
    "Verify_Serial_No_Mismatch": "verify_serial_no_mismatch",
    "Verify_Serial_No_Mismatch_Retry_Count": "retry18",
    "Live_version_Status": "live_version_result",
    "Live_version_Status_Retry_Count": "retry19",
}

def start_connection(conn_type):
    global _conn
    global _athena_con

    with _conn_lock:
        try:
            if conn_type == 'ems':
                # Re-check inside the lock: another thread may have already
                # connected while this thread was waiting for the lock.
                if _conn and not _conn.closed:
                    return _conn
                _conn = psycopg2.connect(connect_timeout=5, **DB_CONFIG)
                _conn.autocommit = False
                logging.info("EMS Database connection started")
                return _conn
            else:
                if _athena_con and not _athena_con.closed:
                    return _athena_con
                _athena_con = psycopg2.connect(connect_timeout=5, **DB_CONFIG_ATHENA)
                _athena_con.autocommit = False
                print(f"Athena Database connection started")
                logging.info("Athena Database connection started")
                return _athena_con
        except Exception as exc:
            if conn_type == 'ems':
                _conn = None
            else:
                _athena_con = None
            logging.error("Database connection failed: %s", exc)
            return None

def close_connection():
    global _conn
    global _athena_con
    with _conn_lock:
        if _conn and not _conn.closed:
            try:
                _conn.close()
                logging.info("EMS Database connection closed")
            except Exception as exc:
                logging.error("Error while closing EMS database connection: %s", exc)

        if _athena_con and not _athena_con.closed:
            try:
                _athena_con.close()
                logging.info("Athena Database connection closed")
            except Exception as exc:
                logging.error("Error while closing Athena database connection: %s", exc)
        _conn = None
        _athena_con = None

def _get_connection(conn_type = 'ems'):
    if conn_type == 'ems':
        if _conn is None or _conn.closed:
            return start_connection(conn_type)
        return _conn
    else:
        if _athena_con is None or _athena_con.closed:
            return start_connection(conn_type)
        return _athena_con
    

def _table_columns(cursor, table_name, schema):
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """,
        (schema, table_name),
    )
    return [row[0] for row in cursor.fetchall()]

def upload_dataframe(df_frame, meter_type,toolname):
    print(meter_type, toolname)
    mapping = COLUMN_MAPPING_IMG
    TABLE_NAME = "GARUD_IMG_PROV"
    if 'img_prov' in toolname:
        mapping = COLUMN_MAPPING_IMG
        if 'garud' in meter_type.lower():
            TABLE_NAME = "GARUD_IMG_PROV"
        else:
            TABLE_NAME = "BETTER_IMG_PROV"
    else:
        if 'garud' in meter_type.lower():
            TABLE_NAME = "GARUD_FTT"
        else:
            TABLE_NAME = "BETTER_FTT"

        if 'rf' in toolname.lower():
            mapping = COLUMN_MAPPING_GARUD_RF
        else:
            mapping = COLUMN_MAPPING_GARUD

    print(f"Uploading dataframe to {TABLE_SCHEMA}.{TABLE_NAME} table")
    logging.info(f"Uploading dataframe to {TABLE_SCHEMA}.{TABLE_NAME} table with mapping: {mapping}")
    missing_cols = [col for col in mapping if col not in df_frame.columns]
    if missing_cols:
        error_msg = f"DataFrame is missing expected columns: {missing_cols}"
        logging.error(error_msg)
        return False, error_msg

    df_renamed = df_frame.rename(columns=mapping)
    df_renamed["date"] = datetime.date.today()

    conn = _get_connection('ems')
    if conn is None:
        error_msg = "Database connection not available"
        logging.error(error_msg)
        return False, error_msg

    try:
        # Serialize on the shared connection: concurrent COM-port threads
        # must not interleave cursors/commits on the same psycopg2 connection.
        with _conn_lock:
            with conn.cursor() as cursor:
                db_columns = _table_columns(cursor, TABLE_NAME, TABLE_SCHEMA)
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
                    conn.rollback()
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
        with _conn_lock:
            try:
                conn.rollback()
            except Exception:
                pass
        error_msg = str(exc)
        logging.error(f"Dataframe upload failed: {error_msg}")
        return False, error_msg

def fetch_by_pcb_serial(pcb_serial_no, tool_type = 'img'):
    """
    Fetch calibration rows for a given PCB serial number.

    meter_type controls which table is searched:
      - a string containing 'better' -> BETTER1P_CALIB only
      - anything else (e.g. 'garud_1ph') -> GARUD1P_CALIB only
      - None (default) -> both tables are searched and results merged,
        since the serial number alone doesn't say which meter type it was

    Returns a list of dicts (db_column_name -> value), one per matching row,
    newest first if the table has a date_time column, with an extra
    "_table" key noting which table each row came from. Returns [] if
    nothing matches, the DB is unreachable, or the query fails -- callers
    don't need to distinguish "no match" from "lookup failed" unless they
    check logs.
    """
    global _athena_con

    pcb_column = "meter_pcb_serial_no"
    tables = ["mct_logs"]

    # Every COM-port worker thread calls this against the single shared
    # Athena connection, so the query is serialized on _conn_lock. If the
    # connection turns out to be dead, it is dropped and one reconnect+retry
    # is attempted before giving up.
    for attempt in range(2):
        conn = _get_connection('athena')
        if conn is None:
            logging.error(
                "Database connection not available for PCB serial lookup (attempt %d/2)",
                attempt + 1,
            )
            continue

        results = []
        try:
            with _conn_lock:
                with conn.cursor() as cursor:
                    for table_name in tables:
                        db_columns = _table_columns(cursor, table_name, TABLE_SCHEMA_ATHENA)
                        if pcb_column not in db_columns:
                            logging.warning(
                                '"%s"."%s" has no "%s" column -- skipping in PCB serial lookup',
                                TABLE_SCHEMA_ATHENA, table_name, pcb_column,
                            )
                            continue
                        order_column = "test_time" if "test_time" in db_columns else "ingested_at"
                        query = sql.SQL(
                            "SELECT * FROM {}.{} WHERE {} = {} ORDER BY {} DESC LIMIT 1"
                        ).format(
                            sql.Identifier(TABLE_SCHEMA_ATHENA),
                            sql.Identifier(table_name),
                            sql.Identifier(pcb_column),
                            sql.Placeholder(),
                            sql.Identifier(order_column),
                        )

                        cursor.execute(query, (pcb_serial_no,))
                        columns = [desc[0] for desc in cursor.description]
                        for row in cursor.fetchall():
                            row_dict = dict(zip(columns, row))
                            row_dict["_table"] = table_name
                            results.append(row_dict)
            logging.info(
                "PCB serial lookup for %s returned %d row(s) across %s: %s",
                pcb_serial_no, len(results), tables, results,
            )
            if results:
                return results[0]['overall_result'].lower() == 'pass'
            return False
        except psycopg2.Error as exc:
            with _conn_lock:
                try:
                    conn.rollback()
                except Exception:
                    pass
                # Drop the shared connection so the retry (or next call)
                # reconnects instead of reusing the broken one.
                if _athena_con is conn:
                    _athena_con = None
            logging.error(
                "PCB serial lookup failed for %s (attempt %d/2): %s",
                pcb_serial_no, attempt + 1, exc,
            )

    return False



# print(fetch_by_pcb_serial('P26040902000000100700173818', 'img'))