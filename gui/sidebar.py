from PyQt5.QtWidgets import QWidget, QListWidget, QVBoxLayout
from gui.app_state import app_state

class Sidebar(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #2F3136; color: white;")
        layout = QVBoxLayout()
        self.clients_list = QListWidget()
        layout.addWidget(self.clients_list)
        self.setLayout(layout)

    def refresh(self):
        self.clients_list.clear()
        for client in app_state.clients:
            self.clients_list.addItem(client)
