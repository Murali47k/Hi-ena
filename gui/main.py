import sys
import threading
import time
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout
from gui.topbar import TopBar
from gui.sidebar import Sidebar
from gui.chat_frame import ChatFrame
from gui.app_state import app_state

from client.main import start_client 

class MainWindow(QWidget):
    def __init__(self, username, server_ip, server_port):
        super().__init__()
        self.setWindowTitle("HI-ENA Chat")
        self.setStyleSheet("background-color: #36393F;")
        self.resize(900, 600)

        main_layout = QVBoxLayout()
        topbar = TopBar()
        main_layout.addWidget(topbar)

        content_layout = QHBoxLayout()

        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(200)
        content_layout.addWidget(self.sidebar)

        self.chat_frame = ChatFrame(self.send_message_to_server)
        content_layout.addWidget(self.chat_frame)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

        threading.Thread(target=self.background_refresh, daemon=True).start()

    def send_message_to_server(self, msg):
        start_client.send_message(msg)
        app_state.add_message("Me", msg)
        self.chat_frame.refresh_messages()

    def background_refresh(self):
        while True:
            self.sidebar.refresh()
            self.chat_frame.refresh_messages()
            time.sleep(1)

def run_gui(username, server_ip, server_port):
    app = QApplication(sys.argv)
    window = MainWindow(username, server_ip, server_port)
    window.show()
    sys.exit(app.exec_())
