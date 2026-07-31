import serial
import threading
import time
from config import DEFAULT_SERIAL_PORT
from PySide6.QtCore import QObject, Signal


def convert_to_iso(text):
    replacements = {
        "1": chr(177),
        "2": chr(178),
        "4": chr(180),
        "7": chr(183),
        "8": chr(184),
        "C": chr(195),
        "E": chr(197),
        "F": chr(198),
        "I": chr(201),
        "J": chr(202),
        "L": chr(204),
        "O": chr(207),
        "Q": chr(209),
        "R": chr(210),
        "T": chr(212),
        "W": chr(215),
        "X": chr(216),
        " ": chr(160),
        ")": chr(169),
        "/": chr(175),
        "#": chr(163),
        "&": chr(166),
        "*": chr(170),
        ",": chr(172),
        ";": chr(187),
        "=": chr(189),
        ">": chr(190),
        "@": chr(192),
        "[": chr(168),
        "]": chr(191),
    }
    result = ""
    for ch in text:
        if ch in replacements:
            result += replacements[ch]
        else:
            result += ch
    result = result.replace("\r", "")
    if chr(207) in result:
        idx = result.index(chr(207))
        result = result[:idx] + ":" + result[idx + 1:]
    return result


class SerialSignals(QObject):
    data_received = Signal(int)
    log_message = Signal(str)
    send_completed = Signal()


class SerialHandler:
    def __init__(self, signals: SerialSignals):
        self.signals = signals
        self.ser = None
        self.tr_on = False
        self.end_s_flag = False
        self.tmp_stop = False
        self.transfer_data = ""
        self.count_n = 0
        self.d_length = 0
        self._send_thread = None

    def open_port(self, port=DEFAULT_SERIAL_PORT, baudrate=4800, parity="N",
                   bytesize=8, stopbits=2):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            parity_map = {"N": serial.PARITY_NONE, "E": serial.PARITY_EVEN,
                          "O": serial.PARITY_ODD, "M": serial.PARITY_MARK,
                          "S": serial.PARITY_SPACE}
            stopbits_map = {1: serial.STOPBITS_ONE, 1.5: serial.STOPBITS_ONE_POINT_FIVE, 2: serial.STOPBITS_TWO}
            self.ser = serial.Serial(
                port=port,
                baudrate=int(baudrate),
                parity=parity_map.get(parity, serial.PARITY_NONE),
                bytesize=int(bytesize),
                stopbits=stopbits_map.get(float(stopbits), serial.STOPBITS_ONE),
                dsrdtr=False,
                rtscts=False,
                xonxoff=False,
                timeout=1
            )
            time.sleep(0.1)
            self.ser.dtr = True
            self.ser.rts = True
            self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._receive_thread.start()
            return True
        except Exception as e:
            self.signals.log_message.emit(f">COMポートが開けません: {e}\n")
            return False

    def close_port(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None

    def _receive_loop(self):
        try:
            while self.ser and self.ser.is_open:
                data = self.ser.read(1)
                if data:
                    byte_val = data[0]
                    self.signals.data_received.emit(byte_val)
        except Exception:
            pass

    def start_send(self, transfer_data):
        clean_data = transfer_data.replace("\r", "")
        iso_data = convert_to_iso(clean_data)
        self.transfer_data = chr(165) + chr(10) + iso_data + chr(165)
        self.d_length = len(self.transfer_data)
        self.count_n = 1
        self.end_s_flag = False
        self.tmp_stop = False
        self._send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self._send_thread.start()

    def _send_loop(self):
        try:
            while not self.end_s_flag and not self.tmp_stop:
                if self.d_length > 10:
                    chunk = self.transfer_data[self.count_n:self.count_n + 10]
                    self.ser.write(bytes(ord(c) for c in chunk))
                    self.ser.flush()
                    self.count_n += 10
                    self.d_length -= 10
                    time.sleep(0.02)
                else:
                    chunk = self.transfer_data[self.count_n:self.count_n + self.d_length]
                    self.ser.write(bytes(ord(c) for c in chunk))
                    self.ser.flush()
                    self.end_s_flag = True
            self.signals.send_completed.emit()
        except Exception as e:
            self.signals.log_message.emit(f">送信エラー: {e}\n")

    def check_dcd(self):
        if self.ser and self.ser.is_open:
            return self.ser.cd
        return False

    @property
    def input_data(self):
        if self.ser and self.ser.is_open:
            data = self.ser.read(self.ser.in_waiting)
            return list(data)
        return []
