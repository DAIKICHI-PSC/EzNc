from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QPushButton, QTextEdit, QGroupBox, QFrame, QMessageBox)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject
from PySide6.QtGui import QFont

from config import load_config
from tcp_client import TcpClient
from serial_handler import SerialHandler, SerialSignals
from nc_data_processor import process_nc_data
import view_file
import save_dialog
import serial_settings


class TcpSignalEmitter(QObject):
    """受信スレッドからメインスレッドへシグナルで渡す"""
    on_log = Signal(str)
    on_dir = Signal(str)
    on_dim = Signal(str)
    on_dis = Signal(str)
    on_gts = Signal(str)
    on_gtf = Signal(str)
    on_chs = Signal(str)
    on_ptf = Signal(str)


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EzNC")
        self.resize(1024, 600)
        self.setMinimumSize(1024, 600)

        self.config = load_config()
        self.top_dir = self.config["top_dir"]
        self.cur_dir = self.top_dir
        self.save_load_dir = ""
        self.receive_dir_flag = False
        self.rrs_flag = False
        self.send_mode = False
        self.raw_bytes_buffer = []
        self.tree_bind_enabled = True

        self.signals = TcpSignalEmitter()
        self.signals.on_log.connect(self.log)
        self.signals.on_dir.connect(self._handle_dir)
        self.signals.on_dim.connect(self._handle_dim)
        self.signals.on_dis.connect(self._handle_dis)
        self.signals.on_gts.connect(self._handle_gts)
        self.signals.on_gtf.connect(self._handle_gtf)
        self.signals.on_chs.connect(self._handle_chs)
        self.signals.on_ptf.connect(self._handle_ptf)

        self.tcp = TcpClient(self._tcp_callbacks())
        self.serial_signals = SerialSignals()
        self.serial_signals.data_received.connect(self._on_serial_receive)
        self.serial_signals.log_message.connect(self.log)
        self.serial_signals.send_completed.connect(self._on_send_completed)
        self.serial = SerialHandler(self.serial_signals)

        self._build_ui()
        self._connect_server()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Horizontal)

        left_group = QGroupBox("ディレクトリ/データ")
        left_layout = QVBoxLayout(left_group)
        left_layout.setContentsMargins(5, 5, 5, 5)

        self.tree = QTreeWidget()
        tree_font = QFont()
        tree_font.setPointSize(14)
        self.tree.setFont(tree_font)
        self.tree.setHeaderLabels(["Files", "Type"])
        self.tree.header().resizeSection(0, 400)
        self.tree.header().resizeSection(1, 80)
        self.tree.header().setSectionHidden(1, True)
        self.tree.viewport().installEventFilter(self)
        left_layout.addWidget(self.tree)
        splitter.addWidget(left_group)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_widget.setMinimumWidth(200)

        btn_layout = QVBoxLayout()
        button_labels = ["フォルダ/ファイル選択", "上の階層のフォルダへ移動", "プログラム表示", "受信", "送信", "中止", "設定"]
        self.buttons = []
        for label in button_labels:
            btn = QPushButton(label)
            btn.setFont(QFont("", 10))
            btn.setMinimumHeight(45)
            btn_layout.addWidget(btn)
            self.buttons.append(btn)

        self.buttons[0].clicked.connect(lambda: self._btn_click(0))
        self.buttons[1].clicked.connect(lambda: self._btn_click(1))
        self.buttons[2].clicked.connect(lambda: self._btn_click(2))
        self.buttons[3].clicked.connect(lambda: self._btn_click(3))
        self.buttons[4].clicked.connect(lambda: self._btn_click(4))
        self.buttons[5].clicked.connect(lambda: self._btn_click(5))
        self.buttons[6].clicked.connect(lambda: self._btn_click(6))

        right_layout.addLayout(btn_layout)
        right_layout.addStretch()

        log_group = QGroupBox("ログ")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(5, 5, 5, 5)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        right_layout.addWidget(log_group, 1)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        main_layout.addWidget(splitter)
        self.disable_controls()

    def _connect_server(self):
        if not self.tcp.connect(self.config["server_host"], self.config["server_port"]):
            self.disable_controls()
            QMessageBox.critical(self, "エラー", "サーバーに接続できません。\n設定を確認してください。")
            self.hide()
            ss = serial_settings.SerialSettings(self, self.config)
            ss.exec()
            self.show()
            self.config = load_config()
            self.top_dir = self.config["top_dir"]
            self.cur_dir = self.top_dir
            if not self.tcp.connect(self.config["server_host"], self.config["server_port"]):
                QMessageBox.critical(self, "エラー", "サーバーに接続できません。")
                self.close()
                return

        self.log(">ディレクトリのトップ表示\n")
        self.tcp.send(f"Dir{self.cur_dir}\r")

    def log(self, text):
        self.log_text.append(text.rstrip("\n\r"))

    def disable_controls(self):
        for btn in self.buttons[:5]:
            btn.setEnabled(False)
        self.buttons[5].setEnabled(False)
        self.buttons[6].setEnabled(False)
        self.tree_bind_enabled = False

    def enable_controls(self):
        for btn in self.buttons[:5]:
            btn.setEnabled(True)
        self.buttons[5].setEnabled(False)
        self.buttons[6].setEnabled(True)
        self.tree_bind_enabled = True

    def eventFilter(self, obj, event):
        if obj == self.tree.viewport():
            if event.type() == event.Type.MouseButtonPress:
                item = self.tree.itemAt(event.pos())
                if not item:
                    self.tree.clearSelection()
                    return True
        return super().eventFilter(obj, event)

    def _btn_click(self, index):
        if index == 0:
            self.log(">---ディレクトリ選択---\n")
            if not self.tree_bind_enabled:
                return
            selected = self.tree.selectedItems()
            if not selected:
                self.log(">ディレクトリが選択されていません\n")
                return
            item = selected[0]
            item_type = item.data(1, Qt.UserRole)
            if item_type in ("dir", "sub"):
                self.disable_controls()
                self.cur_dir += item.text(0) + "\\"
                self.tcp.send(f"Dir{self.cur_dir}\r")
                self.log(">サーバーと通信中...\n")

        elif index == 1:
            self.log(">---階層戻る---\n")
            if self.cur_dir == self.top_dir:
                self.log(">既にトップです\n")
                return
            self.disable_controls()
            parts = self.cur_dir.rstrip("\\").rsplit("\\", 1)
            self.cur_dir = parts[0] + "\\"
            self.tcp.send(f"Dir{self.cur_dir}\r")
            self.log(">サーバーと通信中...\n")

        elif index == 2:
            self.log(">---データ確認---\n")
            selected = self.tree.selectedItems()
            if not selected:
                self.log(">データが選択されていません\n")
                return
            item = selected[0]
            if item.data(1, Qt.UserRole) in ("dir", "sub"):
                self.log(">データが選択されていません\n")
                return
            self.disable_controls()
            self.tcp.send(f"Gts{self.cur_dir}{item.text(0)}\r")
            self.log(">サーバーと通信中...\n")

        elif index == 3:
            self.log(">---受信---\n")
            selected = self.tree.selectedItems()
            if selected:
                item = selected[0]
                if item.data(1, Qt.UserRole) in ("dir", "sub"):
                    self.disable_controls()
                    sd = save_dialog.SaveDialog(self, self.cur_dir + item.text(0) + "\\")
                    sd.exec()
                    if sd.result:
                        self.save_load_dir = sd.result
                        self.send_rr()
                    else:
                        self.enable_controls()
                    return
                else:
                    self.disable_controls()
                    self.save_load_dir = self.cur_dir + item.text(0)
                    self.send_rr()
                    return
            self.disable_controls()
            sd = save_dialog.SaveDialog(self, self.cur_dir.rstrip("\\"))
            sd.exec()
            if sd.result:
                self.save_load_dir = sd.result
                self.send_rr()
            else:
                self.enable_controls()

        elif index == 4:
            self.log(">---送信---\n")
            selected = self.tree.selectedItems()
            if not selected:
                self.log(">データが選択されていません\n")
                return
            item = selected[0]
            if item.data(1, Qt.UserRole) in ("dir", "sub"):
                self.log(">データが選択されていません\n")
                return
            self.disable_controls()
            self.save_load_dir = self.cur_dir + item.text(0)
            self.tcp.send(f"Gtf{self.save_load_dir}\r")
            self.log(">サーバーと通信中...\n")

        elif index == 5:
            self.serial.close_port()
            if self.rrs_flag:
                self.log(">受信を中止\n")
            else:
                self.log(">送信を中止\n")
            self.enable_controls()

        elif index == 6:
            self.hide()
            ss = serial_settings.SerialSettings(self, self.config)
            ss.exec()
            self.show()
            self.config = load_config()

    def send_rr(self):
        self.tcp.send(f"Chs{self.save_load_dir}\r")
        self.log(">サーバーと通信中...\n")

    def _tcp_callbacks(self):
        return {
            "on_log": lambda x: self.signals.on_log.emit(x),
            "on_dir": lambda x: self.signals.on_dir.emit(x),
            "on_dim": lambda x: self.signals.on_dim.emit(x),
            "on_dis": lambda x: self.signals.on_dis.emit(x),
            "on_gts": lambda x: self.signals.on_gts.emit(x),
            "on_gtf": lambda x: self.signals.on_gtf.emit(x),
            "on_chs": lambda x: self.signals.on_chs.emit(x),
            "on_ptf": lambda x: self.signals.on_ptf.emit(x),
        }

    def _handle_dir(self, dir_names):
        names = [n.strip("\r") for n in dir_names.split("\n") if n.strip("\r")]
        self.tree.clear()
        for name in names:
            item = QTreeWidgetItem(self.tree, [name])
            item.setData(1, Qt.UserRole, "dir")
        self.tcp.send(f"Dim{self.cur_dir}\r")

    def _handle_dim(self, dir_names):
        names = [n.strip("\r") for n in dir_names.split("\n") if n.strip("\r")]
        for name in names:
            item = QTreeWidgetItem(self.tree, [name])
            item.setData(1, Qt.UserRole, "mc")
        self.tcp.send(f"Dis{self.cur_dir}\r")

    def _handle_dis(self, dir_names):
        names = [n.strip("\r") for n in dir_names.split("\n") if n.strip("\r")]
        for name in names:
            item = QTreeWidgetItem(self.tree, [name])
            item.setData(1, Qt.UserRole, "sub")
        if self.receive_dir_flag:
            self.log(">送信完了\n")
            self.receive_dir_flag = False
        else:
            self.log(">操作完了\n")
        self.enable_controls()

    def _handle_gts(self, content):
        if not content.strip():
            self.log(">指定のデータには内容がありません\n")
            self.enable_controls()
            return
        self.log(">操作完了\n")
        vf = view_file.ViewFile(self, content.replace("\n", "\r\n"))
        vf.exec()
        self.enable_controls()

    def _handle_gtf(self, content):
        if not content.strip():
            self.log(">指定のデータには内容がありません\n")
            self.log(">送信取消\n")
            self.enable_controls()
            return
        self.log(f">{self.config['baudrate']},{self.config['parity']},{self.config['bytesize']},{self.config['stopbits']}\n")
        self.log(">NCの設定で通信します\n")
        self.log(">送信を開始します\n")
        self.log(">NCの動作を確認\n")
        self._send_content = content
        if not self.serial.open_port(
            port=self.config["serial_port"],
            baudrate=self.config["baudrate"],
            parity=self.config["parity"],
            bytesize=self.config["bytesize"],
            stopbits=self.config["stopbits"]
        ):
            self.enable_controls()
            return
        self.send_mode = True
        self.buttons[5].setEnabled(True)
        self._start_dcd_monitor_send()

    def _handle_chs(self, result):
        if result == "1":
            ans = QMessageBox.question(
                self,
                "確認",
                "指定のデータは既に存在します。\n"
                "上書きする場合はOKを押してください。\n"
                "キャンセルする場合はキャンセルを押してください。\n"
                "上書きしますか？"
            )
            if ans != QMessageBox.Ok:
                self.log(">受信取消\n")
                self.enable_controls()
                return
        self.rrs_flag = True
        self.log(">選択したデータに上書きします\n")
        self.log(f"{self.save_load_dir}\n")
        self._open_serial_for_send()

    def _handle_ptf(self, result):
        if result == "0":
            self.log(">新しいディレクトリで受信\n")
            self.receive_dir_flag = True
            self.tcp.send(f"Dir{self.cur_dir}\r")
            self.log(">サーバーと通信中...\n")
        elif result == "1":
            self.log(">ファイルに保存できません\n")
            self.log(">受信取消\n")
            self.enable_controls()
        elif result == "2":
            self.log(">ファイルサイズ超過\n")
            self.log(">受信取消\n")
            self.enable_controls()

    def send_rs(self):
        self._open_serial_for_receive()

    def _open_serial_for_receive(self):
        self.log(f">{self.config['baudrate']},{self.config['parity']},{self.config['bytesize']},{self.config['stopbits']}\n")
        self.log(">NCの設定で通信します\n")
        self.log(">受信を開始します\n")
        self.log(">NCの動作を確認\n")
        if not self.serial.open_port(
            port=self.config["serial_port"],
            baudrate=self.config["baudrate"],
            parity=self.config["parity"],
            bytesize=self.config["bytesize"],
            stopbits=self.config["stopbits"]
        ):
            self.enable_controls()
            return
        self.buttons[5].setEnabled(True)
        self._start_dcd_monitor()

    def _open_serial_for_send(self):
        self.log(f">{self.config['baudrate']},{self.config['parity']},{self.config['bytesize']},{self.config['stopbits']}\n")
        self.log(">NCの設定で通信します\n")
        self.log(">受信を開始します\n")
        self.log(">NCの動作を確認\n")
        if not self.serial.open_port(
            port=self.config["serial_port"],
            baudrate=self.config["baudrate"],
            parity=self.config["parity"],
            bytesize=self.config["bytesize"],
            stopbits=self.config["stopbits"]
        ):
            self.enable_controls()
            return
        self.buttons[5].setEnabled(True)
        self._start_dcd_monitor()

    def _start_dcd_monitor(self):
        self.dcd_timer = QTimer()
        self.dcd_timer.timeout.connect(self._check_dcd)
        self.dcd_timer.start(1000)

    def _start_dcd_monitor_send(self):
        self.dcd_timer = QTimer()
        self.dcd_timer.timeout.connect(self._check_dcd_send)
        self.dcd_timer.start(1000)

    def _check_dcd(self):
        if self.serial.check_dcd() and not self.serial.tr_on:
            self.serial.tr_on = True
            self.log(">NCが接続されました\n")
        elif not self.serial.check_dcd() and self.serial.tr_on:
            self.serial.tr_on = False
            self.serial.close_port()
            self.dcd_timer.stop()
            self._process_received_data()

    def _check_dcd_send(self):
        if self.serial.check_dcd() and not self.serial.tr_on:
            self.serial.tr_on = True
            self.log(">NCが接続されました\n")
            self.serial.start_send(self._send_content)
        elif not self.serial.check_dcd() and self.serial.tr_on and self.serial.end_s_flag:
            self.serial.tr_on = False
            self.serial.close_port()
            self.dcd_timer.stop()
            self.send_mode = False
            self.log(">送信完了\n")
            self.log(">\n")
            self.enable_controls()

    def _on_send_completed(self):
        pass

    def _on_serial_receive(self, byte_val):
        if self.send_mode:
            return
        if byte_val == 17:
            if not self.serial.tr_on:
                self.log(">NCから送信...\n")
                self.serial.tr_on = True
                self.raw_bytes_buffer = []
            else:
                self.raw_bytes_buffer = []
                self.log(">NCから送信...\n")
        else:
            self.raw_bytes_buffer.append(byte_val)

    def _process_received_data(self):
        processed = process_nc_data(self.raw_bytes_buffer)
        self.log(">データを処理中...\n")
        self.tcp.send(f"Ptf{processed}\r")
        self.log(">サーバーと通信中...\n")

    def closeEvent(self, event):
        self.serial.close_port()
        self.tcp.disconnect()
        super().closeEvent(event)


def main():
    import sys
    app = QApplication(sys.argv)
    window = MainApp()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
