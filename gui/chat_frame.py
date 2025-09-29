# gui/chat_frame.py
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QScrollArea, QLineEdit, QPushButton,
    QHBoxLayout, QApplication, QTextEdit, QFileDialog, QProgressBar
)
from PyQt5.QtCore import Qt
from gui.app_state import app_state
import os
from client.file_transfer import FileSenderThread, file_receiver, DownloadThread

script_dir = os.path.dirname(os.path.abspath(__file__))
style_path = os.path.join(script_dir, "assets", "chatframe.qss")


class ChatBubble(QWidget):
    """Individual chat bubble widget with sender name, left/right alignment, and copy button."""
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

        # Copy button (always visible)
        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.setFixedSize(60, 20)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #4ECDC4;
                color: #1F2A38;
                border-radius: 6px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #FF6B6B;
                color: white;
            }
        """)
        self.copy_btn.clicked.connect(self._copy_text)
        layout.addWidget(self.copy_btn, alignment=Qt.AlignRight if sender_name == "me" else Qt.AlignLeft)

        # Set property for right/left styling via QSS
        self.setProperty("right", "true" if sender_name == "me" else "false")
        layout.setAlignment(Qt.AlignLeft if sender_name != "me" else Qt.AlignRight)
        self.setLayout(layout)

    def _copy_text(self):
        QApplication.clipboard().setText(self.text)


class FileBubble(ChatBubble):
    """Special bubble for file messages with always visible Download button + progress bar on demand."""
    def __init__(self, filename, filesize, sender_name="me", parent=None, client=None):
        text = f"📄 {filename} ({filesize // 1024} KB)"
        super().__init__(text, sender_name=sender_name, parent=parent)

        self.filename = filename
        self.filesize = filesize
        self.client = client
        self.download_thread = None

        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.layout().addWidget(self.progress_bar)

        # Download button (always visible)
        self.download_btn = QPushButton("⬇ Download", self)
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
        self.layout().addWidget(self.download_btn, alignment=Qt.AlignRight)

    def _on_download_clicked(self):
        """Download file via QThread and show progress bar."""
        src = file_receiver.find_saved_path(self.filename)
        if not src:
            print(f"[DOWNLOAD ERROR] file not found: {self.filename}")
            return

        dst_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.progress_bar.show()
        self.download_thread = DownloadThread(src, dst_dir=dst_dir)
        self.download_thread.progress.connect(lambda pct: self.update_progress(pct))
        self.download_thread.finished.connect(lambda dst: print(f"[DOWNLOADED] {dst}"))
        self.download_thread.error.connect(lambda e: print(f"[DOWNLOAD ERROR] {e}"))
        self.download_thread.start()

    def update_progress(self, pct):
        self.progress_bar.setValue(pct)


class ChatFrame(QWidget):
    """Main chat frame with scrollable bubbles and input field."""
    def __init__(self, send_callback, client=None):
        super().__init__()
        main_layout = QVBoxLayout()
        with open(style_path, "r") as f:
            self.setStyleSheet(f.read())

        # Use the shared receiver instance
        self.client = app_state.get_client()
        self.file_receiver = file_receiver
        self.file_receiver.progress.connect(self._on_receive_progress)

        # Scroll area
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

        self._file_bubbles = {}

    def refresh_messages(self):
        """Refresh chat bubbles from app_state messages."""
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self._file_bubbles.clear()

        for username, message in app_state.messages:
            sender_type = "me" if username == app_state.get_username() else username

            if isinstance(message, dict) and message.get("type") == "file":
                filename = message["filename"]
                filesize = message["filesize"]
                bubble = FileBubble(filename, filesize, sender_name=sender_type, client=self.client)
                self._file_bubbles[filename] = bubble
            else:
                bubble = ChatBubble(message, sender_name=sender_type)

            self.scroll_layout.addWidget(bubble)

        self._maybe_autoscroll()

    def _maybe_autoscroll(self):
        """Auto-scroll only if near bottom (<60 px)."""
        scrollbar = self.scroll_area.verticalScrollBar()
        if scrollbar.maximum() - scrollbar.value() <= 60:
            scrollbar.setValue(scrollbar.maximum())

    def _on_send(self):
        text = self.entry.toPlainText().strip()
        if text:
            self.send_callback(text)
            self.entry.clear()
            self.refresh_messages()

    def _on_send_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select File to Send")
        if not filepath:
            return

        sender = app_state.get_username() or "me"
        filesize = os.path.getsize(filepath)
        filename = os.path.basename(filepath)

        app_state.messages.append((sender, {"type": "file", "filename": filename, "filesize": filesize}))
        self.refresh_messages()

        client = self.client
        if client:
            self.file_thread = FileSenderThread(client, filepath)
            if filename in self._file_bubbles:
                fn = filename
                self.file_thread.progress.connect(lambda pct, f=fn: self._file_bubbles[f].update_progress(pct))
            self.file_thread.finished.connect(lambda f: print(f"[FILE SENT] {f}"))
            self.file_thread.error.connect(lambda e: print(f"[FILE SEND ERROR] {e}"))
            self.file_thread.start()

    def _on_receive_progress(self, saved_basename, pct):
        bubble = self._file_bubbles.get(saved_basename)
        if bubble:
            bubble.update_progress(pct)

    def _adjust_textedit_height(self):
        doc_height = self.entry.document().size().height()
        new_height = int(doc_height + 10)
        self.entry.setFixedHeight(min(new_height, 120))
