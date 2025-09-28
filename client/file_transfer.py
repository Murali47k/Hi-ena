import os
import base64
from core.utils import create_message

CHUNK_SIZE = 64 * 1024  # 64KB

def send_file_offer(client, filepath, target="all"):
    """Send metadata about a file to other clients via server."""
    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)
    meta = {
        "filename": filename,
        "filesize": filesize,
        "target": target,
    }
    client.send(create_message("file_offer", meta))


def send_file_chunks(client, filepath, target="all"):
    """Read file and send in chunks."""
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            encoded = base64.b64encode(chunk).decode("utf-8")
            packet = {
                "filename": filename,
                "chunk": encoded,
                "target": target,
            }
            client.send(create_message("file_chunk", packet))

    # signal completion
    client.send(create_message("file_complete", {"filename": filename, "target": target}))


def receive_file_chunk(state, packet, save_dir="Hi-ena downloads"):
    """
    Collect file chunks into memory/disk.
    `state` should be a dict shared by client to track active downloads.
    """
    os.makedirs(save_dir, exist_ok=True)

    fname = packet["filename"]
    data = base64.b64decode(packet["chunk"])
    path = os.path.join(save_dir, fname)

    if fname not in state:
        # Ensure unique filename
        base, ext = os.path.splitext(fname)
        counter = 1
        while os.path.exists(path):
            path = os.path.join(save_dir, f"{base}_{counter}{ext}")
            counter += 1
        state[fname] = open(path, "wb")

    state[fname].write(data)


def finalize_file(state, packet, save_dir="Hi-ena downloads"):
    """Close file after all chunks are received and return saved path."""
    fname = packet["filename"]
    path = os.path.join(save_dir, fname)
    if fname in state:
        state[fname].close()
        del state[fname]
        print(f"[FILE SAVED] {fname}")
    return path
