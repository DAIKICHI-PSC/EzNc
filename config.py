import os
import sys
import ctypes

def get_exe_dir():
    try:
        get_command_line_w = ctypes.windll.kernel32.GetCommandLineW
        get_command_line_w.restype = ctypes.c_wchar_p
        cmd_line = get_command_line_w()
        exe_path = cmd_line.strip().strip('"')
        return os.path.dirname(os.path.abspath(exe_path))
    except Exception:
        if getattr(sys, 'frozen', False):
            return os.path.dirname(os.path.abspath(sys.executable))
        return os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(get_exe_dir(), "daiya.ini")

DEFAULT_SERVER_HOST = "192.168.1.200"
DEFAULT_SERVER_PORT = 12716
DEFAULT_TOP_DIR = "\\\\192.168.1.201\\usr\\nc\\"

DEFAULT_BAUDRATE = 4800
DEFAULT_PARITY = "N"
DEFAULT_BYTESIZE = 8
DEFAULT_STOPBITS = 2

DEFAULT_SERIAL_PORT = "COM1"

PARITY_MAP = {
    "N": "N",
    "E": "E",
    "O": "O",
    "M": "M",
    "S": "S"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            lines = [line.strip() for line in f.readlines()]
        return {
            "server_host": lines[0] if len(lines) > 0 and lines[0] else DEFAULT_SERVER_HOST,
            "server_port": int(lines[1]) if len(lines) > 1 and lines[1] else DEFAULT_SERVER_PORT,
            "top_dir": lines[2] if len(lines) > 2 and lines[2] else DEFAULT_TOP_DIR,
            "serial_port": lines[3] if len(lines) > 3 and lines[3] else DEFAULT_SERIAL_PORT,
            "baudrate": int(lines[4]) if len(lines) > 4 else DEFAULT_BAUDRATE,
            "parity": lines[5] if len(lines) > 5 else DEFAULT_PARITY,
            "bytesize": int(lines[6]) if len(lines) > 6 else DEFAULT_BYTESIZE,
            "stopbits": float(lines[7]) if len(lines) > 7 else DEFAULT_STOPBITS,
        }
    else:
        save_config({
            "server_host": DEFAULT_SERVER_HOST,
            "server_port": DEFAULT_SERVER_PORT,
            "top_dir": DEFAULT_TOP_DIR,
            "serial_port": DEFAULT_SERIAL_PORT,
            "baudrate": DEFAULT_BAUDRATE,
            "parity": DEFAULT_PARITY,
            "bytesize": DEFAULT_BYTESIZE,
            "stopbits": DEFAULT_STOPBITS,
        })
        return {
            "server_host": DEFAULT_SERVER_HOST,
            "server_port": DEFAULT_SERVER_PORT,
            "top_dir": DEFAULT_TOP_DIR,
            "serial_port": DEFAULT_SERIAL_PORT,
            "baudrate": DEFAULT_BAUDRATE,
            "parity": DEFAULT_PARITY,
            "bytesize": DEFAULT_BYTESIZE,
            "stopbits": DEFAULT_STOPBITS,
        }

def save_config(config):
    stopbits = config['stopbits']
    if stopbits == int(stopbits):
        stopbits_str = str(int(stopbits))
    else:
        stopbits_str = str(stopbits)
    with open(CONFIG_FILE, "w") as f:
        f.write(f"{config['server_host']}\n")
        f.write(f"{config['server_port']}\n")
        f.write(f"{config['top_dir']}\n")
        f.write(f"{config['serial_port']}\n")
        f.write(f"{config['baudrate']}\n")
        f.write(f"{config['parity']}\n")
        f.write(f"{config['bytesize']}\n")
        f.write(f"{stopbits_str}\n")
