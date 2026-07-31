from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QFrame, QPushButton, QRadioButton)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from nc_data_processor import validate_data_name


class SaveDialog(QDialog):
    def __init__(self, parent, path):
        super().__init__(parent)
        self.setWindowTitle("EzNC - 保存")
        self.resize(800, 400)
        self.setModal(True)

        self.path = path.rstrip("\\")
        self.ext_name = ".m"
        self.result = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title_label = QLabel("受信するデータの名前を入力")
        title_label.setFont(QFont("", 12))
        layout.addWidget(title_label)

        path_group = QGroupBox("受信ディレクトリ")
        path_layout = QVBoxLayout(path_group)
        path_layout.setContentsMargins(5, 5, 5, 5)
        path_label = QLabel(self.path)
        path_label.setFont(QFont("", 10))
        path_layout.addWidget(path_label)
        layout.addWidget(path_group)

        name_group = QGroupBox("受信用データ名")
        name_layout = QVBoxLayout(name_group)
        name_layout.setContentsMargins(5, 5, 5, 5)
        self.name_entry = QLineEdit()
        self.name_entry.setFont(QFont("", 12))
        self.name_entry.setText("O")
        self.name_entry.selectAll()
        self.name_entry.setFocus()
        name_layout.addWidget(self.name_entry)
        layout.addWidget(name_group)

        ext_group = QGroupBox("拡張子")
        ext_layout = QHBoxLayout(ext_group)
        ext_layout.setContentsMargins(5, 5, 5, 5)
        self.ext_mc = QRadioButton("メイン(.m)")
        self.ext_mc.setChecked(True)
        self.ext_mc.toggled.connect(lambda c: setattr(self, "ext_name", ".m" if c else self.ext_name))
        ext_layout.addWidget(self.ext_mc)
        self.ext_sub = QRadioButton("サブ(.s)")
        self.ext_sub.toggled.connect(lambda c: setattr(self, "ext_name", ".s" if c else self.ext_name))
        ext_layout.addWidget(self.ext_sub)
        layout.addWidget(ext_group)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        exec_btn = QPushButton("実行")
        exec_btn.setFont(QFont("", 10))
        exec_btn.setMinimumHeight(45)
        exec_btn.clicked.connect(self._execute)
        btn_layout.addWidget(exec_btn)
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.setFont(QFont("", 10))
        cancel_btn.setMinimumHeight(45)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _execute(self):
        name = self.name_entry.text().strip()
        if not name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "エラー", "データ名を入力してください。")
            return

        if not validate_data_name(name):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, "エラー",
                "データ名に無効な文字が含まれています。\n"
                "使用できない文字: \\/:,;\"<>|"
            )
            return

        self.result = self.path + "\\" + name + self.ext_name
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            self._execute()
        else:
            super().keyPressEvent(event)
