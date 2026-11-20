import serial
import subprocess
import time

# === Serial config ===
PORT = "COM16"
BAUDRATE = 9600

# === First data to send ===
initial_bytes = bytes([
    0xAA, 0x01, 0x82, 0x35, 0xC9, 0xFF, 0xFF, 0xFF,
    0xFF, 0x04, 0x04, 0x03, 0x82, 0x35, 0xBB, 0xD9, 0x78
])

# === End data to send ===
end_bytes = bytes([0xAA, 0xBB, 0xCC, 0xDD])

# === Command to run ===
command = [
    "python", r".\read_nic_parameters.py",
    "--serial_port", PORT
]

try:
    # Step 1: Open serial and send first bytes
    with serial.Serial(PORT, BAUDRATE, timeout=1) as ser:
        time.sleep(1)  # let port settle
        print("🔄 Sending initial bytes...")
        ser.write(initial_bytes)
        print("✅ Initial bytes sent.")

    # Step 2: Run the provisioning command
    print("🚀 Running provisioning script...")
    result = subprocess.run(command, capture_output=True, text=True)

    print("✅ Script output:\n", result.stdout)
    if result.stderr:
        print("⚠️ Script errors:\n", result.stderr)

    # Step 3: Send end bytes
    with serial.Serial(PORT, BAUDRATE, timeout=15) as ser:
        time.sleep(1)
        print("🔄 Sending end bytes...")
        ser.write(end_bytes)
        print("✅ End bytes sent.")

except Exception as e:
    print("❌ Error:", e)
