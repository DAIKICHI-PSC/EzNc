from PySide6.QtWidgets import (QDialog, QVBoxLayout, QGroupBox, QLabel,
    QHBoxLayout, QPushButton, QRadioButton, QLineEdit, QComboBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from config import save_config


class SerialSettings(QDialog):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.setWindowTitle("EzNC - 設定")
        self.resize(800, 550)
        self.setModal(True)

        self.config = config.copy()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title_label = QLabel("設定")
        title_label.setFont(QFont("", 12))
        layout.addWidget(title_label)

        server_group = QGroupBox("サーバー設定")
        server_layout = QVBoxLayout(server_group)
        server_layout.setContentsMargins(10, 10, 10, 10)

        host_layout = QHBoxLayout()
        host_layout.addWidget(QLabel("サーバーIP:"))
        self.host_entry = QLineEdit(config["server_host"])
        self.host_entry.setFont(QFont("", 10))
        host_layout.addWidget(self.host_entry)
        server_layout.addLayout(host_layout)

        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("ポート:"))
        self.port_entry = QLineEdit(str(config["server_port"]))
        self.port_entry.setFont(QFont("", 10))
        self.port_entry.setMaximumWidth(80)
        port_layout.addWidget(self.port_entry)
        server_layout.addLayout(port_layout)

        topdir_layout = QHBoxLayout()
        topdir_layout.addWidget(QLabel("トップディレクトリ:"))
        self.topdir_entry = QLineEdit(config["top_dir"])
        self.topdir_entry.setFont(QFont("", 10))
        topdir_layout.addWidget(self.topdir_entry)
        server_layout.addLayout(topdir_layout)

        layout.addWidget(server_group)

        port_group = QGroupBox("COMポート")
        port_layout = QHBoxLayout(port_group)
        port_layout.setContentsMargins(10, 10, 10, 10)
        self.port_combo = QComboBox()
        self.port_combo.setFont(QFont("", 10))
        available_ports = ["COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8"]
        self.port_combo.addItems(available_ports)
        current_port = config.get("serial_port", "COM1")
        idx = self.port_combo.findText(current_port)
        if idx >= 0:
            self.port_combo.setCurrentIndex(idx)
        port_layout.addWidget(self.port_combo)
        layout.addWidget(port_group)

        settings_group = QGroupBox("通信設定")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setContentsMargins(10, 10, 10, 10)

        baud_group = QGroupBox("ボーレート")
        baud_layout = QHBoxLayout(baud_group)
        baud_layout.setContentsMargins(5, 5, 5, 5)
        self.baud_vars = {}
        for baud in ["4800", "2400", "1200"]:
            rb = QRadioButton(baud)
            rb.setChecked(str(config["baudrate"]) == baud)
            baud_layout.addWidget(rb)
            self.baud_vars[baud] = rb
        settings_layout.addWidget(baud_group)

        parity_group = QGroupBox("パリティ")
        parity_layout = QHBoxLayout(parity_group)
        parity_layout.setContentsMargins(5, 5, 5, 5)
        self.parity_vars = {}
        parity_options = [("EVEN", "E"), ("MARK", "M"), ("NONE", "N"),
                          ("ODD", "O"), ("SPACE", "S")]
        for label, val in parity_options:
            rb = QRadioButton(label)
            rb.setChecked(config["parity"] == val)
            parity_layout.addWidget(rb)
            self.parity_vars[val] = rb
        settings_layout.addWidget(parity_group)

        data_group = QGroupBox("データビット")
        data_layout = QHBoxLayout(data_group)
        data_layout.setContentsMargins(5, 5, 5, 5)
        self.data_vars = {}
        for d in ["4", "5", "6", "7", "8"]:
            rb = QRadioButton(d)
            rb.setChecked(str(config["bytesize"]) == d)
            data_layout.addWidget(rb)
            self.data_vars[d] = rb
        settings_layout.addWidget(data_group)

        stop_group = QGroupBox("ストップビット")
        stop_layout = QHBoxLayout(stop_group)
        stop_layout.setContentsMargins(5, 5, 5, 5)
        self.stop_vars = {}
        for s in ["1", "1.5", "2"]:
            rb = QRadioButton(s)
            rb.setChecked(float(s) == config["stopbits"])
            stop_layout.addWidget(rb)
            self.stop_vars[s] = rb
        settings_layout.addWidget(stop_group)

        layout.addWidget(settings_group)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _save(self):
        self.config["server_host"] = self.host_entry.text().strip()
        try:
            self.config["server_port"] = int(self.port_entry.text().strip())
        except ValueError:
            self.config["server_port"] = self.config["server_port"]
        self.config["top_dir"] = self.topdir_entry.text().strip()
        if not self.config["top_dir"].endswith("\\"):
            self.config["top_dir"] += "\\"
        self.config["serial_port"] = self.port_combo.currentText()

        for baud, rb in self.baud_vars.items():
            if rb.isChecked():
                self.config["baudrate"] = int(baud)
                break
        for val, rb in self.parity_vars.items():
            if rb.isChecked():
                self.config["parity"] = val
                break
        for d, rb in self.data_vars.items():
            if rb.isChecked():
                self.config["bytesize"] = int(d)
                break
        for s, rb in self.stop_vars.items():
            if rb.isChecked():
                self.config["stopbits"] = float(s)
                break
        save_config(self.config)
        self.accept()
