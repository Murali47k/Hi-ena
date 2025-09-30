from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt
import os

import importlib.resources as pkg_resources
import gui.assets 

class TopBar(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        with pkg_resources.open_text("gui.assets", "topbar.qss") as f:
            self.setStyleSheet(f.read())
        self.label = QLabel("HI-ENA Connect")
        self.label.setStyleSheet("color: white; font-weight: bold; font-size: 16px;")
        layout.addWidget(self.label, alignment=Qt.AlignLeft)
        self.setLayout(layout)
