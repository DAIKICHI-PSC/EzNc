import socket
import threading
from config import DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT


class TcpClient:
    def __init__(self, callbacks):
        self.callbacks = callbacks
        self.sock = None
        self.buffer = ""
        self.connected = False
        self._receive_thread = None

    def connect(self, host=DEFAULT_SERVER_HOST, port=DEFAULT_SERVER_PORT):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect((host, port))
            self.connected = True
            self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._receive_thread.start()
            return True
        except Exception as e:
            self.log_callback(f">TCP接続エラー: {e}\n")
            return False

    def disconnect(self):
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

    def send(self, data):
        if self.connected and self.sock:
            self.sock.sendall(data.encode("cp932"))

    def _receive_loop(self):
        try:
            while self.connected:
                try:
                    data = self.sock.recv(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break

                if not data:
                    self.log_callback(">TCP接続が切断されました\n")
                    break

                try:
                    text = data.decode("cp932")
                except UnicodeDecodeError:
                    text = data.decode("cp932", errors="replace")

                self.buffer += text
                self._process_buffer()
        except Exception as e:
            self.log_callback(f">受信ループ例外: {e}\n")
        finally:
            self.connected = False

    def _process_buffer(self):
        while "\r" in self.buffer:
            end_pos = self.buffer.index("\r")
            line = self.buffer[:end_pos + 1]
            self.buffer = self.buffer[end_pos + 1:]

            if len(line) < 3:
                continue

            command = line[:3]
            payload = line[3:end_pos]

            if command == "Dir":
                self.callbacks["on_dir"](payload)
            elif command == "Dim":
                self.callbacks["on_dim"](payload)
            elif command == "Dis":
                self.callbacks["on_dis"](payload)
            elif command == "Gts":
                self.callbacks["on_gts"](payload)
            elif command == "Gtf":
                self.callbacks["on_gtf"](payload)
            elif command == "Chs":
                self.callbacks["on_chs"](payload)
            elif command == "Ptf":
                self.callbacks["on_ptf"](payload)

    @property
    def log_callback(self):
        return self.callbacks.get("on_log", lambda x: None)
