import socket
import threading
import os
import sys
import time
import json
import ctypes

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QFrame,
    QMessageBox,
)
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QFont, QColor

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

CONFIG_FILE = os.path.join(get_exe_dir(), "config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(data):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "0.0.0.0"


def process_text(source_text):
    source_text = source_text.replace(" ", "")
    source_text = source_text.replace("\r\n", ";")

    if source_text == "":
        return ""

    edited_text = source_text.upper()
    buffer_b = ""
    num_flag = 0

    for ch in edited_text:
        buffer = ch

        if (ord(ch) == 44 or (ord(ch) > 64 and ord(ch) < 91)) and num_flag == 1:
            buffer = " " + ch
            num_flag = 0

        if ord(ch) > 47 and ord(ch) < 58:
            num_flag = 1

        if ch == ";":
            buffer = " ;" + "\r\n"
            num_flag = 0

        buffer_b = buffer_b + buffer

    return buffer_b


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


class EzNcServer(QMainWindow):
    log_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.log_signal.connect(self._append_log)

        self.buffer = ""
        self.save_path = ""
        self.timer_counter = 0
        self.timer_running = False
        self.timer_thread = None
        self.server_socket = None
        self.client_socket = None
        self.client_address = None
        self.server_thread = None
        self.running = False
        self.lock = threading.RLock()
        self.waiting_for_response = False

        self.ip_address = get_local_ip()
        config = load_config()
        self.port = config.get("port", 12716)

        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("EzNC Server")
        self.resize(600, 500)
        self.setMinimumSize(400, 300)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        settings_frame = QFrame()
        settings_layout = QHBoxLayout(settings_frame)

        settings_layout.addWidget(QLabel("Port:"))

        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(1, 65535)
        self.port_spinbox.setValue(self.port)
        self.port_spinbox.setMinimumWidth(80)
        self.port_spinbox.valueChanged.connect(self.save_port)
        settings_layout.addWidget(self.port_spinbox)

        self.start_btn = QPushButton("Listen")
        self.start_btn.clicked.connect(self.start_listen)
        settings_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)
        settings_layout.addWidget(self.stop_btn)

        settings_layout.addStretch()

        self.ip_label = QLabel(f"IP: {self.ip_address}")
        self.ip_label.setStyleSheet("color: blue;")
        settings_layout.addWidget(self.ip_label)

        main_layout.addWidget(settings_frame)

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)
        font = QFont("MS Gothic", 15)
        self.text_box.setFont(font)
        self.text_box.setStyleSheet(
            "QTextEdit { background-color: black; color: white; }"
        )
        main_layout.addWidget(self.text_box)

        QTimer.singleShot(500, self.start_listen)

    def save_port(self, port):
        config = load_config()
        config["port"] = port
        save_config(config)

    MAX_LOG_LINES = 10000

    def _append_log(self, text):
        self.text_box.append(text.replace("\r\n", "\n").replace("\r", "\n"))
        doc = self.text_box.document()
        if doc.lineCount() > self.MAX_LOG_LINES:
            cursor = self.text_box.textCursor()
            cursor.movePosition(cursor.Start)
            lines_to_remove = doc.lineCount() - self.MAX_LOG_LINES + 100
            for _ in range(lines_to_remove):
                cursor.select(cursor.LineUnderCursor)
                cursor.removeSelectedText()
                if not cursor.atEnd():
                    cursor.movePosition(cursor.Down)
            self.text_box.setTextCursor(cursor)
        self.text_box.ensureCursorVisible()

    def ptext(self, text):
        self.log_signal.emit(text)

    def start_listen(self):
        self.port = self.port_spinbox.value()

        if self.running:
            return

        self.running = True
        self.buffer = ""
        self.timer_counter = 0
        self.timer_running = False

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.port_spinbox.setEnabled(False)

        self.setWindowTitle("EzNC Server")

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.ip_address, self.port))
            self.server_socket.listen(1)
            self.server_socket.settimeout(1)

            self.ptext(f">Port {self.port} listening")
            self.ptext(">Waiting for connection")

            self.server_thread = threading.Thread(target=self.accept_connections, daemon=True)
            self.server_thread.start()

        except Exception as e:
            self.ptext(f"***Error: {str(e)}")
            self.running = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def stop_server(self):
        self.running = False
        self.stop_timer()
        self.ptext(">Server stoped.")

        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception:
                pass
            self.client_socket = None

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.port_spinbox.setEnabled(True)

    def accept_connections(self):
        while self.running:
            try:
                self.server_socket.settimeout(1)
                try:
                    client_socket, client_address = self.server_socket.accept()
                except socket.timeout:
                    continue

                if self.client_socket:
                    try:
                        self.client_socket.close()
                    except Exception:
                        pass

                client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                self.client_socket = client_socket
                self.client_address = client_address

                self.ptext(">---Client Connected---")
                self.ptext("")

                recv_thread = threading.Thread(target=self.receive_data, daemon=True)
                recv_thread.start()

                break

            except Exception as e:
                if self.running:
                    self.ptext(f"***Error: {str(e)}")
                break

    def start_timer(self):
        self.timer_running = True
        self.timer_thread = threading.Thread(target=self.timer_loop, daemon=True)
        self.timer_thread.start()

    def stop_timer(self):
        self.timer_running = False
        if self.timer_thread and self.timer_thread != threading.current_thread():
            self.timer_thread.join(timeout=2)
            self.timer_thread = None

    def timer_loop(self):
        while self.timer_running:
            time.sleep(1)
            self.timer_counter += 1
            if self.timer_counter > 60:
                self.stop_timer()
                QTimer.singleShot(
                    0,
                    lambda: self._on_timeout(),
                )
                break

    def _on_timeout(self):
        with self.lock:
            if self.client_socket:
                try:
                    self.client_socket.close()
                except Exception:
                    pass
                self.client_socket = None
        self.ptext(">Time out")
        self.ptext(">---Timeout Disconnect---")
        self.start_listen_auto()

    def start_listen_auto(self):
        self.buffer = ""
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        self.running = True
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.ip_address, self.port))
            self.server_socket.listen(1)
            self.server_socket.settimeout(1)
            self.ptext(f">Port {self.port} listening")
            self.ptext(">Waiting for connection")
            self.server_thread = threading.Thread(target=self.accept_connections, daemon=True)
            self.server_thread.start()
        except Exception as e:
            self.ptext(f"***Error: {str(e)}")

    def receive_data(self):
        client_sock = self.client_socket
        if not client_sock:
            return

        client_sock.settimeout(300)

        try:
            while self.running:
                try:
                    data = client_sock.recv(4096)
                    if not data:
                        break
                    decoded = data.decode("shift-jis", errors="replace")
                    self.process_data(decoded)
                except socket.timeout:
                    if self.waiting_for_response:
                        break
                    continue
                except Exception as e:
                    QTimer.singleShot(0, lambda e=e: self.ptext(f"***Error {str(e)}"))
                    break
        finally:
            self._close_client(client_sock)
            self._on_client_disconnected()

    def _close_client(self, client_sock):
        try:
            client_sock.close()
        except Exception:
            pass
        with self.lock:
            self.client_socket = None

    def _on_client_disconnected(self):
        self.stop_timer()
        self.ptext(">---Client Disconnected---")
        self.start_listen_auto()

    def process_data(self, rec_tcp_data):
        self.stop_timer()
        self.waiting_for_response = False
        with self.lock:
            self.buffer = self.buffer + rec_tcp_data
            end_pos = self.buffer.find("\r")

            if end_pos != -1 and len(self.buffer) > 3:
                ccommand = self.buffer[:3]
                dir_path = self.buffer[3:end_pos]
                self.buffer = ""
            else:
                ccommand = ""
                dir_path = ""

        if ccommand == "Dir":
            self.handle_dir(dir_path)
        elif ccommand == "Dim":
            self.handle_dim(dir_path)
        elif ccommand == "Dis":
            self.handle_dis(dir_path)
        elif ccommand == "Gts":
            self.handle_gts(dir_path)
        elif ccommand == "Gtf":
            self.handle_gtf(dir_path)
        elif ccommand == "Ptf":
            self.handle_ptf(dir_path)
        elif ccommand == "Chs":
            self.handle_chs(dir_path)

    def send_data(self, data):
        with self.lock:
            client_sock = self.client_socket
        if client_sock:
            try:
                client_sock.sendall(data.encode("shift-jis", errors="replace"))
            except Exception as e:
                self.ptext(f"***Send Error: {str(e)}")

    def start_response_timeout(self):
        self.waiting_for_response = True
        self.timer_counter = 0
        self.start_timer()

    def handle_dir(self, dir_path):
        self.ptext(">Client command [Dir] received")
        self.ptext(f">Listing folders in [{dir_path}]")

        dir_files = "Dir"
        try:
            if not os.path.isdir(dir_path):
                self.send_data("Dir\r")
                self.start_response_timeout()
                self.ptext(">No folders found in the specified path")
                return

            for entry in os.listdir(dir_path):
                full_path = os.path.join(dir_path, entry)
                if os.path.isdir(full_path):
                    dir_files = dir_files + entry + "\n"
                    self.ptext(dir_path + entry)

            if dir_files == "Dir":
                self.send_data("Dir\r")
                self.start_response_timeout()
                self.ptext(">No folders found in the specified path")
            else:
                self.send_data(dir_files + "\r")
                self.start_response_timeout()
                self.ptext(">Folder list sent to client")
        except Exception as e:
            self.ptext(f"***Error: {str(e)}")

    def handle_dim(self, dir_path):
        self.ptext(">Client command [Dim] received")
        self.ptext(f">Listing M-code programs in [{dir_path}]")

        dir_files = "Dim"
        try:
            if not os.path.isdir(dir_path):
                self.send_data("Dim\r")
                self.start_response_timeout()
                self.ptext(">No main programs found")
                return

            for entry in sorted(os.listdir(dir_path)):
                if entry.endswith(".m"):
                    dir_files = dir_files + entry + "\n"
                    self.ptext(dir_path + entry)

            if dir_files == "Dim":
                self.send_data("Dim\r")
                self.start_response_timeout()
                self.ptext(">No main programs found")
            else:
                self.send_data(dir_files + "\r")
                self.start_response_timeout()
                self.ptext(">Main program list sent to client")
        except Exception as e:
            self.ptext(f"***Error: {str(e)}")

    def handle_dis(self, dir_path):
        self.ptext(">Client command [Dis] received")
        self.ptext(f">Listing sub programs in [{dir_path}]")

        dir_files = "Dis"
        try:
            if not os.path.isdir(dir_path):
                self.send_data("Dis\r")
                self.start_response_timeout()
                self.ptext(">No sub programs found")
                return

            for entry in sorted(os.listdir(dir_path)):
                if entry.endswith(".s"):
                    dir_files = dir_files + entry + "\n"
                    self.ptext(dir_path + entry)

            if dir_files == "Dis":
                self.send_data("Dis\r")
                self.start_response_timeout()
                self.ptext(">No sub programs found")
            else:
                self.send_data(dir_files + "\r")
                self.start_response_timeout()
                self.ptext(">Sub program list sent to client")
        except Exception as e:
            self.ptext(f"***Error: {str(e)}")

    def handle_gts(self, dir_path):
        self.ptext(">Client command [Gts] received")
        self.ptext(f">Reading file [{dir_path}]")

        dir_files = "Gts"
        try:
            with open(dir_path, "r", encoding="shift-jis", errors="replace", newline="") as f:
                sfile = f.read()

            self.ptext(f">File [{dir_path}] loaded")
            sfile = process_text(sfile)
            sfile = sfile.replace("\r", "")
            self.send_data(dir_files + sfile + "\r")
            self.start_response_timeout()
            self.ptext(f">File [{dir_path}] sent to client")
        except Exception as e:
            self.ptext(f"***Error: {str(e)}")

    def handle_gtf(self, dir_path):
        self.ptext(">Client command [Gtf] received")
        self.ptext(f">Reading file [{dir_path}]")

        dir_files = "Gtf"
        try:
            with open(dir_path, "r", encoding="shift-jis", errors="replace", newline="") as f:
                sfile = f.read()

            if sfile == "":
                self.ptext(">File is empty, cannot send")
                self.send_data("Gtf\r")
                self.start_response_timeout()
                return

            sfile = sfile.replace("\r", "")
            self.send_data(dir_files + sfile + "\r")
            self.start_response_timeout()
            self.ptext(f">File [{dir_path}] sent to client")
        except Exception as e:
            self.ptext(f"***Error: {str(e)}")

    def handle_ptf(self, dir_path):
        self.ptext(">Client command [Ptf] received")

        if dir_path == "":
            self.ptext(">Received data is empty")
            self.ptext(">File size is 0")
            self.send_data("Ptf1\r")
            self.start_response_timeout()
            return

        dir_path = dir_path.replace("\n", "\r\n")

        try:
            if os.path.exists(self.save_path):
                self.ptext(f">File [{self.save_path}] already exists")
                fp_pos = 0
                while os.path.exists(self.save_path + str(fp_pos)):
                    fp_pos += 1
                new_name = self.save_path + str(fp_pos)
                with open(self.save_path, "r", encoding="shift-jis", errors="replace", newline="") as f:
                    content = f.read()
                with open(new_name, "w", encoding="shift-jis", newline="") as f:
                    f.write(content)
                self.ptext(f"Renamed existing file to [{new_name}]")

            with open(self.save_path, "w", encoding="shift-jis", errors="replace", newline="") as f:
                f.write(dir_path)
            self.send_data("Ptf0\r")
            self.start_response_timeout()
            self.ptext(f">Received data saved to [{self.save_path}]")
        except Exception as e:
            self.ptext(f"***Error: {str(e)}")

    def handle_chs(self, dir_path):
        self.ptext(">Client command [Chs] received")
        self.ptext(f">Checking file [{dir_path}]")
        self.save_path = dir_path

        try:
            if not os.path.exists(dir_path):
                self.ptext(">Specified file does not exist")
                self.send_data("Chs0\r")
            else:
                self.ptext(">Specified file exists")
                self.send_data("Chs1\r")
            self.start_response_timeout()
            self.ptext(">Response sent to client")
        except Exception as e:
            self.ptext(f"***Error: {str(e)}")

    def closeEvent(self, event):
        self.stop_server()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = EzNcServer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
