from PyQt5.QtWidgets import QWidget, QListWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt5.QtCore import Qt
from gui.app_state import app_state
import os

import importlib.resources as pkg_resources
import gui.assets

class Sidebar(QWidget):
    def __init__(self):
        super().__init__()
        
        # self.setStyleSheet("background-color: #2F3136; color: white;")
        layout = QVBoxLayout()
        with pkg_resources.open_text("gui.assets", "sidebar.qss") as f:
            self.setStyleSheet(f.read())
        # --- Online Clients Section ---
        clients_label = QLabel("Online Users")
        # clients_label.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")
        layout.addWidget(clients_label)

        self.clients_list = QListWidget()
        self.clients_list.setFixedHeight(250)  # about 60% of sidebar space
        layout.addWidget(self.clients_list)

        # --- System Logs Section ---
        logs_label = QLabel("System Logs")
        # logs_label.setStyleSheet("font-weight: bold; font-size: 14px; color: white; margin-top: 10px;")
        layout.addWidget(logs_label)

        self.logs_view = QTextEdit()
        self.logs_view.setReadOnly(True)
        # self.logs_view.setStyleSheet("background-color: #232428; color: #B0B3B8; font-size: 12px;")
        layout.addWidget(self.logs_view)

        self.setLayout(layout)

    def refresh(self):
        # Refresh clients
        self.clients_list.clear()
        for client in sorted(set(app_state.clients)):
            self.clients_list.addItem(client)

        # Refresh logs
        self.logs_view.clear()
        for log in app_state.system_logs:
            self.logs_view.append(f"• {log}")
