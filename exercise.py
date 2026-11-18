import tkinter as tk
import subprocess

def execute_script(com_port):
    input_args = {"com_port": com_port}
    command = r"Downloads\expr.py"
    command+str(input_args)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    if error:
        print("Error:", error)
    else:
        print("Output:", output)

root = tk.Tk()
root.title("FW Upgrade Script")

for i in range(1, 49):
    button = tk.Button(root, text="COM{i}", command=lambda i=i: execute_script(i))
    button.pack()

root.mainloop()