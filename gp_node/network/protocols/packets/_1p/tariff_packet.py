import datetime
from gp_node.utils.serialize import deserialize_uint16
from gp_node.utils.serialize import deserialize_uint8
from gp_node.utils.serialize import deserialize_uint32
from gp_node.utils.serialize import deserialize_int16
from gp_node.utils.serialize import deserialize_int32
import gp_node.utils.serialize as serialize



class TariffPacket(object):

    def __init__(self):

        self.return_params = { "nowGroup"                : 0                
                               ,"energyAtSOM"            : 0.00                  
                               ,"lastBillTS"             : datetime.datetime(1970, 1, 1, 0, 0, 0)                  
                               ,"newTariffTS"            : datetime.datetime(1970, 1, 1, 0, 0, 0)        
                               ,"prepaidModeChangeTS"    : datetime.datetime(1970, 1, 1, 0, 0, 0)        
                               ,"tariffToActivate"       : 0        
                               ,"prepaidEnableF"         : 0      
                               ,"balance"                : 0.00        
                               ,"fdPrice"                : [0,0,0,0,0,0]          
                               ,"energyPrice"            : [0,0,0,0,0,0]          
                               ,"energySlab"             : [0,0,0,0,0]            
                               ,"fdType"                 : 0        
                               ,"fdTelescopicF"          : 0        
                               ,"mmcApplication"         : 0        
                               ,"friendlyHours"          : 0        
                               ,"alertLimit"             : 0        
                               ,"emergencyCredit"        : 0       
                               ,"topUpLimit"             : 0        
                               ,"mmc"                    : 0      
                               ,"CummulativePosRecharge" : 0.00
                               ,"CummulativeNegRecharge" : 0.00
                               ,"netRecharge"            : 0.00
                               ,"currentACBalance"       : 0.00
                               ,"currentFDCost"          : 0.00
                               ,"currentEnergyCost"      : 0.00
                               ,"status"                 : 0
                               ,"tariffType"             : int(1)
                               ,"currentPosRecharge"     : 0.00  # new requirement data added from here
                               ,"currentNegRecharge"     : 0.00
                               ,"egCharges"              : 0.00
                               ,"dgCharges"              : 0.00
                               ,"energyAtSOMEg"          : 0.00
                               ,"energyAtSOMDg"          : 0.00
                               ,"currentNetRecharge"     : 0.00
                               ,"cummEgFdCost"           : 0.00
                               ,"CummulativeFDCostEg"    : 0.00
                               ,"CummulativeFDCostDg"    : 0.00
                               ,"billType"               : "kWh" }


    def __str__(self):
        return (\
        "Fixed Deduction Prices             : {} Paisa\n"
        "Fixed Deduction Type               : {} \n"
        "Fixed Deduction Telescopic Flag    : {} \n"                
        "Slab Prices                        : {} Paisa\n"
        "Slab Energies                      : {} KWh\n"
        "Monthly Minimum Charge             : {} Rs\n"
        "Friendly Hours                     : {} \n"
        "MMC Application                    : {} \n"
        "Alert limit                        : {} \n"
        "Emergency Credits                  : {} \n"
        "Topup limit                        : {} \n")\
                .format(\
                        self.return_params["fdPrice"],
                        self.return_params["fdType"],
                        self.return_params["fdTelescopicF"],
                        self.return_params["energyPrice"],
                        self.return_params["energySlab"],
                        self.return_params["mmc"],
                        self.return_params["friendlyHours"],
                        self.return_params["mmcApplication"],                        
                        self.return_params["alertLimit"],
                        self.return_params["emergencyCredit"],
                        self.return_params["topUpLimit"])

    def deserializePrepaidInfo_new(self,payload):
        bytes = bytearray()
        # print ">>>>>>>>>>>>>>>>>>>>>>>."
        bytes = payload

        temp                            = deserialize_uint16(payload[0:2],"reverse")
        if temp == 0: 
            self.return_params["nowGroup"] = "DG Tariff"
        elif temp == 1:
            self.return_params["nowGroup"] = "EG Tariff"

        self.tariffChangeReqF           = deserialize_uint16(payload[2:4],"reverse")
        self.prepaidModeChangeReqF      = deserialize_uint16(payload[4:6],"reverse") 
        self.return_params["energyAtSOM"]                = (deserialize_uint32(payload[6:10],"reverse"))/100.00
        self.return_params["lastBillTS"]                 = datetime.datetime(1970, 1, 1) +\
                    datetime.timedelta(seconds=((bytes[13]<<24) + (bytes[12]<<16) +(bytes[11]<<8) + bytes[10]))                       
        
        self.return_params["lastBillTS"]                = datetime.datetime(1970, 1, 1) +\
                    datetime.timedelta(seconds=((bytes[17]<<24) + (bytes[16]<<16) +(bytes[15]<<8) + bytes[14])) 
        self.return_params["prepaidModeChangeTS"]        = datetime.datetime(1970, 1, 1) +\
                    datetime.timedelta(seconds=((bytes[21]<<24) + (bytes[20]<<16) +(bytes[19]<<8) + bytes[18])) 
        
        self.return_params["tariffToActivate"]                = deserialize_uint16(payload[22:24],"reverse")
        temp             = deserialize_uint16(payload[24:26],"reverse")
        if temp == 0:
            self.return_params["prepaidEnableF"] = "Disabled"
        elif temp == 0x55:
            self.return_params["prepaidEnableF"] = "Enabled"
        else:
            self.return_params["prepaidEnableF"] = "NA"   
        self.return_params["balance"]                = deserialize_int32(payload[26:30],"reverse")/100.00 
        self.return_params["CummulativePosRecharge"] = deserialize_uint32(payload[30:34],"reverse")/100.00 
        self.return_params["CummulativeNegRecharge"] = deserialize_int32(payload[34:38],"reverse")/100.00     
        self.return_params["netRecharge"]            = deserialize_int32(payload[38:42],"reverse")/100.00     
        self.return_params["currentACBalance"]       = deserialize_int32(payload[42:46],"reverse")/100.00     
        self.return_params["currentFDCost"]          = deserialize_uint32(payload[46:50],"reverse")/100.00     
        self.return_params["currentEnergyCost"]      = deserialize_uint32(payload[50:54],"reverse")/100.00         
        temp2                       = deserialize_uint16(payload[54:56],"reverse")    
        if temp2 == 0:            
            self.return_params["status"]             = "ACC_NO_BALANCE"        
        elif temp2 == 1:
            self.return_params["status"]             = "ACC_NO_BALANCE_FRIENDLY_HOURS"
        elif temp2 == 2:
            self.return_params["status"]             = "ACC_EMERGENCY_CREDIT"
        elif temp2 == 3:
            self.return_params["status"]             = "ACC_LOW_BALANCE"
        elif temp2 == 4:   
            self.return_params["status"]             = "ACC_ENOUGH_BALANCE"   
        elif temp2 == 5:   
            self.return_params["status"]             = "ACC_PREPAID_DISABLED"   
        elif temp2 == 6:   
            self.return_params["status"]             = "ACC_DATA_NOT_AVAILABLE"
               
        self.return_params["currentPosRecharge"]     = deserialize_uint32(payload[56:60],"reverse")/100.00      
        self.return_params["currentNegRecharge"]     = deserialize_uint32(payload[60:64],"reverse")/100.00
        self.return_params["egCharges"]              = deserialize_uint32(payload[64:68],"reverse")/100.00
        self.return_params["dgCharges"]              = deserialize_uint32(payload[68:72],"reverse")/100.00
        self.return_params["energyAtSOMEg"]          = deserialize_uint32(payload[72:76],"reverse")/100.00
        self.return_params["energyAtSOMDg"]          = deserialize_uint32(payload[76:80],"reverse")/100.00
        self.return_params["currentNetRecharge"]     = deserialize_int32(payload[80:84],"reverse")/100.00
        if len(payload) > 84:
            self.return_params["cummEgFdCost"]       = deserialize_uint32(payload[84:88])/100.00
        if len(payload) > 88:
            if payload[88] == 0:
                self.return_params["billType"]           = "kVAh" 
            else:  
                self.return_params["billType"]           = "kWh"   


    def deserializePrepaidInfo(self,payload):
        if len(payload)>82:
            self.deserializePrepaidInfo_new(payload)
            return

        bytes = bytearray()
        # print ">>>>>>>>>>>>>>>>>>>>>>>."
        bytes = payload

        temp                            = deserialize_uint8(payload[0:1],"reverse")
        if temp == 0: 
            self.return_params["nowGroup"] = "DG Tariff"
        elif temp == 1:
            self.return_params["nowGroup"] = "EG Tariff"

        self.tariffChangeReqF           = deserialize_uint8(payload[1:2],"reverse")
        # self.prepaidModeChangeReqF      = deserialize_uint16(payload[4:6],"reverse") 
        self.return_params["energyAtSOM"]                = (deserialize_uint32(payload[2:6]))/100.00
        self.return_params["lastBillTS"]                 = datetime.datetime(1970, 1, 1) +\
                    datetime.timedelta(seconds=((bytes[6]<<24) + (bytes[7]<<16) +(bytes[8]<<8) + bytes[9]))                       
        
        self.return_params["lastBillTS"]                = datetime.datetime(1970, 1, 1) +\
                    datetime.timedelta(seconds=((bytes[10]<<24) + (bytes[11]<<16) +(bytes[12]<<8) + bytes[13])) 
        self.return_params["prepaidModeChangeTS"]        = datetime.datetime(1970, 1, 1) +\
                    datetime.timedelta(seconds=((bytes[14]<<24) + (bytes[15]<<16) +(bytes[16]<<8) + bytes[17])) 
        
        # self.return_params["tariffToActivate"]                = deserialize_uint16(payload[22:24],"reverse")
        temp             = deserialize_uint8(payload[18:19],"reverse")
        if temp == 0:
            self.return_params["prepaidEnableF"] = "Disabled"
        elif temp == 0x55:
            self.return_params["prepaidEnableF"] = "Enabled"
        else:
            self.return_params["prepaidEnableF"] = "NA"   
        self.return_params["balance"]                = deserialize_int32(payload[28:32])/100.00 
        self.return_params["CummulativePosRecharge"] = deserialize_uint32(payload[32:36])/100.00 
        self.return_params["CummulativeNegRecharge"] = deserialize_int32(payload[36:40])/100.00     
        self.return_params["netRecharge"]            = deserialize_int32(payload[40:44])/100.00     
        self.return_params["currentACBalance"]       = deserialize_int32(payload[44:48])/100.00     
        self.return_params["currentFDCost"]          = deserialize_uint32(payload[48:52])/100.00     
        self.return_params["currentEnergyCost"]      = deserialize_uint32(payload[52:56])/100.00         
        temp2                       = deserialize_uint8(payload[19:20],"reverse")    
        if temp2 == 0:            
            self.return_params["status"]             = "ACC_NO_BALANCE"        
        elif temp2 == 1:
            self.return_params["status"]             = "ACC_NO_BALANCE_FRIENDLY_HOURS"
        elif temp2 == 2:
            self.return_params["status"]             = "ACC_EMERGENCY_CREDIT"
        elif temp2 == 3:
            self.return_params["status"]             = "ACC_LOW_BALANCE"
        elif temp2 == 4:   
            self.return_params["status"]             = "ACC_ENOUGH_BALANCE"   
        elif temp2 == 5:   
            self.return_params["status"]             = "ACC_PREPAID_DISABLED"   
        elif temp2 == 6:   
            self.return_params["status"]             = "ACC_DATA_NOT_AVAILABLE"
               
        self.return_params["currentPosRecharge"]     = deserialize_uint32(payload[56:60])/100.00      
        self.return_params["currentNegRecharge"]     = deserialize_uint32(payload[60:64])/100.00
        self.return_params["egCharges"]              = deserialize_uint32(payload[64:68])/100.00
        self.return_params["dgCharges"]              = deserialize_uint32(payload[68:72])/100.00
        self.return_params["energyAtSOMEg"]          = deserialize_uint32(payload[72:76])/100.00
        self.return_params["energyAtSOMDg"]          = deserialize_uint32(payload[76:80])/100.00
        self.return_params["currentNetRecharge"]     = deserialize_int32(payload[20:24])/100.00
        # if len(payload) > 84:
        self.return_params["cummEgFdCost"]       = deserialize_uint32(payload[24:28])/100.00
        # if len(payload) > 88:
        if payload[80] == 0:
            self.return_params["billType"]           = "kVAh"
        else:
            self.return_params["billType"]           = "kWh"    

          

    def getPacketPrepaidInfo(self):

        return (\
        "Prepaid Mode                       : {}\n"
        "Prepaid Billing Type               : {}\n"
        "Change Prepaid Mode Time Stamp     : {}\n"
        "Account balance                    : {} Rs\n"
        "Energy at start of month           : {} {}\n"
        "Time Stamp Of Last Prepaid Billing : {}\n"
        "New Tariff Activation Time Stamp   : {}\n"
        "Next Tariff To Activate            : {}\n"
        "Activated Tariff Group Number      : {}\n"
        "Net Positive Recharge              : {} Rs\n"
        "Net Negative Recharge              : {} Rs\n"
        "Net Recharge                       : {} Rs\n"
        "Current Account Balance            : {} Rs\n"
        "Current FD Cost                    : {} Rs\n"
        "Current Energy Cost                : {} Rs\n"
        "Status                             : {}\n"
        "Current Positive Recharge          : {} Rs\n"
        "Current Negative Recharge          : {} Rs\n"
        "EG Consumption Charge              : {} Rs\n"
        "DG Consumption Charge              : {} Rs\n"
        "EG Energy Consumed                 : {} {}\n"
        "DG Energy Consumed                 : {} {}\n"
        "Current Net Recharge               : {} Rs \n"
        "Cummulative EG FD Cost             : {} Rs \n")\
                .format(\
                        self.return_params["prepaidEnableF"],
                        self.return_params["billType"],
                        self.return_params["prepaidModeChangeTS"],
                        self.return_params["balance"],
                        self.return_params["energyAtSOM"], self.return_params["billType"],
                        self.return_params["lastBillTS"],
                        self.return_params["lastBillTS"],  
                        self.return_params["tariffToActivate"],         
                        self.return_params["nowGroup"],
                        self.return_params["CummulativePosRecharge"],       
                        self.return_params["CummulativeNegRecharge"],       
                        self.return_params["netRecharge"],       
                        self.return_params["currentACBalance"],  
                        self.return_params["currentFDCost"],     
                        self.return_params["currentEnergyCost"], 
                        self.return_params["status"],
                        self.return_params["currentPosRecharge"],
                        self.return_params["currentNegRecharge"],
                        self.return_params["egCharges"],
                        self.return_params["dgCharges"],
                        self.return_params["energyAtSOMEg"], self.return_params["billType"],
                        self.return_params["energyAtSOMDg"], self.return_params["billType"],
                        self.return_params["currentNetRecharge"],
                        self.return_params["cummEgFdCost"])

    def deserializeTariffGroupInfo(self,payload):
        bytes = bytearray()
        bytes = payload
        temp  = deserialize_uint16(payload[0:2],"reverse")

        if temp == 0:
            self.return_params["fdType"] = "daily"
        elif temp == 1:
            self.return_params["fdType"] = "monthly"
        elif temp == 2:
            self.return_params["fdType"] = "slabwise"
        else:
            self.return_params["fdType"] = "NA"
        
        self.return_params["fdTelescopicF"]              = deserialize_uint16(payload[2:4],"reverse") 
        self.return_params["mmcApplication"]             = deserialize_uint16(payload[4:6],"reverse") 
        intFriendlyHours                = int(bytes[6])
        
        friendlyHoursAM = (intFriendlyHours & 0b00001111)
        friendlyHoursPM = (intFriendlyHours & 0b11110000)>>4

        if(friendlyHoursAM == 12):
            self.return_params["friendlyHours"]          = str(friendlyHoursPM) + " PM to " + str(friendlyHoursAM) + " PM"
        elif friendlyHoursAM == 0 and  friendlyHoursPM == 0:
            self.return_params["friendlyHours"]          = str(friendlyHoursPM) + " , " + str(friendlyHoursAM)
        else:
            self.return_params["friendlyHours"]          = str(friendlyHoursPM) + " PM to " + str(friendlyHoursAM) + " AM"
            
        self.return_params["alertLimit"]                 = int(bytes[7])
        self.return_params["emergencyCredit"]            = int(bytes[8])
        self.return_params["topUpLimit"]                 = int(bytes[9])
        self.return_params["mmc"]                        = deserialize_uint16(payload[10:12],"reverse")        
        for i in range(6):
            self.return_params["fdPrice"][i]              = deserialize_uint32(payload[12+(i*4):16+(i*4)],"reverse")

        for i in range(6):
            self.return_params["energyPrice"][i]          = (deserialize_uint16(payload[36+(i*2):38+(i*2)],"reverse"))

        for i in range(5):
            self.return_params["energySlab"][i]           = deserialize_uint16(payload[48+(i*2):50+(i*2)],"reverse")  


    def getTariffGroupInfo(self):
        return (\
        "Fixed Deduction Prices             : {} Paisa\n"
        "Fixed Deduction Type               : {} \n"
        "Fixed Deduction Telescopic Flag    : {} \n"                
        "Slab Prices                        : {} Paisa\n"
        "Slab Energies                      : {} KWh\n"
        "Monthly Minimum Charge             : {} Rs\n"
        "Friendly Hours                     : {} \n"
        "MMC Application                    : {} \n"
        "Alert limit                        : {} *10 Rs\n"
        "Emergency Credits                  : {} *10 Rs\n"
        "Topup limit                        : {} *1000 Rs\n")\
                .format(\
                        self.return_params["fdPrice"],
                        self.return_params["fdType"],
                        self.return_params["fdTelescopicF"],
                        self.return_params["energyPrice"],
                        self.return_params["energySlab"],
                        self.return_params["mmc"],
                        self.return_params["friendlyHours"],
                        self.return_params["mmcApplication"],                        
                        self.return_params["alertLimit"],
                        self.return_params["emergencyCredit"],
                        self.return_params["topUpLimit"])


    def serialize(self):

        payload = bytearray()

        payload.extend(serialize.serialize_uint16(self.return_params["fdType"],"reverse"))
        payload.extend(serialize.serialize_uint16(self.return_params["fdTelescopicF"],"reverse"))
        payload.extend(serialize.serialize_uint16(self.return_params["mmcApplication"],"reverse"))
        payload.extend(serialize.serialize_uint8(self.return_params["friendlyHours"],"reverse"))
        payload.extend(serialize.serialize_uint8(self.return_params["alertLimit"],"reverse"))
        payload.extend(serialize.serialize_uint8(self.return_params["emergencyCredit"],"reverse"))
        payload.extend(serialize.serialize_uint8(self.return_params["topUpLimit"],"reverse"))
        payload.extend(serialize.serialize_uint16(self.return_params["mmc"],"reverse"))    
        
        for index in range(len(self.return_params["fdPrice"])):
            payload.extend(serialize.serialize_uint32(self.return_params["fdPrice"][index],"reverse"))

        for index in range(len(self.return_params["energyPrice"])):
            payload.extend(serialize.serialize_uint16(self.return_params["energyPrice"][index],"reverse"))
        for index in range(len(self.return_params["energySlab"])):
            payload.extend(serialize.serialize_uint16(self.return_params["energySlab"][index],"reverse"))
        payload.extend(serialize.serialize_uint8(self.return_params["tariffType"],"reverse"))
        return payload

    def deserializePrepaidLogs(self,payload):
        bytes = bytearray()
        bytes = payload

        temp                            = deserialize_uint16(payload[0:2],"reverse")
        if temp == 0: 
            self.return_params["nowGroup"] = "DG Tariff"
        elif temp == 1:
            self.return_params["nowGroup"] = "EG Tariff"

        # self.tariffChangeReqF             = deserialize_uint16(payload[2:4],"reverse")
        # self.prepaidModeChangeReqF        = deserialize_uint16(payload[4:6],"reverse") 
        self.return_params["energyAtSOM"] = (deserialize_uint32(payload[6:10],"reverse"))/100.00
        self.return_params["lastBillTS"]  = datetime.datetime(1970, 1, 1) +\
                    datetime.timedelta(seconds=((bytes[13]<<24) + (bytes[12]<<16) +(bytes[11]<<8) + bytes[10]))                       
        
        self.return_params["newTariffTS"] = datetime.datetime(1970, 1, 1) +\
                    datetime.timedelta(seconds=((bytes[17]<<24) + (bytes[16]<<16) +(bytes[15]<<8) + bytes[14])) 
        self.return_params["prepaidModeChangeTS"] = datetime.datetime(1970, 1, 1) +\
                    datetime.timedelta(seconds=((bytes[21]<<24) + (bytes[20]<<16) +(bytes[19]<<8) + bytes[18])) 
        
        self.return_params["tariffToActivate"] = deserialize_uint16(payload[22:24],"reverse")
        temp             = deserialize_uint16(payload[24:26],"reverse")
        if temp == 0:
            self.return_params["prepaidEnableF"] = "Disabled"
        elif temp == 0x55:
            self.return_params["prepaidEnableF"] = "Enabled"
        else:
            self.return_params["prepaidEnableF"] = "NA"

        self.return_params["balance"]                = deserialize_int32(payload[26:30],"reverse")/100.00
        self.return_params["CummulativePosRecharge"] = deserialize_uint32(payload[30:34],"reverse")/100.00
        self.return_params["CummulativeNegRecharge"] = deserialize_uint32(payload[34:38],"reverse")/100.00
        self.return_params["currentPosRecharge"]     = deserialize_uint32(payload[38:42],"reverse")/100.00
        self.return_params["currentNegRecharge"]     = deserialize_uint32(payload[42:46],"reverse")/100.00
        self.return_params["egCharges"]              = deserialize_uint32(payload[46:50],"reverse")/100.00
        self.return_params["dgCharges"]              = deserialize_uint32(payload[50:54],"reverse")/100.00
        self.return_params["energyAtSOMEg"]          = deserialize_uint32(payload[54:58],"reverse")/100.00
        self.return_params["energyAtSOMDg"]          = deserialize_uint32(payload[58:62],"reverse")/100.00
        self.return_params["CummulativeFDCostEg"]    = deserialize_uint32(payload[62:66],"reverse")/100.00
        self.return_params["CummulativeFDCostDg"]    = deserialize_uint32(payload[66:70],"reverse")/100.00
        if payload[70] == 0:
            self.return_params["billType"] = "kVAh"

    def getPacketPrepaidLogs(self):

        return (\
        "Prepaid Mode                       : {}\n"
        "Prepaid Billing Type               : {}\n"
        "Change Prepaid Mode Time Stamp     : {}\n"
        "Account balance                    : {} Rs\n"
        "Energy at start of month           : {} {}\n"
        "Time Stamp Of Last Prepaid Billing : {}\n"
        "New Tariff Activation Time Stamp   : {}\n"
        "Next Tariff To Activate            : {}\n"
        "Activated Tariff Group Number      : {}\n"
        "Net Positive Recharge              : {} Rs\n"
        "Net Negative Recharge              : {} Rs\n"
        "Current Positive Recharge          : {} Rs\n"
        "Current Negative Recharge          : {} Rs\n"
        "EG Consumption Charge              : {} Rs\n"
        "DG Consumption Charge              : {} Rs\n"
        "EG Energy Consumed                 : {} {}\n"
        "DG Energy Consumed                 : {} {}\n"
        "Cumm EG FD Cost                    : {} Rs\n"
        "Cumm DG FD Cost                    : {} Rs\n").format(\
                                            self.return_params["prepaidEnableF"],
                                            self.return_params["billType"],
                                            self.return_params["prepaidModeChangeTS"],
                                            self.return_params["balance"],
                                            self.return_params["energyAtSOM"], self.return_params["billType"],
                                            self.return_params["lastBillTS"],
                                            self.return_params["newTariffTS"],  
                                            self.return_params["tariffToActivate"],         
                                            self.return_params["nowGroup"],
                                            self.return_params["CummulativePosRecharge"],       
                                            self.return_params["CummulativeNegRecharge"],
                                            self.return_params["currentPosRecharge"],
                                            self.return_params["currentNegRecharge"],
                                            self.return_params["egCharges"],
                                            self.return_params["dgCharges"],
                                            self.return_params["energyAtSOMEg"], self.return_params["billType"],
                                            self.return_params["energyAtSOMDg"], self.return_params["billType"],
                                            self.return_params["CummulativeFDCostEg"],
                                            self.return_params["CummulativeFDCostDg"])