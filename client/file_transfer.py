import os
import socket

CHUNK_SIZE = 64 * 1024  # 64KB per chunk

def send_file(sock, filepath):
    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)

    # Send metadata first
    header = f"FILE:{filename}:{filesize}"
    sock.sendall(header.encode() + b"\n")

    # Send file in chunks
    with open(filepath, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sock.sendall(chunk)

def receive_file(sock, save_dir="Hi-ena dowloads"):
    os.makedirs(save_dir, exist_ok=True)

    # Read header
    header = sock.recv(1024).decode().strip()
    if not header.startswith("FILE:"):
        return

    _, filename, filesize = header.split(":")
    filesize = int(filesize)
    filepath = os.path.join(save_dir, filename)

    received = 0
    with open(filepath, "wb") as f:
        while received < filesize:
            chunk = sock.recv(CHUNK_SIZE)
            if not chunk:
                break
            f.write(chunk)
            received += len(chunk)
