import os
import argparse
from gp_node.network.network_api import NetworkAPI
from gp_node.network.protocols.common.tap import TAPHandler, TAPPacket, TAPError
from gp_node.network.protocols._1p.flash_io_new import FlashIOMasterNew, FlashIOErrorNew
from gp_node.utils.address import Address

import serial
import gp_node.utils.serialize as serialize
import json
import datetime
import time
import easygui


# START_ADDRESS = 0x0100
# METER_ADDRESS = "255.255.255.255" ##"6.0.7.self.Len0"
# DCU_NUMBER_Ver = 0

class TestCasePCTMCT():
    def __init__(self,ser,portID, data_json = {}): 
        # Thread.__init__(self) 
        # self.portID = portID 
        # self.cfg = cfg
        self.network_api = NetworkAPI(ser, portID, "irda")
        self.Len = data_json.get("RETRIES", 4)
        self.nic_pcb_len=data_json.get("NIC_PCB_LENGTH", 27)
        self.dcu_time = ""
        self.live_version_V = 0
        self.Pass = 'Pass'
        self.Fail = 'Fail'
        self.METER_ADDRESS = "255.255.255.255"
        self.inter_version= data_json.get("INTERNAL_VERSION", 0)

    def set_unicast_address(self, address):
        self.METER_ADDRESS = address
        print("Unicast address", self.METER_ADDRESS, address)

    def return_dictionary_value(self,RetryV,ResultS): 
        return_dict = {} 
        if (ResultS == 'Pass'):
            return_dict["Result"] = 'Pass'
            return_dict["Retries"] = RetryV+1
            return return_dict 

        else:
            return_dict["Result"] = 'Fail'
            return_dict["Retries"] = RetryV+1
            return return_dict      
    
    def Set_time_val(self):
        print("\nSending command to set ip time")
        for i in range(self.Len):
            try:
                
                SetTime_status, set_time = self.network_api.set_ip_time(Address(self.METER_ADDRESS),"now")
                print("Set_meter_Time:",SetTime_status)
                if SetTime_status == 'ok':
                    return {"Result": 'pass', "Retries": i+1, "Set_time": str(set_time)}
                    # return self.return_dictionary_value(i,self.Pass)
                    
                else:
                    return {"Result": 'fail', "Retries": i+1, "Set_time": set_time}
                    # return self.return_dictionary_value(i,self.Fail)    
                
            except:
                if ((i+1)==self.Len):
                    # return self.return_dictionary_value(i,self.Fail)
                    return {"Result": 'fail', "Retries": i+1, "Set_time": None}

    def Verify_time_val(self):
        print("\nSending command to verify time")
        return_dict = {}
        for i in range(self.Len):
            try:
                GetTime = self.network_api.get_time(Address(self.METER_ADDRESS))
                print("Get_Time:",GetTime)
                timeDiff = (datetime.datetime.now() - GetTime).total_seconds()
                print("meter time Diff",timeDiff)
                self.dcu_time = GetTime
                if timeDiff >= -20 and timeDiff < 200  :
                    return self.return_dictionary_value(i,self.Pass)
                else:
                    return self.return_dictionary_value(i,self.Fail)
                    
            except:
                print("Retry")
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)
                
    def Factory_reset_val(self):
        print("\nSending command to do factory reset")
        for i in range(self.Len):
            try:
                FactoryInit = self.network_api.factory_init_1(Address(self.METER_ADDRESS))
                print("FactoryInit:",FactoryInit)
                if FactoryInit == 'ok':
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def Meter_Relay_On(self):
        print("\nSending command to do turn relay ON")
        for i in range(self.Len):
            try:
                RelayON = self.network_api.turn_relay_on(Address(self.METER_ADDRESS))
                print("turn relay ON:",RelayON)
                if RelayON == 'relay turned on':
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def Meter_Relay_OFF(self):
        print("\nSending command to do turn relay OFF")
        for i in range(self.Len):
            try:
                RelayOFF = self.network_api.turn_relay_off(Address(self.METER_ADDRESS))
                print("turn relay OFF:",RelayOFF)
                if RelayOFF == 'relay turned off':
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)   
    
    def metering_mode_set(self,mode):
        if (mode==1):
            print("\n sending command to set metering mode 1")
        else:
            print("\n sending command to set metering mode 0")
        metering_mode_Set = self.network_api.set_metering_mode(Address(self.METER_ADDRESS),mode)
        if metering_mode_Set == 'ok' or  metering_mode_Set == 'Okay':
            print("metering mode is changed ")
        else:
            print("metering mode is not changed")

    def relay_mode_set(self,mode):
        print("\nsending command to set relay state 5")
        for i in range(self.Len):
            try:
                metering_mode_Set = self.network_api.set_relay_mode(Address(self.METER_ADDRESS),mode)
                print("metering mode changed:",metering_mode_Set)
                if metering_mode_Set == 'ok' or  metering_mode_Set == 'params rejected':
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)  
    
    def Verify_Current(self,Minvalue,Maxvalue,IsOff = False):
        print("\nSending command to do verify current")
        for i in range(self.Len):
            try:
                Current = self.network_api.get_1p_metering_data(Address(self.METER_ADDRESS))
                CurrentV = Current.return_params["phase_current"]
                CurrentN = Current.return_params["neutral_current"]
                live_tamper=Current.return_params["tamper_event"]

                print("Verify Phase Current:   ",CurrentV)
                print("Verify Neutral Current: ",CurrentN)
                print("Verify live tamper: ",live_tamper)
                if (IsOff == True):
                    if ((Minvalue <= CurrentV <= Maxvalue) and (Minvalue <= CurrentN <= Maxvalue)) and ('CURRENT_REVERSE' not in live_tamper):
                        # return self.return_dictionary_value(i,self.Pass)
                        return {
                            "Result": 'pass',
                            "Retries": i + 1,
                            "CurrentV": CurrentV,
                            "CurrentN": CurrentN,
                            "live_tamper": live_tamper
                            }

                    else:
                        # return self.return_dictionary_value(i,self.Fail)     
                        return {
                            "Result": 'fail',
                            "Retries": i + 1,
                            "CurrentV": CurrentV,
                            "CurrentN": CurrentN,
                            "live_tamper": live_tamper
                            }

                elif (IsOff == False):
                    # print "hi"
                    if ((Minvalue <= CurrentV <= Maxvalue) and (Minvalue <= CurrentN <= Maxvalue)) and ('CURRENT_REVERSE' not in live_tamper):
                        # return self.return_dictionary_value(i,self.Pass)
                        
                        return {
                            "Result": 'pass',
                            "Retries": i + 1,
                            "CurrentV": CurrentV,
                            "CurrentN": CurrentN,
                            "live_tamper": live_tamper
                            }

                    else:
                        # return self.return_dictionary_value(i,self.Fail)    
                        return {
                            "Result": 'fail',
                            "Retries": i + 1,
                            "CurrentV": CurrentV,
                            "CurrentN": CurrentN,
                            "live_tamper": live_tamper
                            }
                
            except Exception as e:
                print(f"Exception in Verify Current: {str(e)}")    
                if ((i+1)==self.Len):
                    # return self.return_dictionary_value(i,self.Fail)
                    return {
                            "Result": 'fail',
                            "Retries": i + 1,
                            "CurrentV": None,
                            "CurrentN": None,
                            "live_tamper": None
                            }
    
    def Verify_Voltage(self,Minvalue,Maxvalue):
        print("\nSending command to do verify voltage")
        for i in range(self.Len):
            try:
                Voltage = self.network_api.get_1p_metering_data(Address(self.METER_ADDRESS))
                VoltageV = Voltage.return_params["voltage"]
                print("Verify voltage:",VoltageV)
                if VoltageV >= Minvalue and VoltageV <= Maxvalue:
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)   

    def Verify_Energy_value(self):
        print("\nSending command to do verify energy")
        for i in range(self.Len):
            try:
                energy = self.network_api.get_1p_metering_data(Address(self.METER_ADDRESS))
                VoltageV = energy.return_params["activeHr_energy_imp"]
                print("Verify energy:",VoltageV)
                if float(VoltageV) <= (0.1):
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)                

    def Calibration_unLock(self):
        print("\nSending command to do Calibration_unLock")
        for i in range(self.Len):
            try:
                arg_val = "0x300,2,bc 5a"
                Calib = self.network_api.eeprom_write(Address(self.METER_ADDRESS),arg_val)
                arg_val2 = "0x300,2,b0 5a"
                time.sleep(0.5)
                Calib2 = self.network_api.eeprom_write(Address(self.METER_ADDRESS),arg_val2)
                print("Calib Unlock:",Calib,Calib2)
                if Calib == 'ok' and Calib2 == 'ok':
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def Calibration_Status(self,IsUnlock =False):
        print("\nSending command to do verify Calibration state")
        if IsUnlock == True:
            calibStr = 'Calib Unlocked !!!'
        else:
            calibStr = 'Calib Locked !!!'
        for i in range(self.Len):
            try:
                CalibS = self.network_api.get_calib_status(Address(self.METER_ADDRESS))
                print("Verify Calibration State:",CalibS)
                if CalibS == calibStr:
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)
                                      
    def Verify_Relay_State(self):
        print("\nSending command to do verify Relay state")
        for i in range(self.Len):
            try:
                Relay = self.network_api.relay_state(Address(self.METER_ADDRESS))
                print("Verify Relay State:",Relay)
                if Relay == 'MANUAL_CONTROL_ON':
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail) 

    def Set_Meter_serial_number(self,SrNumber):
        print("\nSending command to do Set serial number")
        for i in range(self.Len):
            try:
                SrNumbER = self.network_api.set_serial_number(Address(self.METER_ADDRESS),SrNumber)
                print("Set Meter Serial number:",SrNumbER)
                if SrNumbER == 'ok':
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)
    
    def Set_nic_pcb_no(self,nic_pcb_no):
        print("\nSending command to do Set nic pcb number")
        for i in range(self.Len):
            try:
                Sr_num_nic = self.network_api.set_nic_pcb_no(Address(self.METER_ADDRESS),nic_pcb_no)
                print("Set nic pcb number:",nic_pcb_no)
                if Sr_num_nic == 'ok':
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def Verify_Serial_number(self):
        print("\nSending command to do verify Serial number")
        for i in range(self.Len):
            try:
                SERIAL_NUMBER = self.network_api.get_meter_serial_no(Address(self.METER_ADDRESS))
                # print "SERIAL_NUMBER",SERIAL_NUMBER
                SERIAL_NUMBER_V = SERIAL_NUMBER.split('UID 1')
                SERIAL_NUMBER_V2 = SERIAL_NUMBER_V[0].split(':')
                # print "SERIAL_NUMBER",SERIAL_NUMBER_V2
                SerialNumber = SERIAL_NUMBER_V2[1].split(' ')[1]
                print("get_meter_serial_no",SerialNumber)
                if  SerialNumber != '98765432':
                    return SerialNumber
                    # return self.return_dictionary_value(i,self.Pass)

                else:
                    print("Serial No not set in Meter")
                    return SerialNumber
                    # return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)
    
    def Verify_Serial_number2(self):
        print("\nSending command to do verify Serial number")
        for i in range(self.Len):
            try:
                SERIAL_NUMBER = self.network_api.get_meter_serial_no(Address(self.METER_ADDRESS))
                # print "SERIAL_NUMBER",SERIAL_NUMBER
                SERIAL_NUMBER_V = SERIAL_NUMBER.split('UID 1')
                SERIAL_NUMBER_V2 = SERIAL_NUMBER_V[0].split(':')
                # print "SERIAL_NUMBER",SERIAL_NUMBER_V2
                SerialNumber = SERIAL_NUMBER_V2[1].split(' ')[1]
                print("get_meter_serial_no",SerialNumber)
                if  SerialNumber != '98765432':
                    # return SerialNumber
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)   

    def Nic_PCB_No(self):
        print("\nSending command to do verify Nic PCB number")
        for i in range(self.Len):
            try:
                Nic_PCB_NUMBER = str(self.network_api.get_nic_pcb_no(Address(self.METER_ADDRESS)))
                print("get_Nic_Pcb_no",Nic_PCB_NUMBER[0:self.nic_pcb_len])
                if Nic_PCB_NUMBER[0:self.nic_pcb_len]:
                    return Nic_PCB_NUMBER[0:self.nic_pcb_len]

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def get_Meter_address(self,MetrAddress):
        print("\nSending command to get meter address")
        for i in range(self.Len):
            try:
                MtrAddr = str(self.network_api.get_address(Address(self.METER_ADDRESS),str(MetrAddress)))
                print("get Meter address:",MtrAddr)
                # cal_address=self.make_address(serialnum_mct)
                if MtrAddr:
                    return MtrAddr
                    # return self.return_dictionary_value(i,self.Pass)
                else:
                    print("did not get meter address")
                    return MtrAddr
                    # return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def get_Meter_address2(self,MetrAddress,serialnum_mct):
        print("\nSending command to get meter address")
        for i in range(self.Len):
            try:
                MtrAddr = self.network_api.get_address(Address(self.METER_ADDRESS),str(MetrAddress))
                print("get Meter address:",MtrAddr)
                cal_address=self.make_address(serialnum_mct)
                if str(MtrAddr) == cal_address:
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def Verify_Meter_address(self,MetrAddress):
        print("\nSending command to do Get meter address")
        for i in range(self.Len):
            try:
                MtrAddr = self.network_api.get_address(Address(self.METER_ADDRESS),0)
                print("Get Meter address:",MtrAddr)
                if str(MtrAddr) == str(MetrAddress):
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)                                              

    def Verify_Batt_volt(self):
        print("\nSending command to Get Battery Voltage")
        for i in range(self.Len):
            try:
                print (1)
                batt_volt = self.network_api.get_battery_volt_params(Address(self.METER_ADDRESS))
                print("Battery Voltage is :",batt_volt)
                print (batt_volt)
                if (float(batt_volt) >= float(3.0)):
                    # return self.return_dictionary_value(i,self.Pass)
                    return {
                        "Result": "pass",
                        "Retries": i,
                        "Bettery_voltage": batt_volt
                    }
                else:
                    # return self.return_dictionary_value(i,self.Fail)    
                    return {
                        "Result": "fail",
                        "Retries": i,
                        "Bettery_voltage": batt_volt
                    }
            
            except Exception as e:
                print(f"Error in Verify Battery Voltage: {str(e)}")    
                if ((i+1)==self.Len):
                    # return self.return_dictionary_value(i,self.Fail)   
                    return {
                        "Result": "fail",
                        "Retries": i,
                        "Bettery_voltage": None
                    }  

    def Set_Meter_PCB_serial_number(self,SrNumber):
        print("\nSending command to do Set PCB serial number")
        for i in range(self.Len):
            try:
                # print("in ver class")
                SrNumbER = self.network_api.set_pcb_serial_no(Address(self.METER_ADDRESS),SrNumber)
                print("Set Meter PCB Serial number:",SrNumbER)
                if SrNumbER == 'ok':
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def Get_Meter_PCB_serial_number(self,SrNumberV):
        print("\nSending command to do Get PCB serial number")
        # for i in range(self.Len):
        #     try:
                # SrNumbER = self.network_api.get_pcb_serial_no(Address(METER_ADDRESS))
                # arg = str(SrNumbER)
                # arg1 = arg.split("\0")[0]
                # print "Get Meter PCB Serial number:",arg1
        if str(SrNumberV) != '':
            return self.return_dictionary_value(1,self.Pass)

        else:
            return self.return_dictionary_value(1,self.Fail)    
                
            # except:    
            #     if ((i+1)==self.Len):
            #         return self.return_dictionary_value(i,self.Fail)

    def Get_pcb_serial_num(self):
        print("\nSending command to do Get PCB serial number")
        for i in range(self.Len):
            try:
                pcb_serial_no = self.network_api.get_pcb_serial_no(Address(self.METER_ADDRESS))
                pcb_serial_no1 = pcb_serial_no.split("\0")[0]
                print("pcb_serial_no",pcb_serial_no1)
                if str(pcb_serial_no1)!='':
                    return pcb_serial_no1
                
            except:
                pass
    
    def hr_energy_register(self):
        print("\nSending command to check HR Energy Register")
        for i in range(self.Len):
            try:
                hr_energy_bucket = self.network_api.get_nxp_ene_data(Address(self.METER_ADDRESS),1)
                Act_hr_energy = hr_energy_bucket.return_params["activeHr_energy_imp"]
                print("Active HR Energy : {} Kwh".format(Act_hr_energy))
                if Act_hr_energy is not None:
                    return float(Act_hr_energy)
                else:
                    return "Fail"
            except:
                if ((i+1)==self.Len):
                    return "Fail"

    def get_1p_calib_coffi(self):
        print("\nSending command to get 1p calib cofficients")
        for i in range(self.Len):
            try:
                calib_coffi=self.network_api.get_1p_calib_cofficient(Address(self.METER_ADDRESS),1)
                if calib_coffi:
                    return calib_coffi
                else:
                    return 'Fail'
            except Exception as e:
                print("Exception in get_1p_calib_coffi", e)
                if ((i+1)==self.Len):
                    return 'Fail'

    def dlms_Activation_check_value(self):
        print("\nSending command to check dlms activation")
        for i in range(self.Len):
            try:
                dlms_act = self.network_api.check_dlms_activation(Address(self.METER_ADDRESS))
                if dlms_act == 0:
                    return self.return_dictionary_value(i,self.Pass)
                else:
                    return self.return_dictionary_value(i,self.Fail)
            except:
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def Set_Current_rating(self, current_rating_val = "5-10 A"):
        print("\nSending command to Set current rating:",current_rating_val)
        for i in range(self.Len):
            try:
                Setrating = self.network_api.set_current_rating_dlms(Address(self.METER_ADDRESS),str(current_rating_val))
                
                print("Set_rating:", current_rating_val)
                if Setrating == 'ok' or Setrating == 'Okay':
                    return self.return_dictionary_value(i,self.Pass)
                else:
                    return self.return_dictionary_value(i,self.Fail)

            except:
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)
    
    def Set_manufacturing_year(self, manufacturing_year_val = 0000):
        print("\nSending command to Set manufacturing year:",manufacturing_year_val)
        for i in range(self.Len):
            try:
                Setrating = self.network_api.set_manufacturing_year_dlms(Address(self.METER_ADDRESS),str(manufacturing_year_val))
                print("Set_manufacturing_year:", manufacturing_year_val)
                if Setrating == 'ok' or Setrating == 'Okay':
                    return self.return_dictionary_value(i,self.Pass)
                else:
                    return self.return_dictionary_value(i,self.Fail)

            except:
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)
    
    def Set_payment_mode(self, payment_mode = 1):
        print("\nSending command to Set payment mode:",payment_mode)
        for i in range(self.Len):
            try:
                Setrating = self.network_api.set_payment_mode(Address(self.METER_ADDRESS),str(payment_mode))
                print("Set_payment_mode:", payment_mode)
                if Setrating == 'ok' or Setrating == 'Okay' or Setrating == "params rejected":
                    return self.return_dictionary_value(i,self.Pass)
                else:
                    return self.return_dictionary_value(i,self.Fail)

            except:
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def Clear_Energy_Value(self):
        print("\nSending command to Clear Energy")
        for i in range(self.Len):
            try:
                ClearEnergy = self.network_api.tod_enable(Address(self.METER_ADDRESS))
                print("Clear Energy:",ClearEnergy)
                if ClearEnergy == 'ok':
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)    
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def get_live_version_val(self):
        # print(datetime.datetime.now())
        print("\nSending command to get live version")
        for i in range(2):
            try:
                print (self.METER_ADDRESS)
                liveversion = self.network_api.get_live_version(Address(self.METER_ADDRESS))
                print("live_version",liveversion)
                self.live_version_V = liveversion

                if str(liveversion)!='':
                    # print "in live version"
                    return liveversion
                
            except:
                if ((i+1)==2):
                    # print "in fail"
                    return "Fail"
    
    def get_internal_version_val(self):
        print("\nSending command to get internal version")
        for i in range(self.Len):
            try:
                print (self.METER_ADDRESS)
                int_version = self.network_api.get_tool_version(Address(self.METER_ADDRESS))
                print("INTERNAL_VERSION",int_version)
                if(int_version):
                    return str(int_version)
                
            except:
                if ((i+1)==self.Len):
                    return '0'

    def get_bootloader_version_val(self, bootloader_version_val):
        print("\nSending command to get Bootloader Version")
        for i in range(self.Len):
            try:
                bootloader_version = self.network_api.get_bootloader_logs(Address(self.METER_ADDRESS))
                print(f"Bootloader_version{bootloader_version}")
                print(f"send version:{bootloader_version_val}")
                if float(bootloader_version) == float(bootloader_version_val):
                    # return self.return_dictionary_value(i,self.Pass)
                    return {
                        "Result": "pass",
                        "Retries": i,
                        "bootloader_version": bootloader_version
                    }
                else:
                    # return self.return_dictionary_value(i,self.Fail)
                    return {
                        "Result": "fail",
                        "Retries": i,
                        "bootloader_version": bootloader_version
                    }
            except Exception as e:
                print(f"Error in get Bootloader Version: {str(e)}")
                if ((i+1)==self.Len):
                    # return self.return_dictionary_value(i,self.Fail)
                    return {
                        "Result": "fail",
                        "Retries": i,
                        "bootloader_version": None
                    }
    
    def get_better_meter_bootloader_version_val(self, bootloader_inx, bootloader_version_val):
        print("\nSending command to get Bootloader Version")
        for i in range(self.Len):
            try:
                bootloader_version = self.network_api.get_second_bootloader_logs(Address(self.METER_ADDRESS), bootloader_inx)
                if bootloader_inx == 1:
                    print("1st Bootloader_version",bootloader_version)
                    if float(bootloader_version) == float(bootloader_version_val):
                        # return self.return_dictionary_value(i,self.Pass)
                        return {
                            "Result": "pass",
                            "Retries": i,
                            "bootloader_version": bootloader_version
                        }
                    else:
                        # return self.return_dictionary_value(i,self.Fail)
                        return {
                            "Result": "fail",
                            "Retries": i,
                            "bootloader_version": bootloader_version
                        }
                else:
                    print("2nd Bootloader_version",bootloader_version)
                    if float(bootloader_version) == float(bootloader_version_val):
                        # return self.return_dictionary_value(i,self.Pass)
                        return {
                            "Result": "pass",
                            "Retries": i,
                            "bootloader_version": bootloader_version
                        }
                    else:
                        # return self.return_dictionary_value(i,self.Fail)
                        return {
                            "Result": "fail",
                            "Retries": i,
                            "bootloader_version": bootloader_version
                        }
            except Exception as e:
                print(f"Error in get {bootloader_inx} Bootloader version: {str(e)}")
                if ((i+1)==self.Len):
                    # return self.return_dictionary_value(i,self.Fail)
                    return {
                        "Result": "fail",
                        "Retries": i,
                        "bootloader_version": None
                    }

    def get_live_version_val_check_port(self):
        # print(datetime.datetime.now())
        print("\nSending command to get live version")
        for i in range(2):
            try:
                print (self.METER_ADDRESS)
                liveversion = self.network_api.get_live_version(Address(self.METER_ADDRESS))
                print("live_version",liveversion)
                self.live_version_V = liveversion

                if str(liveversion)!='':
                    return liveversion
                
            except:
                if ((i+1)==2):
                    return "Fail"

    def make_address(self, SERIAL_NUM):
        hex_value = hex(SERIAL_NUM)
        desired_length=8  # Convert hex string to integer
        byte_value=self.add_leading_zeros(hex_value, desired_length)
        # print(byte_value)
        
        Address_new=str(int(byte_value[0]+byte_value[1],16))+'.'+str(int(byte_value[2]+byte_value[3],16))+'.'+str(int(byte_value[4]+byte_value[5],16))+'.'+str(int(byte_value[6]+byte_value[7],16))
        print(Address_new)
        return Address_new
         
    def add_leading_zeros(self,hex_value, desired_length):
        hex_value = hex_value.lstrip('0x')
        hex_value = hex_value.lower()
        return "{:0>{width}}".format(hex_value, width=desired_length)

    def get_time_and_version_val(self):
        return_list = []
        return_list.append(self.dcu_time)   
        return_list.append(self.live_version_V)
        # print "List of dcu time and version",return_list
        return return_list   

    def get_meter_sim_and_sim_number(self, meter_type = 'garud'):
        # print(datetime.datetime.now())
        print("\nSending command to verify sim number")
        return_list = []
        for i in range(self.Len):
            try:
                dcuParams = self.network_api.get_gprs_profile_by_index(Address(self.METER_ADDRESS),0,meter_type,isReturn=True)
                # print "dcuParams",dcuParams
                # print(dcuParams)
                if (dcuParams["Active_Sim"] == 1 or dcuParams["Active_Sim"] == 2):
                    return_list.append(dcuParams["SIM_NUM"].decode())
                    return_list.append(dcuParams["Active_Sim"])
                    apn_number = str(dcuParams["APN"].decode())
                    apn_number = apn_number.split('"')[1]
                    return_list.append(apn_number)
                    imei = str(dcuParams["IMEI"].decode())
                    return_list.append(imei)
                    return_list.append(dcuParams["Signal_Strength"])
                    print("SIM_NUM:",return_list[0])
                    print("Active_Sim:",return_list[1])
                    print("APN:",return_list[2])
                    print("IMEI:",return_list[3])
                    print("Signal_Strength: ",return_list[4])
                    if return_list[4] > 20:
                        return return_list
                    else:
                        print("Fail in signal strength")


    
            except:
                pass
        return return_list  

    def check_num_events(self):
        # print(datetime.datetime.now())
        print("\nSending command to check num events")
        return_list1 = []
        return_list = []
        for i in range(self.Len):
         try:
             Check_Num_Events=self.network_api.get_num_event_record(Address(self.METER_ADDRESS))
             print(Check_Num_Events)
             # print(type(Check_Num_Events))
             event1=Check_Num_Events.return_params["current_events"]
             event2=Check_Num_Events.return_params["voltage_events"]
             event3=Check_Num_Events.return_params["power_events"]
             event4=Check_Num_Events.return_params["transactions_events"]
             event5=Check_Num_Events.return_params["non_rollover_events"]
             event6=Check_Num_Events.return_params["control_events"]
             event7=Check_Num_Events.return_params["other_events"]
             event8=Check_Num_Events.return_params["RF_events"]
             event9=Check_Num_Events.return_params["total_events"]
             return_list1.append(self.check_event_list(event1))
             return_list1.append(self.check_event_list(event2))
             return_list1.append(self.check_event_list(event4))
             return_list1.append(self.check_event_list(event5))
             return_list1.append(self.check_event_list(event6))
             return_list1.append(self.check_event_list(event7))
             # print(return_list1)
             if "fail" in return_list1:
                 # return_list=self.Fail
                 return self.return_dictionary_value(i,self.Fail)
             else:
                 return self.return_dictionary_value(i,self.Pass)
                 # print("the packet is in verification class",datetime.datetime.now())
         except:
              if ((i+1)==self.Len):
                 return self.return_dictionary_value(i,self.Fail)
      # except:

             # print(return_list)
             # return return_list
            # print(event1)
      # except:
      #        if ((i+1)==self.Len):
      #            return self.return_dictionary_value(i,self.Fail)
      # except:
      #        if ((i+1)==self.Len):
      #               return self.return_dictionary_value(i,self.Fail)
            # print(Check_Num_Events[1])
            # if ("No. of current related events" in Check_Num_Events):
            #     print("yes i found")

    def check_event_list(self,events):
        if (events == 0):
            return "pass"
        else:
            # easygui.msgbox("fail in "+events)
            return "fail"

    def get_live_tamper(self):
        print("\nSending command to get live tamper")
        for i in range(self.Len):
            try:
                live_tamper=self.network_api.get_1p_metering_data(Address(self.METER_ADDRESS))
                live_event_tamper = live_tamper.return_params["tamper_event"]
                print("live tamper: ",live_event_tamper)
                return self.return_dictionary_value(i,self.Pass)
            except:
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def Set_network_val(self,index_val):
        print("\nSending command to set network")
        for i in range(self.Len):
            try:
                Setnum = self.network_api.set_network(Address(self.METER_ADDRESS), index_val)
                print("Set_network:",Setnum)
                if (Setnum == 'ok') or (Setnum == 'Okay'):
                    return self.return_dictionary_value(i,self.Pass)
                else:
                    return self.return_dictionary_value(i,self.Fail)

            except:
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)
                
    def Set_channel_val(self,index_val):
        print("\nSending command to set channel")
        for i in range(self.Len):
            try:
                Setnum = self.network_api.set_channel(Address(self.METER_ADDRESS), index_val)
                print("Set_channel:",Setnum)
                if (Setnum == 'ok') or (Setnum == 'Okay'):
                    return self.return_dictionary_value(i,self.Pass)
                else:
                    return self.return_dictionary_value(i,self.Fail)

            except:
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def Get_network_val(self,index_val):
        print("\nSending command to Verify meter network")
        for i in range(self.Len):
            try:
                Setnum = self.network_api.get_network(Address(self.METER_ADDRESS))
                print("Get_network:",Setnum)
                if int(Setnum) == int(index_val):
                    return self.return_dictionary_value(i,self.Pass)
                else:
                    return self.return_dictionary_value(i,self.Fail)

            except:
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def Get_channel_val(self,index_val):
        print("\nSending command to Verify channel")
        for i in range(self.Len):
            try:
                Setnum = self.network_api.get_channel(Address(self.METER_ADDRESS))
                print("Get_channel:",Setnum)
                if int(Setnum) == int(index_val):
                    return self.return_dictionary_value(i,self.Pass)
                else:
                    return self.return_dictionary_value(i,self.Fail)

            except:
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)
    
    def set_tunnel_mode(self, Mode = '0xBB'):
        print("\nSending command to do Set Tunnel Mode", Mode)
        # for i in range(self.Len):
        try:
            Mode = self.network_api.set_debug_print(Address(self.METER_ADDRESS), Mode)
            print("Set Tunnel Mode: ",Mode)
            if( Mode.lower() == 'ok') or (Mode.lower() == 'okay'):
                return self.return_dictionary_value(0,self.Pass)
            elif( Mode.lower() == '?'):
                return self.return_dictionary_value(0,self.Fail)
            else:
                return self.return_dictionary_value(0,self.Fail)
            
        except Exception as e:    
            print("Exception in set_tunnel_mode", e)
            if ((self.Len)==self.Len):
                return self.return_dictionary_value(0,self.Fail)
                    
    def meter_reset(self, interval = 65):
        print(f"\nSending command to reset meter with interval: {interval} seconds")
        for i in range(self.Len):
            try:
                reset_status = self.network_api.reset(Address(self.METER_ADDRESS),interval)
                print("Meter reset status: ",reset_status)
                if (reset_status == 'ok') or (reset_status == 'Okay'):
                    return self.return_dictionary_value(i,self.Pass)
                else:
                    return self.return_dictionary_value(i,self.Fail)

            except:
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)       

    def Set_Meter_RelayMode(self, Mode):
        print("\nSending command to do Set Relay Mode", Mode)
        for i in range(self.Len):
            try:
                Mode = self.network_api.set_relay_mode(Address(self.METER_ADDRESS), Mode)
                print("Set Relay Mode :",Mode)
                if Mode == 'ok' or Mode == 'Okay' or 'params rejected':
                    return self.return_dictionary_value(i,self.Pass)
                else:
                    return self.return_dictionary_value(i,self.Fail)
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def set_hardware_version(self, Mode):
        print("\nSending command to do Set Hardware version", Mode)
        for i in range(self.Len):
            try:
                Mode = self.network_api.set_hw_version(Address(self.METER_ADDRESS), Mode)
                print("Set HW Version:",Mode)
                if Mode == 'ok' or Mode == 'Okay':
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)
    
    def get_hardware_version(self):
        print("\nSending command to do Verify Hardware version")
        for i in range(self.Len):
            try:
                hw_version = self.network_api.get_hw_version(Address(self.METER_ADDRESS))
                print("get HW Version:",hw_version)
                if hw_version == 5 :
                    return self.return_dictionary_value(i,self.Pass)

                else:
                    return self.return_dictionary_value(i,self.Fail)
                
            except:    
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def Enable_Print(self):
        self.network_api.enable_print_rxtx(Address(self.METER_ADDRESS))         

    def set_mqtt_topics(self,topic,index_val):
        print("\nSending command to set mqtt topic: ",topic)
        for i in range(self.Len):
            try:
                Setnum = self.network_api.set_gprs_topic(Address(self.METER_ADDRESS),topic,index_val)
                print("set mqtt topic:",Setnum)
                if (Setnum == 'ok') or (Setnum == 'Okay'):
                    return self.return_dictionary_value(i,self.Pass)
                else:
                    return self.return_dictionary_value(i,self.Fail)

            except:
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail) 

    def set_gprs_protocol(self, gprs_protocol_val = 1):
        print("\nSending command to Set GPRS Protocol")
        for i in range(self.Len):
            try:
                Setnum = self.network_api.set_gprs_protocol(Address(self.METER_ADDRESS),gprs_protocol_val)
                print("set Gprs Protocol :",Setnum)
                if (Setnum == 'ok') or (Setnum == 'Okay'):
                    return self.return_dictionary_value(i,self.Pass)
                else:
                    return self.return_dictionary_value(i,self.Fail)
            except:
                if ((i+1)==self.Len):
                    return self.return_dictionary_value(i,self.Fail)

    def get_gprs_protocol(self, gprs_protocol_val):
        print("\nSending command to Get GPRS Protocol")
        for i in range(self.Len):
            try:
                protocol = 0
                Setnum = self.network_api.get_gprs_protocol1(Address(self.METER_ADDRESS)) 
                print(Setnum)
                if (int(Setnum) == 44052):
                    protocol = 2      
                else:
                    protocol = 1 

                print("Get Gprs Protocol :",protocol)
                if(protocol == gprs_protocol_val):
                    # return self.return_dictionary_value(i,self.Pass)
                    return {
                        "Result": "pass",
                        "Retries": i,
                        "Protocol": int(Setnum)
                    }
                else:
                    # return self.return_dictionary_value(i,self.Fail)
                    return {
                        "Result": "fail",
                        "Retries": i,
                        "Protocol": int(Setnum)
                    }
            except Exception as e:
                print(f"Error in get GPRS Protocol value: {str(e)}")
                if ((i+1)==self.Len):
                    # return self.return_dictionary_value(i,self.Fail)    
                    return {
                        "Result": "fail",
                        "Retries": i,
                        "Protocol": None
                    }