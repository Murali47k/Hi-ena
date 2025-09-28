import os
import base64
from PyQt5.QtCore import QThread, pyqtSignal , QObject
from core.utils import create_message

CHUNK_SIZE = 64 * 1024  # 64 KB

class FileSenderThread(QThread):
    """Send a file in chunks via a connected client."""
    progress = pyqtSignal(int)      # emits percentage
    finished = pyqtSignal(str)      # emits filename when done
    error = pyqtSignal(str)         # emits error string

    def __init__(self, client, filepath, target="all"):
        super().__init__()
        self.client = client
        self.filepath = filepath
        self.target = target

    def run(self):
        try:
            filesize = os.path.getsize(self.filepath)
            filename = os.path.basename(self.filepath)

            # Send file metadata
            meta = {"filename": filename, "filesize": filesize, "target": self.target}
            self.client.send(create_message("file_offer", meta))

            sent_bytes = 0
            with open(self.filepath, "rb") as f:
                while chunk := f.read(CHUNK_SIZE):
                    encoded = base64.b64encode(chunk).decode("utf-8")
                    packet = {"filename": filename, "chunk": encoded, "target": self.target}
                    self.client.send(create_message("file_chunk", packet))

                    sent_bytes += len(chunk)
                    pct = int((sent_bytes / filesize) * 100)
                    self.progress.emit(pct)

            # Signal completion
            self.client.send(create_message("file_complete", {"filename": filename, "target": self.target}))
            self.finished.emit(filename)

        except Exception as e:
            self.error.emit(str(e))

class FileReceiver(QObject):
    """Manages incoming file chunks and saves them to disk with progress."""
    progress = pyqtSignal(str, int)  # filename, percent

    def __init__(self, save_dir="Hi-ena downloads"):
        super().__init__()
        self._downloads = {}  # {filename: (file_handle, total_bytes, received_bytes)}
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)

    def receive_chunk(self, packet):
        fname = packet["filename"]
        data = base64.b64decode(packet["chunk"])
        path = os.path.join(self.save_dir, fname)

        if fname not in self._downloads:
            base, ext = os.path.splitext(fname)
            counter = 1
            while os.path.exists(path):
                path = os.path.join(self.save_dir, f"{base}_{counter}{ext}")
                counter += 1
            f_handle = open(path, "wb")
            total_bytes = packet.get("filesize", 0)
            self._downloads[fname] = [f_handle, total_bytes, 0]

        f_handle, total_bytes, received_bytes = self._downloads[fname]
        f_handle.write(data)
        received_bytes += len(data)
        self._downloads[fname][2] = received_bytes

        # emit progress
        pct = int((received_bytes / total_bytes) * 100) if total_bytes > 0 else 0
        self.progress.emit(fname, pct)

    def finalize_file(self, packet):
        fname = packet["filename"]
        if fname in self._downloads:
            f_handle, _, _ = self._downloads[fname]
            path = f_handle.name
            f_handle.close()
            del self._downloads[fname]
            print(f"[FILE SAVED] {path}")
            return path
        return None