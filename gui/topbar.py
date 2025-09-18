from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
style_path = os.path.join(script_dir, "assets", "topbar.qss")

class TopBar(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        with open(style_path, "r") as f:
            self.setStyleSheet(f.read())
        self.label = QLabel("HI-ENA Connect")
        self.label.setStyleSheet("color: white; font-weight: bold; font-size: 16px;")
        layout.addWidget(self.label, alignment=Qt.AlignLeft)
        self.setLayout(layout)
