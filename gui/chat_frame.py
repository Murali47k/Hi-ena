from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QHBoxLayout
from gui.app_state import app_state
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
style_path = os.path.join(script_dir, "assets", "chatframe.qss")

class ChatFrame(QWidget):
    def __init__(self, send_callback):
        super().__init__()
        layout = QVBoxLayout()
        with open(style_path, "r") as f:
            self.setStyleSheet(f.read())
        self.messages_view = QTextEdit()
        self.messages_view.setReadOnly(True)
        layout.addWidget(self.messages_view)

        # input row
        input_layout = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Type a message...")
        send_button = QPushButton("Send")
        send_button.clicked.connect(self._on_send)
        input_layout.addWidget(self.entry)
        input_layout.addWidget(send_button)

        layout.addLayout(input_layout)
        self.setLayout(layout)
        self.send_callback = send_callback

    def refresh_messages(self):
        self.messages_view.clear()
        for username, message in app_state.messages:
            self.messages_view.append(f"<b>{username}:</b> {message}")

    def _on_send(self):
        text = self.entry.text().strip()
        if text:
            self.send_callback(text)
            self.entry.clear()
