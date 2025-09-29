# gui/chat_frame.py
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QScrollArea, QLineEdit, QPushButton,
    QHBoxLayout, QApplication, QMenu, QTextEdit, QFileDialog, QProgressBar
)
from PyQt5.QtCore import Qt
from gui.app_state import app_state
import os
from client.file_transfer import FileSenderThread, file_receiver, DownloadThread

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
        menu.setStyleSheet("""
            QMenu {
                background-color: #1F2A38;
                color: white;
                border: 1px solid #FF6B6B;
                padding: 4px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 6px 12px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: #4ECDC4;
                color: #1F2A38;
            }
        """)
        copy_action = menu.addAction("📋 Copy")
        action = menu.exec_(event.globalPos())
        if action == copy_action:
            QApplication.clipboard().setText(self.text)


class FileBubble(ChatBubble):
    """Special bubble for file messages with hover Download button + progress bar."""
    def __init__(self, filename, filesize, sender_name="me", parent=None, client=None):
        text = f"📄 {filename} ({filesize // 1024} KB)"
        super().__init__(text, sender_name=sender_name, parent=parent)

        self.filename = filename
        self.filesize = filesize
        self.client = client
        self.download_thread = None

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()

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
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.download_btn, alignment=Qt.AlignRight)

    def enterEvent(self, event):
        self.download_btn.show()

    def leaveEvent(self, event):
        self.download_btn.hide()

    def _on_download_clicked(self):
        """
        Download: copy file from hidden save-dir (~/.Hiena-Downloads) to ~/Downloads
        (handled in a QThread to avoid blocking UI).
        """
        # find source path in the shared receiver save folder
        src = file_receiver.find_saved_path(self.filename)
        if not src:
            print(f"[DOWNLOAD ERROR] file not found in hidden store: {self.filename}")
            # optionally: request from server (not implemented currently)
            return

        dst_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.download_thread = DownloadThread(src, dst_dir=dst_dir)
        self.download_thread.progress.connect(lambda pct: self.update_progress(pct))
        self.download_thread.finished.connect(lambda dst: print(f"[DOWNLOADED] {dst}"))
        self.download_thread.error.connect(lambda e: print(f"[DOWNLOAD ERROR] {e}"))
        self.download_thread.start()

    def update_progress(self, pct):
        self.progress_bar.show()
        self.progress_bar.setValue(pct)


class ChatFrame(QWidget):
    """Main chat frame with scrollable bubbles and input field."""
    def __init__(self, send_callback, client=None):
        super().__init__()
        main_layout = QVBoxLayout()
        with open(style_path, "r") as f:
            self.setStyleSheet(f.read())

        # Use the shared receiver instance (so network events reach GUI)
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

        # map displayed filename -> bubble (for quick UI progress updates)
        self._file_bubbles = {}

    def refresh_messages(self):
        """Refresh chat bubbles from app_state messages."""
        # Clear existing widgets
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self._file_bubbles.clear()

        # Recreate bubbles
        for username, message in app_state.messages:
            sender_type = "me" if username == app_state.get_username() else username

            if isinstance(message, dict) and message.get("type") == "file":
                filename = message["filename"]
                filesize = message["filesize"]
                bubble = FileBubble(filename, filesize, sender_name=sender_type, client=self.client)
                # store by the displayed filename (this matches FileReceiver.saved_basename)
                self._file_bubbles[filename] = bubble
            else:
                bubble = ChatBubble(message, sender_name=sender_type)

            self.scroll_layout.addWidget(bubble)

        # Scroll to bottom
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

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

        # Add file message to GUI (sender's own bubble)
        app_state.messages.append((sender, {"type": "file", "filename": filename, "filesize": filesize}))
        self.refresh_messages()

        # Send file via QThread with progress
        client = self.client
        if client:
            self.file_thread = FileSenderThread(client, filepath)
            # attach progress updates to the local sender bubble (if present)
            if filename in self._file_bubbles:
                # capture filename in default arg to avoid late-binding issues
                fn = filename
                self.file_thread.progress.connect(lambda pct, f=fn: self._file_bubbles[f].update_progress(pct))
            self.file_thread.finished.connect(lambda f: print(f"[FILE SENT] {f}"))
            self.file_thread.error.connect(lambda e: print(f"[FILE SEND ERROR] {e}"))
            self.file_thread.start()

    def _on_receive_progress(self, saved_basename, pct):
        # Update any bubble that matches the saved basename
        bubble = self._file_bubbles.get(saved_basename)
        if bubble:
            bubble.update_progress(pct)

    def _adjust_textedit_height(self):
        doc_height = self.entry.document().size().height()
        new_height = int(doc_height + 10)
        self.entry.setFixedHeight(min(new_height, 120))
