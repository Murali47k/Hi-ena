from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QScrollArea, QLineEdit, QPushButton,
    QHBoxLayout, QApplication, QMenu, QTextEdit, QFileDialog
)
from PyQt5.QtCore import Qt
from gui.app_state import app_state
import os
from client import file_transfer

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

        # 🔹 Apply custom style to Copy menu
        menu.setStyleSheet("""
            QMenu {
                background-color: #1F2A38;     /* Dark background to match chat */
                color: white;                  /* White text */
                border: 1px solid #FF6B6B;     /* Coral border for highlight */
                padding: 4px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 6px 12px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: #4ECDC4;     /* Aqua highlight */
                color: #1F2A38;                /* Dark text when selected */
            }
        """)
        copy_action = menu.addAction("📋 Copy")
        action = menu.exec_(event.globalPos())
        if action == copy_action:
            QApplication.clipboard().setText(self.text)


class FileBubble(ChatBubble):
    """Special bubble for file messages with hover-based Download button."""
    def __init__(self, filename, filesize, sender_name="me", parent=None, client=None):
        text = f"📄 {filename} ({filesize // 1024} KB)"
        super().__init__(text, sender_name=sender_name, parent=parent)

        self.filename = filename
        self.filesize = filesize
        self.client = client

        # Download button
        self.download_btn = QPushButton("⬇ Download", self)
        self.download_btn.hide()
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #4ECDC4;
                color: #1F2A38;
                border-radius: 10px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #FF6B6B;
                color: white;
            }
        """)
        self.download_btn.clicked.connect(self._on_download_clicked)

        layout = self.layout()
        layout.addWidget(self.download_btn, alignment=Qt.AlignRight)

    def enterEvent(self, event):
        self.download_btn.show()

    def leaveEvent(self, event):
        self.download_btn.hide()

    def _on_download_clicked(self):
        """Trigger file_request when Download is clicked."""
        if self.client:
            self.client.send({
                "type": "file_request",
                "data": {"filename": self.filename}
            })
            print(f"[REQUESTED FILE] {self.filename}")


class ChatFrame(QWidget):
    """Main chat frame with scrollable bubbles and input field."""
    def __init__(self, send_callback, client=None):
        super().__init__()
        main_layout = QVBoxLayout()
        with open(style_path, "r") as f:
            self.setStyleSheet(f.read())

        self.client = app_state.get_client()

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
        self.entry = QTextEdit()
        self.entry.setFixedHeight(30)
        self.entry.setMinimumHeight(30)
        self.entry.setMaximumHeight(120)
        self.entry.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.entry.setWordWrapMode(True)

        # Auto-resize as user types
        self.entry.textChanged.connect(self._adjust_textedit_height)

        send_button = QPushButton("Send")
        send_button.clicked.connect(self._on_send)

        file_button = QPushButton("Send File")
        file_button.clicked.connect(self._on_send_file)

        input_layout.addWidget(self.entry)
        input_layout.addWidget(send_button)
        input_layout.addWidget(file_button)
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

        # Add new messages as ChatBubble or FileBubble
        for username, message in app_state.messages:
            sender_type = "me" if username == app_state.get_username() else username

            if isinstance(message, dict) and message.get("type") == "file":
                filename = message["filename"]
                filesize = message["filesize"]
                bubble = FileBubble(filename, filesize, sender_name=sender_type, client=self.client)
            else:
                bubble = ChatBubble(message, sender_name=sender_type)

            self.scroll_layout.addWidget(bubble)

        # Auto scroll to bottom
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def _on_send(self):
        """Send text message and refresh chat."""
        text = self.entry.toPlainText().strip()
        if text:
            self.send_callback(text)
            self.entry.clear()
            self.refresh_messages()

    def _on_send_file(self):
        """Pick a file and send it in chunks."""
        filepath, _ = QFileDialog.getOpenFileName(self, "Select File to Send")
        if filepath:
            filesize = os.path.getsize(filepath)
            filename = os.path.basename(filepath)
            sender = app_state.get_username() or "me"

            # Store message in app_state for GUI
            app_state.messages.append((
                sender,
                {"type": "file", "filename": filename, "filesize": filesize}
            ))

            # Actually send via file_transfer
            file_transfer.send_file_offer(self.client, filepath)
            file_transfer.send_file_chunks(self.client, filepath)

            self.refresh_messages()

    def _adjust_textedit_height(self):
        doc_height = self.entry.document().size().height()
        new_height = int(doc_height + 10)
        if new_height < 120:
            self.entry.setFixedHeight(new_height)
        else:
            self.entry.setFixedHeight(120)
