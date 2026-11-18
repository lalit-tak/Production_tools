# README.md

## Requirements installation

These scripts need some external modules.

First move to [/nic_app/provisioning/scripts](/nic_app/provisioning/scripts)

To install them please use:

```Python
pip install -r requirements.txt
```

## Files

|File|Explanation / Usage|
|-|-|
|[`nic_provisioning.py`](/nic_app/provisioning/scripts/nic_provisioning.py)|Manages the communication with the NIC. **Must not be used directly!**|
|[`wirepas_provisioning.py`](/nic_app/provisioning/scripts/wirepas_provisioning.py)|Manages the generation, encoding and decoding of the data that are used in the provisioning and reading processes. **Must not be used directly!**|
|[`provision_nic_parameters.py`](/nic_app/provisioning/scripts/provision_nic_parameters.py)|This script will apply the parameters provided to the NIC and read them back.|
|[`read_nic_parameters.py`](/nic_app/provisioning/scripts/read_nic_parameters.py)|This script will read the parameters currently stored on the NIC.|

## General information

### Communication

The communication is performed through the meter port at 19200 bauds.

### Behavior

The NIC will open a 100 ms window after every boot, during which it's possible to provision or read parameters. After this 100 ms window, it's not possible to provision or read the NIC parameters anymore.

### Setup

It is required to have the following to provision a NIC or read its parameters:

- A PC, Running the Python Script
- A Serial USB Converter, that will connect the PC to the NIC's Meter Port
- A NIC

Then, the process to provision is the following

1. Connect the PC to the NIC using the Serial USB Converter
2. Launch the script with the right parameters
3. Wait until the provisioning is successfully performed

If anything goes wrong (e.g. missing NIC Parameters, Serial Error, etc.), the script will print an error and exit.

## `provision_nic_parameters.py`

### Script help

To access the scripts' help please use the following command:

```Python
python3 provision_nic_parameters.py -h
```

### Required parameters

Without this parameter, the `provision_nic_parameters.py` script cannot be launched.

|Parameter|Description|Example|
|-|-|-|
|`--serial_port`|Serial port used to communicate with the NIC.|`--serial_port /dev/ttyUSB0`|

### Optional Parameters

These are optional parameters, please specify them is they are missing from the [`config.mk`](/nic_app/config.mk) file.

Note: At least one of these parameters must be set to be able to launch the script.

|Parameter|Description|Example|
|-|-|-|
|`--node_address`|Node Address used by the NIC for the Wirepas Network.|`--node_address 0x12347678` or `--node_address 305419896`|
|`--encryption_key`|Encryption Key used by the NIC for the Wirepas Network. Must be specified as a 16 bytes value.|`--encryption_key AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA`|
|`--authentication_key`|Authentication Key used by the NIC for the Wirepas Network. Must be specified as a 16 bytes value.|`--authentication_key BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB`|
|`--network_address`|Network address used by the NIC for the Wirepas Network.|`--network_address 0x123476` or `--network_address 1193046`|
|`--network_channel`|Network channel used by the NIC for the Wirepas Network.|`--network_channel 1`|

### Launching the script (with minimum parameters)

```Python
python3 provision_nic_parameters.py --serial_port /dev/ttyUSB0 --node_address 0x12345678
```

#### Advanced script launching

It's possible to create a file that stores these parameter to avoid having to write them every time.

**However, we advise not to specify the node address in it, as it shall be unique.**

**We also advise not to specify the serial port inside it, if there are multiple Serial USB Converters in use to communicate with different NICs.**

Here's what the file could look like:

Name of the file: `parameters`

```txt
--encryption_key
22222222222222222222222222222222
--authentication_key
33333333333333333333333333333333
--network_address
7023224
--network_channel
1
```

Then, the script can be executed like this:

```Python
python3 provision_nic_parameters.py --serial_port /dev/ttyUSB0 --node_address 0x12345678 @parameters
```

## `read_nic_parameters.py`

### Script help

To access the scripts' help please use the following command:

```Python
python3 read_nic_parameters.py -h
```

#### Required parameters

Without this parameter, the `read_nic_parameters.py` script cannot be launched.

|Parameter|Description|Example|
|-|-|-|
|`--serial_port`|Serial port used to communicate with the NIC.|`--serial_port /dev/ttyUSB0`|

### Launching the script

```Python
python3 provision_nic_parameters.py --serial_port /dev/ttyUSB0
```
