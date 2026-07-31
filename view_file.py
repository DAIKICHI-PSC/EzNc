from PySide6.QtWidgets import (QDialog, QVBoxLayout, QGroupBox, QTextEdit,
    QHBoxLayout, QPushButton)
from PySide6.QtGui import QFont


class ViewFile(QDialog):
    def __init__(self, parent, content):
        super().__init__(parent)
        self.setWindowTitle("EzNC - ファイル確認")
        self.resize(1024, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        group = QGroupBox("ファイル内容")
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(5, 5, 5, 5)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        font = QFont("Fixedsys Excelsior 3.01", 18)
        if not font.exactMatch():
            font = QFont("MS Gothic", 18)
        self.text.setFont(font)
        self.text.setPlainText(content)
        group_layout.addWidget(self.text)
        layout.addWidget(group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("戻る")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
