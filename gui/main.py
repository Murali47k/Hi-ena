import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import pyqtSignal, QObject, QTimer
from gui.topbar import TopBar
from gui.sidebar import Sidebar
from gui.chat_frame import ChatFrame
from gui.app_state import app_state
from core.utils import create_message

# 🔗 Thread-safe bridge between Client threads and GUI
class GuiBridge(QObject):
    message_received = pyqtSignal(str, str)   # sender, message
    system_message = pyqtSignal(str)
    client_list_updated = pyqtSignal(list)

# single global instance
gui_bridge = GuiBridge()


class MainWindow(QWidget):
    def __init__(self, client):
        super().__init__()
        self.client = client
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

        # ✅ Connect signals to UI updates
        gui_bridge.message_received.connect(self.on_message_received)
        gui_bridge.system_message.connect(self.on_system_message)
        gui_bridge.client_list_updated.connect(self.on_client_list_updated)

        # ✅ Optional periodic refresh (if needed)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_ui)
        self.timer.start(1000)

    def send_message_to_server(self, msg):
        # send message to server safely
        if self.client:
            payload = {"message": msg}
            self.client.send(create_message("chat", payload))
            app_state.add_message(self.client.username, msg)
            self.chat_frame.refresh_messages()

    # --- Signal Handlers (run on main GUI thread) ---
    def on_message_received(self, sender, msg):
        app_state.add_message(sender, msg)
        self.chat_frame.refresh_messages()

    def on_system_message(self, msg):
        app_state.add_message("SYSTEM", msg)
        self.chat_frame.refresh_messages()

    def on_client_list_updated(self, clients):
        app_state.set_clients(clients)
        self.sidebar.refresh()

    def refresh_ui(self):
        # If you still want periodic refresh (UI always up-to-date)
        self.sidebar.refresh()
        self.chat_frame.refresh_messages()


def run_gui(client):
    app = QApplication(sys.argv)
    window = MainWindow(client)
    window.show()
    sys.exit(app.exec_())
