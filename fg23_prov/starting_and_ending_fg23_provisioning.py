import serial
import subprocess
import time

# === Serial config ===
PORT = "COM2"
BAUDRATE = 9600

# === First data to send ===
initial_bytes = bytes([
    0xAA, 0x01, 0x82, 0x35, 0xC9, 0xFF, 0xFF, 0xFF,
    0xFF, 0x04, 0x04, 0x03, 0x82, 0x35, 0xBB, 0xD9, 0x78
])

# # === End data to send ===
end_bytes = bytes([0xAA, 0xBB, 0xCC, 0xDD])

try:
    # # Step 1: Open serial and send first bytes
    # with serial.Serial(PORT, BAUDRATE, timeout=15) as ser:
    #     time.sleep(1)  # let port settle
    #     print("🔄 Sending initial bytes...")
    #     ser.write(initial_bytes)
    #     print("✅ Initial bytes sent.")

    # Step 2: Run the provisioning command
    with serial.Serial(PORT, BAUDRATE, timeout=15) as ser:
        print("🚀 Running provisioning script...")
        ser.write(mac_address_bytes)
        hex_str = ser.read(4000).hex()
        mac = ":".join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))
        print(mac)
        # print("✅ Script output:\n", result.stderr)



    # # Step 3: Send end bytes
    # with serial.Serial(PORT, BAUDRATE, timeout=15) as ser:
    #     time.sleep(1)
    #     print("🔄 Sending end bytes...")
    #     ser.write(end_bytes)
    #     print("✅ End bytes sent.")

except Exception as e:
    print("❌ Error:", e)
