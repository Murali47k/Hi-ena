# gui/chatframe.py
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QScrollArea, QLineEdit, QPushButton, 
    QHBoxLayout, QApplication, QMenu
)
from PyQt5.QtCore import Qt
from gui.app_state import app_state
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
style_path = os.path.join(script_dir, "assets", "chatframe.qss")

class ChatBubble(QWidget):
    """Individual chat bubble widget with sender name, left/right alignment, and copy-on-double-click."""
    def __init__(self, text, sender_name="me", parent=None):
        super().__init__(parent)
        self.sender_name = sender_name
        self.text = text

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Sender name label
        name_label = QLabel(sender_name if sender_name != "me" else "You")
        name_label.setObjectName("senderName")
        layout.addWidget(name_label, alignment=Qt.AlignLeft if sender_name != "me" else Qt.AlignRight)

        # Message bubble
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.label)

        # Set property for right/left styling via QSS
        self.setProperty("right", "true" if sender_name == "me" else "false")

        layout.setAlignment(Qt.AlignLeft if sender_name != "me" else Qt.AlignRight)
        self.setLayout(layout)

    def mouseDoubleClickEvent(self, event):
        """Show small copy menu on double click."""
        menu = QMenu()
        copy_action = menu.addAction("Copy")
        action = menu.exec_(event.globalPos())
        if action == copy_action:
            QApplication.clipboard().setText(self.text)


class ChatFrame(QWidget):
    """Main chat frame with scrollable bubbles and input field."""
    def __init__(self, send_callback):
        super().__init__()
        main_layout = QVBoxLayout()
        with open(style_path, "r") as f:
            self.setStyleSheet(f.read())

        # Scroll area for messages
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        # Input layout
        input_layout = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Type a message...")
        send_button = QPushButton("Send")
        send_button.clicked.connect(self._on_send)
        input_layout.addWidget(self.entry)
        input_layout.addWidget(send_button)
        main_layout.addLayout(input_layout)

        self.setLayout(main_layout)
        self.send_callback = send_callback

    def refresh_messages(self):
        """Refresh chat bubbles from app_state messages."""
        # Clear old widgets
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Add new messages as ChatBubble
        for username, message in app_state.messages:
            sender_type = "me" if hasattr(self.send_callback, "__self__") and \
                username == self.send_callback.__self__.client.username else username
            bubble = ChatBubble(message, sender_name=sender_type)
            self.scroll_layout.addWidget(bubble)

        # Auto scroll to bottom
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def _on_send(self):
        """Send message and refresh chat."""
        text = self.entry.text().strip()
        if text:
            self.send_callback(text)
            self.entry.clear()
            self.refresh_messages()
