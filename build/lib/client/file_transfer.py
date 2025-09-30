# client/file_transfer.py
import os
import base64
import shutil
from PyQt5.QtCore import QThread, pyqtSignal, QObject
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

            # 1) Send file metadata (offer)
            meta = {"filename": filename, "filesize": filesize, "target": self.target}
            self.client.send(create_message("file_offer", meta))

            # 2) Send file data in base64 chunks; include filesize so receiver always knows total
            sent_bytes = 0
            with open(self.filepath, "rb") as f:
                while chunk := f.read(CHUNK_SIZE):
                    encoded = base64.b64encode(chunk).decode("utf-8")
                    packet = {"filename": filename, "chunk": encoded, "filesize": filesize, "target": self.target}
                    self.client.send(create_message("file_chunk", packet))

                    sent_bytes += len(chunk)
                    pct = int((sent_bytes / filesize) * 100) if filesize > 0 else 100
                    self.progress.emit(pct)

            # 3) Signal completion
            self.client.send(create_message("file_complete", {"filename": filename, "target": self.target}))
            self.finished.emit(filename)

        except Exception as e:
            self.error.emit(str(e))


class DownloadThread(QThread):
    """Copy a saved file from hidden folder into ~/Downloads (with progress)."""
    progress = pyqtSignal(int)    # percent
    finished = pyqtSignal(str)    # destination path
    error = pyqtSignal(str)

    def __init__(self, src_path, dst_dir=None):
        super().__init__()
        self.src_path = src_path
        self.dst_dir = dst_dir or os.path.join(os.path.expanduser("~"), "Downloads")

    def run(self):
        try:
            if not os.path.exists(self.src_path):
                raise FileNotFoundError(f"Source not found: {self.src_path}")

            os.makedirs(self.dst_dir, exist_ok=True)
            total = os.path.getsize(self.src_path)
            base, ext = os.path.splitext(os.path.basename(self.src_path))
            dst = os.path.join(self.dst_dir, os.path.basename(self.src_path))

            # ensure unique name in destination
            counter = 1
            while os.path.exists(dst):
                dst = os.path.join(self.dst_dir, f"{base}_{counter}{ext}")
                counter += 1

            copied = 0
            with open(self.src_path, "rb") as sf, open(dst, "wb") as df:
                while chunk := sf.read(CHUNK_SIZE):
                    df.write(chunk)
                    copied += len(chunk)
                    pct = int((copied / total) * 100) if total > 0 else 100
                    self.progress.emit(pct)

            self.finished.emit(dst)
        except Exception as e:
            self.error.emit(str(e))


class FileReceiver(QObject):
    """
    Manages incoming file offers/chunks/completion and saves them under a hidden folder:
    ~/.Hiena-Downloads

    Emits progress as (saved_basename, percent).
    """
    progress = pyqtSignal(str, int)  # saved_basename, percent

    def __init__(self, save_dir=None):
        super().__init__()
        if save_dir is None:
            save_dir = os.path.join(os.path.expanduser("~"), ".Hiena-Downloads")
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

        # mapping: (sender, orig_filename) -> { 'fh': filehandle, 'total': int, 'received': int, 'saved_basename': str, 'path': str }
        self._downloads = {}

    def handle_offer(self, packet):
        """
        Prepare a file on disk for incoming transfer. Packet should contain:
        {'from': sender, 'filename': filename, 'filesize': filesize}
        """
        sender = packet.get("from", "unknown")
        fname = packet.get("filename")
        total_bytes = packet.get("filesize", 0)
        if not fname:
            return

        key = (sender, fname)
        if key in self._downloads:
            # already prepared (duplicate offer)
            return

        base, ext = os.path.splitext(fname)
        saved_basename = fname
        path = os.path.join(self.save_dir, saved_basename)
        counter = 1
        while os.path.exists(path):
            saved_basename = f"{base}_{counter}{ext}"
            path = os.path.join(self.save_dir, saved_basename)
            counter += 1

        fh = open(path, "wb")
        self._downloads[key] = {"fh": fh, "total": total_bytes, "received": 0, "saved_basename": saved_basename, "path": path}
        # emit 0% initially
        self.progress.emit(saved_basename, 0)

    def receive_chunk(self, packet):
        """
        Packet expected to contain at least: {'from': sender, 'filename': fname, 'chunk': base64_str, 'filesize': maybe}
        """
        sender = packet.get("from", "unknown")
        fname = packet.get("filename")
        if not fname:
            return

        key = (sender, fname)

        # if offer was missed, create a slot using filesize from packet (race)
        if key not in self._downloads:
            total_bytes = packet.get("filesize", 0)
            self.handle_offer({'from': sender, 'filename': fname, 'filesize': total_bytes})

        entry = self._downloads.get(key)
        if entry is None:
            return

        try:
            data = base64.b64decode(packet.get("chunk", ""))
        except Exception:
            data = b""

        fh = entry["fh"]
        fh.write(data)
        entry["received"] += len(data)

        total = entry.get("total", 0)
        pct = int((entry["received"] / total) * 100) if total > 0 else 0
        self.progress.emit(entry["saved_basename"], pct)

    def finalize_file(self, packet):
        """
        Close file and return saved path. Packet should contain {'from': sender, 'filename': fname}
        """
        sender = packet.get("from", "unknown")
        fname = packet.get("filename")
        if not fname:
            return None

        key = (sender, fname)
        entry = self._downloads.pop(key, None)
        if not entry:
            return None
        try:
            fh = entry["fh"]
            path = entry["path"]
            fh.close()
            print(f"[FILE SAVED] {path}")
            return path
        except Exception:
            return None

    def find_saved_path(self, saved_basename):
        """
        Return full path under save_dir for given saved_basename, or None.
        """
        candidate = os.path.join(self.save_dir, saved_basename)
        if os.path.exists(candidate):
            return candidate
        return None


# Module-level singleton shared by GUI and client listener
file_receiver = FileReceiver()
