import serial
import sys
import time
from gp_node.utils import Address
import os
from optparse import OptionParser


class WPShell:


    def __init__(self, ser, standalone=False):
        self.ser = ser
        self.standalone = standalone
        self.ser.flushInput();
        self.ser.flushOutput();
        self.commands = { \
            # "reset": {"actions": {"do": self.do_reset}}, \
            # "set_ack": {"actions": {"do": self.do_set_ACK}}, \
            # "config": {"actions": {"do": self.do_config_mode}}, \
            # "gateway": {"actions": {"do": self.set_gateway_mode}}, \
            # "router": {"actions": {"do": self.set_router_mode}}, \
            # "network": {"actions": {"set": self.set_network, "get": self.get_network}}, \
            "network": {"actions": {"set": self.set_network, "get": self.get_network}},\
            "channel": {"actions": {"set": self.set_channel, "get": self.get_channel}},\
            "address": {"actions": {"set":self.set_address,  "get": self.get_address}},\
            "mode":    {"actions": {"get": self.get_mode}},\
            "device_name": {"actions": {"get": self.get_device_name}}, \
            # "margin": {"actions": {"set": self.set_margin, "get": self.get_margin}}, \
            # "timeout": {"actions": {"set": self.set_timeout, "get": self.get_timeout}}, \
            # "channel": {"actions": {"set": self.set_channel, "get": self.get_channel}}, \
            # "strength": {"actions": {"get": self.get_signal_strength}}, \
            # "temp": {"actions": {"get": self.get_temp}}, \
            # "factory": {"actions": {"do": self.set_factory_default}}, \
            # "tx_carrier": {"actions": {"do": self.do_tx_carrier}}, \
            # "tx_power": {"actions": {"set": self.set_tx_power, "get": self.get_tx_power}, "range": "(-20, -10, 0, 5, 10)"}, \
            # "exit": {"actions": {"do": self.exit_config_mode}}, \
            # "packet_mode":{"actions":{"do":self.do_packet_mode}},\
            # "transparent_mode":{"actions":{"do":self.do_transparent_mode}},\
            # "address":{"actions":{"set":self.set_address,"get":self.get_address}},\
            "help": {"actions": {"do": self.print_help}}}; \

        self.action_symbols = { \
            "get": "?", \
            "set": "=[value]", \
            "do": ""};


    def enter_config_mode(self):
        if self.standalone:
            print ("Assuming device is in config mode (--standalone).");
        else:
            # self.ser.write(self.generate_command(0xC));
            # This sleep is a hack...when the device first goes into config
            # mode it spits out a bunch of ">" characters, so we're waiting
            # for those to be done before getting into the actual work.
            # Need to investigate.
            print ("Processing... (please wait for 1 seconds)");
            # time.sleep(1.0);
        
        self.ser.flushInput();
        self.ser.flushOutput();

    def set_byte(self, address, paylen, payload):
        packet = bytearray()
        packet.extend('M')
        packet.extend('S')
        packet.extend(chr(address))
        packet.extend(chr(paylen))

        for b in range (0, paylen):
            value = payload&0xFF
            packet.extend(chr(value))
            payload >>= 8
        packet.extend('X')

        self.ser.write(packet);
        print ("TX >>", [hex(b) for b in packet])
        time.sleep(0.5);

        bytex = bytearray()
        try:
            while(self.ser.inWaiting() > 0):
                bytex.extend(self.ser.read())
        except Exception as err:
            print ("Error", str(err))
            return 0

        length = len(bytex)
        print ("RX <<", [hex(b) for b in bytex])

        if length == 0:
            return 0

        if bytex[0] == packet[0] and bytex[1] == packet[1] and bytex[2] == packet[2]:
            paystr = ''
            for b in range (0, bytex[3]):
                paystr += chr(bytex[4+b])
            return paystr
        return 0

    def get_byte(self, address, retVal="value"):
        packet = bytearray()
        packet.extend('M')
        packet.extend('G')
        packet.extend(chr(address))
        packet.extend(chr(0x00))
        packet.extend('X')

        self.ser.write(packet);
        print ("TX >>", [hex(b) for b in packet])
        time.sleep(0.5);

        bytex = bytearray()
        try:
            while(self.ser.inWaiting() > 0):
                bytex.extend(self.ser.read())
        except Exception as err:
            print ("Error", str(err))
            return 0

        length = len(bytex)
        print ("RX <<", [hex(b) for b in bytex])
        if length == 0:
            return 0

        if bytex[0] == packet[0] and bytex[1] == packet[1] and bytex[2] == packet[2]:
            if retVal == "value":
                value = 0
                for b in range(0, bytex[3]):
                    value += (bytex[4+b])<<(b*8)
                return value
            elif retVal == "revbytes":
                payload = []
                b = bytex[3]
                while b:
                    b -= 1
                    payload.append(hex(bytex[4+b]))
                return payload
            elif retVal == "str":
                paystr = ''
                for b in range (0, bytex[3]):
                    paystr += chr(bytex[4+b])
                return paystr
            elif retVal == "bytes":
                payload = []
                for b in range (0, bytex[3]):
                    payload.append(hex(bytex[4+b]))
                return payload
        return 0


    # def do_config_mode(self, arg):
    #     self.enter_config_mode();
    #     return "(Entered config mode.)";

    # def do_reset(self, arg):
    #     self.ser.write(self.generate_reset_string());
    #     return "(Reset done.)";

    # def set_gateway_mode(self, arg):
    #     self.enter_config_mode();
    #     time.sleep(0.1);
    #     self.set_command("G")
    #     # self.ser.write("G");
    #     time.sleep(0.1);
    #     self.ser.write("X");
    #     return "(Gateway mode set.)";

    # def set_router_mode(self, arg):
    #     self.enter_config_mode();
    #     time.sleep(0.1);
    #     self.set_command("R")
    #     # self.ser.write("R");
    #     time.sleep(0.1);
    #     self.ser.write("X");
    #     return "(Router mode set.)";

    def set_network(self, arg):
        network = int(arg)
        self.enter_config_mode();
        return self.set_byte(49, 4, network);

    def get_network(self, arg):
        self.enter_config_mode();
        return self.get_byte(49, "bytes");

    def set_channel(self, arg):
        channel = int(arg);
        self.enter_config_mode();
        return self.set_byte(0, 1, channel);

    def get_channel(self, arg):
        self.enter_config_mode();
        return self.get_byte(0);

    def set_address(self,arg):
        address = int(arg);
        self.enter_config_mode();
        return self.set_byte(45, 4, address);

    def get_address(self,arg):
        self.enter_config_mode();
        return self.get_byte(45);

    def get_mode(self,arg):
        self.enter_config_mode();
        return self.get_byte(14);

    def get_device_name(self,arg):
        self.enter_config_mode();
        return self.get_byte(60, "str");

    # def set_margin(self, arg):
    #     margin = int(arg)
    #     self.enter_config_mode();
    #     self.set_byte(59, margin);
    #     self.ser.write("X");
    #     return "(Margin set to " + str(margin) + ".)";

    # def get_margin(self, arg):
    #     margin = 0
    #     self.enter_config_mode();
    #     margin = self.get_byte(59);
    #     self.ser.write("X");
    #     return margin;

    # def set_timeout(self, arg):
    #     timeout = int(arg)
    #     self.enter_config_mode();
    #     self.set_byte(timeout, timeout);
    #     self.ser.write("X");
    #     return "(Timeout set to " + str(timeout) + ".)";

    # def get_timeout(self, arg):
    #     timeout = 0
    #     self.enter_config_mode();
    #     timeout = self.get_byte(13);
    #     self.ser.write("X");
    #     return timeout;

    # def do_set_ACK(self, arg):
    #     self.enter_config_mode();
    #     self.set_byte(0x3A, 17);
    #     self.ser.write("X");
    #     return "(ACK set to )";


    # def get_signal_strength(self, arg):
    #     self.enter_config_mode();
    #     strength = self.get_command('S');
    #     self.ser.write("X");
    #     strength = strength/2
    #     rssi_val = 56-(strength/2)

    #     if(strength > -75):
    #         return "RSSI : ", (rssi_val), "Excellent"
    #     elif(strength > -85):
    #         return "RSSI : ", (rssi_val), "Good"
    #     elif(strength > -95):
    #         return "RSSI : ", (rssi_val), "Ok"
    #     elif(strength > -110):
    #         return "RSSI : ", (rssi_val), "Low"

    # def get_temp(self, arg):
    #     self.enter_config_mode();
    #     temp = self.get_command('U');
    #     self.ser.write("X");
    #     return str(temp-128) + " C";


    # def set_factory_default(self, arg):
    #     self.enter_config_mode();
    #     time.sleep(0.1);
    #     self.set_command("@TM")
    #     time.sleep(0.1);
    #     self.ser.write("X");
    #     return "(Factory default set.)";

    # def do_packet_mode(self,arg):
    #     self.enter_config_mode()
    #     time.sleep(0.1)
    #     self.set_byte(3,0)
    #     time.sleep(0.1)
    #     byte = self.get_byte(3)
    #     time.sleep(0.1)
    #     self.ser.write("X")

    #     if(byte == 0):
    #         return "(in packet mode)"
    #     else:
    #         print byte
    #         return "(failed)"

    # def do_transparent_mode(self,arg):
    #     self.enter_config_mode()
    #     time.sleep(0.1)
    #     self.set_byte(3,1)
    #     time.sleep(0.1)
    #     byte = self.get_byte(3)
    #     time.sleep(0.1)
    #     self.ser.write("X")

    #     if(byte == 1):
    #         return "(in transparent mode)"
    #     else:
    #         print byte
    #         return "(failed)"

    # def do_tx_carrier(self, arg):
    #     self.enter_config_mode();
    #     time.sleep(0.1);
    #     self.ser.write("1");
    #     time.sleep(0.1);
    #     try:
    #         input("(Transmitting carrier. Press enter to stop and exit...)");
    #     except:
    #         self.ser.write("X");
    #         return "(Carrier off.)";
    #     self.ser.write("X");
    #     return "(Carrier off.)";

    # def set_tx_power(self, arg):
    #     power = 0;
    #     if (int(arg) == -20):
    #         power = 1;
    #     elif (int(arg) == -10):
    #         power = 2;
    #     elif (int(arg) == 0):
    #         power = 3;
    #     elif (int(arg) == 5):
    #         power = 4;
    #     elif (int(arg) == 10):
    #         power = 5;
    #     else:
    #         return "(Invalid argment. Valid power levels are " + self.commands["tx_power"]["range"] + ").";
    #     self.enter_config_mode();   
    #     self.set_byte(0x01, power);
    #     self.ser.write("X");
    #     return "(TX power set to " + arg + " dBm.)";

    # def get_tx_power(self, arg):
    #     power = None;
    #     self.enter_config_mode();
    #     raw_power = self.get_byte(0x01);
    #     self.ser.write("X");
    #     if raw_power == 1:
    #         power = -20;
    #     elif raw_power == 2:
    #         power = -10;
    #     elif raw_power == 3:
    #         power = 0;
    #     elif raw_power == 4:
    #         power = 5;
    #     elif raw_power == 5:
    #         power = 10;
    #     else:
    #         return "(Power value returned was invalid: " + str(raw_power) + ")";
    #     return str(power) + " dBm";

    # def exit_config_mode(self, arg):
    #     self.ser.write("X");
    #     return "(Exited config mode.)";

    def print_help(self, arg):
        for command in sorted(self.commands.keys()):
            valid_forms = "";
            for symbol in sorted([self.action_symbols[action] for action in self.commands[command]["actions"]]):
                valid_forms += command + symbol + " ";
            if "range" in self.commands[command]:
                valid_forms += "\n   " + self.commands[command]["range"];
            print (valid_forms);

    def execute(self, input_string):
        if (len(sys.argv) > 1):
            token = input_string;
            command = "";
            action = "";
            argument = "";
            if (token[-1] == "?"):
                command = token[0:-1];
                action = "get";
            elif "=" in token:
                command = token.partition("=")[0];
                action = "set";
                argument = token.partition("=")[2];
            else:
                command = token;
                action = "do"; 
            if command in self.commands:
                if action in self.commands[command]["actions"]:
                    print (self.commands[command]["actions"][action](argument));
                else:
                    print ("Can't " + action + " \"" + command + "\". You can only:");
                    for valid_action in self.commands[command]["actions"]:
                        print ("\t" + valid_action + ": " + command + self.action_symbols[valid_action]);
            else:
                print ("Unknown command: " + command);
                print ("Type \"help\" for a list of known self.commands.");

            print ("")

    def run(self):
        while True:
            print ("wp-shell $ "),
            cmd = input()
            if cmd == "":
                pass
            elif cmd == "exit":
                sys.exit()
            elif cmd == "clear":
                os.system("clear")
            else:
                self.execute(cmd)


if __name__=="__main__":
    parser = OptionParser()
    parser.add_option("-d", "--device", dest="device", help="gateway device file")
    parser.add_option("-t", "--timeout", dest="timeout", help="uart timeout")
    parser.add_option("-b", "--baud_rate", dest="baud_rate", help="baud rate")
    parser.add_option("--standalone", dest="standalone", action='store_true', default=False, help="do not enable preamble");
    (options, args) = parser.parse_args()
    if options.device is None:
        options.device = "COM1"
    if options.baud_rate is None:
        options.baud_rate = 19200
    if options.timeout is None:
        options.timeout = 3
    if options.standalone is None:
        options.standalone = False

    print ("Device: ", options.device)
    print ("Baud Rate: ", options.baud_rate)
    print ("Time out: ", options.timeout)
    print ("Standalone: ", options.standalone)
    try:
        ser = serial.Serial(options.device, int(options.baud_rate), timeout=int(options.timeout))
    except serial.serialutil.SerialException, OSError:
        sys.exit('Error: Could not open communication port')
    rcsh = WPShell(ser, standalone=options.standalone)
    rcsh.run()
