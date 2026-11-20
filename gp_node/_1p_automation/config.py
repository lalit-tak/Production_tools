from colorama import init
from termcolor import colored
import json
import xlrd 

import openpyxl
import sys
import os
import easygui
import serial
import importlib

"""
To add new meter type, create folder in 
config with same name as mentioned in TYPE_OF_METER
and put rx tx command files in same way with similar 
names. 
"""

TYPE_OF_METER = "ISM_1P_RF_HOUSEHOLD_1101"


################## Display Configuration Parameters ##################
STEP_INDEX_SIZE         = 4
STRING_DISPLAY_SIZE     = 20
TEST_CASE_DISPLAY_SIZE  = 15
METERTYPE_DISPLAY_SIZE  = 10
RETRY_DISPLAY_SIZE      = 2
RESULT_CASE             = 4
MAX_VAL                 = 13
MIN_VAL                 = 13
METER_DATA              = 13
OPERATOR_SIZE           = 13
TEST_RESULT             = 5
EMPTY_SIZE              = 20
retry                   = int(4)
STRING_DIVIDER          = ' : '
######################################################################

class config:
    def __init__(self):        
        """
        Types of meters are :
        1. ISM_1P_RF_HOUSEHOLD_1100
        2. MAXWELL_1P_RF_HOUSEHOLD_3085
        3. MAXWELL_1P_WIFI_HOUSEHOLD_307
        """        
        self.DEVICE = "COM1"
        self.BAUDRATE = 9600
        self.SERIAL_TIMEOUT  = 3
        self.RETRIES = 4
        self.TOOL_TYPE = "PCT"
        self.CONFIG_FILE_NAME = "serial_config.json"
        self.EXCEL_FILE_NAME = "address_list.xlsx"
        self.LOG_FILE_NAME = "mct_log.json"

        self.SEND_START_CMD = True 

        self.STRING_COMP = "string_comp"
        self.IN_RANGE = "in_range"
        self.EQUAL_TO ="equal_to"
        self.MATCH_IN_DICT = "match_in_dict"
        self.PRESS_ENTER_AFTER_EACH_CASE = True
        self.METER_ADDRESS = "255.255.255.255"
    
    def verify_config_json(self):
        
        config_dict = {}

        try:        
            with open(self.CONFIG_FILE_NAME, 'r+') as file:
                config_file_data = file.read()
                file.close()

            config_dict = json.loads(config_file_data)

        except Exception as e:
            print ("Config file ERROR: \n\n",e)
            config_dict = {"DEVICE":"COM8",
                                "BAUDRATE":9600,
                                "SERIAL_TIMEOUT":3,
                                "RETRIES":4,
                                "TOOL_TYPE":"MRI"            
                            }
            config_file_data = json.dumps(config_dict)
            with open(self.CONFIG_FILE_NAME, 'w+') as file:
                file.write(config_file_data)
                file.close()    

            print ("\n\n New config file created")
            
            self.DEVICE = config_dict["DEVICE"]
            self.BAUDRATE = int(config_dict["BAUDRATE"])
            self.SERIAL_TIMEOUT  = int(config_dict["SERIAL_TIMEOUT"])
            self.RETRIES = int(config_dict["RETRIES"])
            self.TOOL_TYPE = config_dict["TOOL_TYPE"]


        else:
            self.DEVICE = config_dict["DEVICE"]
            self.BAUDRATE = int(config_dict["BAUDRATE"])
            self.SERIAL_TIMEOUT  = int(config_dict["SERIAL_TIMEOUT"])
            self.RETRIES = int(config_dict["RETRIES"])
            self.TOOL_TYPE = config_dict["TOOL_TYPE"]

    def verify_log_json(self):
        
        log_dict = {}

        try:        
            with open(self.LOG_FILE_NAME, 'r+') as file:
                config_file_data = file.read()
                file.close()

            log_dict = json.loads(log_file_data)

        except Exception as e:
            # print "UI config file corrupted, ERROR: ",e
            return False
        else:
            return True

    def add_log_json(self, serial, address):
        
        log_dict = {}

        try:        
            with open(self.LOG_FILE_NAME, 'r+') as file:
                log_file_data = file.read()
                file.close()

            log_dict = json.loads(log_file_data)

        except Exception as e:
            print("Log file ERROR: \n\n",e)

            log_dict[serial] = str(address)
            log_file_data = json.dumps(log_dict)
            with open(self.LOG_FILE_NAME, 'w+') as file:
                file.write(log_file_data)
                file.close()    

            print ("First default log added")

        else:
            log_dict[serial] = str(address)
            log_file_data = json.dumps(log_dict)
            with open(self.LOG_FILE_NAME, 'w+') as file:
                file.write(log_file_data)
                file.close()    


    def is_serial_already_present(self, serial):
        
        log_dict = {}

        with open(self.LOG_FILE_NAME, 'r+') as file:
            log_file_data = file.read()
            file.close()

        log_dict = json.loads(log_file_data)
        if serial in log_dict:
            return True
        else:
            return False

    def is_excel_present(self):
        
        try:
            loc = self.EXCEL_FILE_NAME 
              
            wb = xlrd.open_workbook(loc) 
            sheet = wb.sheet_by_index(0) 
            sheet.cell_value(0, 0) 

        except Exception as e:
            print ("Cap meter .xlsc file not found, creating one for you")
            wb = openpyxl.Workbook()
            wb.create_sheet(index = 0 , title = "MeterList") # MRI_DATA_LOG
            sheet = wb.active 
            print ("sheet name = ",sheet.title)
            # workbook = xlsxwriter.Workbook(loc)
            # worksheet = workbook.add_worksheet()
            # worksheet.write('A1', 'MCT DATA LOG')
            wb.remove_sheet(wb.get_sheet_by_name('Sheet'))

            wb.save(loc)
            print ("New xlsc file created")    

        else:
            
            msg = "Excel file for meter serial number and address not present.\
            \nAdd file and restart tool"
            # easygui.msgbox(msg, \
            #     title= str(self.TOOL_TYPE)+" || GRAMPOWER")
            # sys.exit("Restart Tool")
                # return False
            return False
        
        return True

    def enterSrNum(self, toolName):
        while(1):
            # scanning of barcode and taking serial no input
            serial_num = 0
            try:
                serial_num = input("Enter Meter Serial Num: ")
                # print "type of serial_num = ",type(serial_num)
            except Exception as e:
                print ("Enter integer values only")
            else:
                minRange = int(10000)
                maxRange = int(999999)

                if serial_num < minRange or serial_num >= maxRange:
                    print ("Serial number should be in range of 10000 to 999999")
                # elif True == cfg.is_serial_already_present(str(serial_num)):
                #     print "Serial number already present in logs, re-write new one"
                else:
                    return serial_num   

    def get_system_mac_address(self):
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

    def get_ip_from_excel(self, serial):
        address = 0
        try:
            loc = self.EXCEL_FILE_NAME 
              
            wb = xlrd.open_workbook(loc) 
            sheet = wb.sheet_by_index(0) 
            sheet.cell_value(0, 0) 
            for i in range(sheet.nrows):                
                ser = sheet.cell_value(i, 1)
                if int(serial) == int(ser):
                    address = str(sheet.cell_value(i, 2))   
                
        except Exception as e:
            return False
        else:
            if address == 0:
                return False
            return address

    def add_log_xlsc(self, mac_address, MeterInfo, testResult,bookName,fileName):

        loc = bookName
        # return
        wb = xlrd.open_workbook(loc) 
        sheet = wb.sheet_by_index(0)
        numRows = sheet.nrows+1
        # print "numRows = ",numRows

        wb = openpyxl.load_workbook(loc)
        # sheet1 = wb.active
        sheet1 = wb.get_sheet_by_name(fileName)
        # print "sheet name = ",sheet1.title


        # workbook = xlsxwriter.Workbook(loc)
        # sheets = wbRD.sheets()
        # book_ro = xlrd.open_workbook(loc)
        # book = copy(book_ro)  # creates a writeable copy
        # sheet1 = book_ro.sheet_by_index(0)  # get a first sheet
        # workbook = xlsxwriter.Workbook(loc)
        colx = 1
        cellToWrite = sheet1.cell(numRows,colx)
        cellToWrite.value = mac_address
        colx += 1
        if(1 != numRows):
            cellToWrite = sheet1.cell(numRows,colx)
            cellToWrite.value = sheet.nrows-1
            colx += 1
        
        # print "type of MeterInfo = ",type(MeterInfo)
        for loopCount in range(len(MeterInfo)):
            cellToWrite = sheet1.cell(numRows,colx)
            data = MeterInfo[loopCount]
            cellToWrite.value = data
            colx += 1

        for loopCount in range(len(testResult)):
            cellToWrite = sheet1.cell(numRows,colx, testResult[loopCount])
            data = testResult[loopCount]
            cellToWrite.value = data
            colx += 1
        # print "sheet name = ",sheet1.title
        wb.save(loc)

    def verify_log_xlsc(self,bookName,fileName):
        loc = bookName#self.LOG_FILE_NAME 
        
        try:   
            wb = xlrd.open_workbook(loc) 
            sheet = wb.sheet_by_index(0) 
            sheet.cell_value(0, 0) 

        except Exception as e:
            print ("LOG XL file not found, creating one for you")
            wb = openpyxl.Workbook()
            wb.create_sheet(index = 0 , title = fileName) # MRI_DATA_LOG
            sheet = wb.active 
            print ("sheet name = ",sheet.title)
            # workbook = xlsxwriter.Workbook(loc)
            # worksheet = workbook.add_worksheet()
            # worksheet.write('A1', 'MCT DATA LOG')
            wb.remove_sheet(wb.get_sheet_by_name('Sheet'))

            wb.save(loc)
            print ("New xlsc file created")
            return False
        else:
            return True 

    def add_index_of_pushed_data(self,index,bookName,fileName):

        loc = bookName
        # return
        wb = xlrd.open_workbook(loc) 
        sheet = wb.sheet_by_index(0)
        numRows = sheet.nrows+1
        # print "numRows = ",numRows

        wb = openpyxl.load_workbook(loc)
        # sheet1 = wb.active
        sheet1 = wb.get_sheet_by_name(fileName)
        # print "sheet name = ",sheet1.title


        # workbook = xlsxwriter.Workbook(loc)
        # sheets = wbRD.sheets()
        # book_ro = xlrd.open_workbook(loc)
        # book = copy(book_ro)  # creates a writeable copy
        # sheet1 = book_ro.sheet_by_index(0)  # get a first sheet
        # workbook = xlsxwriter.Workbook(loc)
        colx = sheet.ncols
        # print colx
        cellToWrite = sheet1.cell(1,colx)
        cellToWrite.value = index
        # print "sheet name = ",sheet1.title
        wb.save(loc)           
                
    def getAddress(self,toolName,serial_num):
        
        address = self.get_ip_from_excel(serial_num)
        print ("Address is : ", address)
        if address is not False:
            print ("Meter Serial Number : ", serial_num," Address : ", address)
        else:
            easygui.msgbox(\
            "Meter Serial Number and Address not present in excel sheet.\
            \nUpdate excel sheet for this serial num and address\
            \nand restart TOOL",\
                title=toolName)
            sys.exit("Restart tool")
        return address        

    def trim_string(self,string, size):
        """
        This method trims string from right if smaller size provided than its 
         actual length and it fill spaces on right if larger size provided  

        @param 1: string of any size.
        @param 2: Size for output string.

        @return : string.
        """

        if int(len(string)) > int(size):
            return_str = string[:int(size)]
            return return_str
        else:
            return_str = string.ljust(size)
            return return_str
   
    
    def display(self, test_name = False,\
                      index_no = False,\
                      string_to_display = "NA",\
                      TYPE_OF_METER = TYPE_OF_METER,\
                      retry = False,\
                      upper_space = 0,\
                      lower_space = 0,\
                      printing = True,\
                      logging = False,\
                      script_logging = False,
                      display_sap_str = False,
                      test_case_result = False,
                      procedure_result = False,
                      min_val=False,      
                      max_val=False,
                      meter_data=False,
                      operator=False,
                      empty_size=False):
        """
        This method helps in managing display at terminal, logging in log and script log
        table. It provides configurable positions to display and also maintains
        symmetry. Reason for developing this function is to merge logging and printing
        at one place with symmetry in display and every statement gets associated with 
        its step number, meter address, status etc.

        @return : None

        """

        for i in range(0, int(upper_space)):
            print ('\n')
        str_test_case_name = " "
        if test_name == False:
            str_test_case_name = " "
        else:
            str_test_case_name = test_name
        str_test_case_name =self.trim_string(str_test_case_name, TEST_CASE_DISPLAY_SIZE)
        str_step        = self.trim_string(str(index_no),  STEP_INDEX_SIZE)
        str_display     = str(string_to_display)
        str_display     =self.trim_string(str(string_to_display), STRING_DISPLAY_SIZE)      
        str_meter_type  =self.trim_string(str(TYPE_OF_METER), METERTYPE_DISPLAY_SIZE)  
        str_min_val     =self.trim_string(str(min_val),MIN_VAL)
        str_max_val     = self.trim_string(str(max_val),MAX_VAL)
        str_operator    = self.trim_string(str(operator),OPERATOR_SIZE)
        str_empty       = self.trim_string(str(empty_size),EMPTY_SIZE)
        str_retry       =self.trim_string(str(retry),RETRY_DISPLAY_SIZE)
        str_meter_data = self.trim_string(str(meter_data),METER_DATA)

        if procedure_result==True:
            KEY_RESULT_COLOR = "green"
            str_result = self.trim_string("Pass",TEST_RESULT)
        elif procedure_result==False:
            KEY_RESULT_COLOR = "red"
            str_result = self.trim_string("Fail",TEST_RESULT)
        else:
            KEY_RESULT_COLOR = "white"
            str_result = self.trim_string("NA",TEST_RESULT)
           
        if test_case_result==True:
            TEST_CASE_RESULT_COLOR = "green"
            str_test_case_result = self.trim_string("Pass",TEST_RESULT)
        elif test_case_result==False:
            TEST_CASE_RESULT_COLOR = "red"
            str_test_case_result = self.trim_string("Fail",TEST_RESULT)
        else:
            TEST_CASE_RESULT_COLOR = "white"
            str_test_case_result = self.trim_string("NA",TEST_RESULT)

        # make_string = colored(str_test_case_name,TEST_CASE_RESULT_COLOR,attrs=['bold'])+\
        #               str_step+STRING_DIVIDER+str_display+STRING_DIVIDER+str_meter_type+STRING_DIVIDER+\
        #               str_retry+STRING_DIVIDER+str_operator+STRING_DIVIDER+'min_val = '+str_min_val+\
        #               STRING_DIVIDER+'max_val = '+str_max_val+STRING_DIVIDER+'meter_o/p = '+str_meter_data+\
        #               STRING_DIVIDER+'key_result = '+colored(str_result,KEY_RESULT_COLOR)+STRING_DIVIDER+ \
        #               "Test_result = "+STRING_DIVIDER+colored(str_test_case_result,TEST_CASE_RESULT_COLOR,attrs=['bold'])

        if test_name != False:
            make_string = "\n\n"+str_test_case_name+STRING_DIVIDER+"Test_result = "+STRING_DIVIDER+str_test_case_result+"\n\n"          
        
        else:
            make_string = str_step+STRING_DIVIDER+str_display+STRING_DIVIDER+str_meter_type+STRING_DIVIDER+\
                          str_retry+STRING_DIVIDER+str_operator+STRING_DIVIDER+'min_val = '+str_min_val+\
                          STRING_DIVIDER+'max_val = '+str_max_val+STRING_DIVIDER+'meter_o/p = '+str_meter_data+\
                          STRING_DIVIDER+'key_result = '+ str_result#+STRING_DIVIDER+ "Test_result = "+STRING_DIVIDER+ " " #str_test_case_result

        if printing == True:
            if (test_name != False) and (self.PRESS_ENTER_AFTER_EACH_CASE == True):                
                print (make_string)
                user_input=input("############################################################# Press enter to run next test case #############################################################\n\n")
            else:
                print (make_string)