from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt

class TopBar(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        self.setStyleSheet("background-color: #202225;")
        self.label = QLabel("HI-ENA Chat")
        self.label.setStyleSheet("color: white; font-weight: bold; font-size: 16px;")
        layout.addWidget(self.label, alignment=Qt.AlignLeft)
        self.setLayout(layout)
