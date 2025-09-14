import argparse
import socket
import threading
import sys
import os
import time
import hashlib

# add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.utils import create_message, parse_message
from gui.app_state import app_state  

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5555


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class Client:
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        self.host = host
        self.port = port
        self.sock = None
        self.listening = False
        self.username = None  # store username for GUI tagging

    def connect(self):
        """Connect to the server, start listener thread."""
        if self.sock:
            return True
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.listening = True
            threading.Thread(target=self._listener_thread, daemon=True).start()
            return True
        except ConnectionRefusedError:
            print("[ERROR] Could not connect to server.")
            return False

    def send(self, msg_str):
        """Send a raw JSON message to the server."""
        try:
            self.sock.sendall((msg_str + "\n").encode("utf-8"))
        except Exception as e:
            print("[ERROR] send failed:", e)

    def _listener_thread(self):
        """Listen for messages from the server and handle them."""
        while self.listening:
            try:
                data = self.sock.recv(4096)
                if not data:
                    print("[INFO] Server closed connection.")
                    self.listening = False
                    break

                text = data.decode("utf-8")
                for line in text.splitlines():
                    if not line.strip():
                        continue
                    packet = parse_message(line)
                    self._handle_incoming(packet)

            except Exception as e:
                print("[ERROR] listening:", e)
                self.listening = False
                break

    def _handle_incoming(self, packet):
        """Handles incoming packets and updates GUI state."""
        ptype = packet.get("type")
        pdata = packet.get("data", {})

        if ptype == "auth_result":
            print("[AUTH]", pdata)

        elif ptype == "chat":
            sender = pdata.get("from", "unknown")
            msg = pdata.get("message", "")
            print(f"{sender}: {msg}")
            # ✅ Update GUI state
            app_state.add_message(sender, msg)

        elif ptype == "system":
            sys_msg = pdata.get("message", "")
            print("[SYSTEM]", sys_msg)
            app_state.add_message("SYSTEM", sys_msg)

        elif ptype == "clients":
            # server sends updated client list
            app_state.set_clients(pdata.get("list", []))

        else:
            print("[RECV]", packet)

    def close(self):
        self.listening = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.sock = None


def command_host(args, use_gui=False):
    client = Client(args.host, args.port)
    client.username = args.username or "host"
    if not client.connect():
        return

    password_hash = sha256_hex(args.password)
    payload = create_message("host", {
        "server_name": args.name,
        "password_hash": password_hash,
        "username": client.username
    })
    client.send(payload)

    time.sleep(0.5)

    if use_gui:
        from gui.main import run_gui
        run_gui(client)
        return

    print("[INFO] You are now hosting. Type chat messages to broadcast. /quit to exit.")
    try:
        while True:
            line = input()
            if line.strip().lower() == "/quit":
                break
            msg = create_message("chat", {"message": line})
            client.send(msg)
            app_state.add_message(client.username, line)
    finally:
        client.close()


def command_join(args, use_gui=False):
    client = Client(args.host, args.port)
    client.username = args.username or "guest"
    if not client.connect():
        return

    password_hash = sha256_hex(args.password)
    payload = create_message("join", {
        "server_name": args.name,
        "password_hash": password_hash,
        "username": client.username
    })
    client.send(payload)

    time.sleep(0.5)

    if use_gui:
        from gui.main import run_gui
        run_gui(client)
        return

    print("[INFO] Joined (if auth succeeded). Type chat messages to send. /quit to exit.")
    try:
        while True:
            line = input()
            if line.strip().lower() == "/quit":
                break
            msg = create_message("chat", {"message": line})
            client.send(msg)
            app_state.add_message(client.username, line)
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(prog="lanchat-client", description="LAN chat client - Phase1")
    sub = parser.add_subparsers(dest="command", required=True)

    hostp = sub.add_parser("host-server", help="Host a new server/room")
    hostp.add_argument("--name", required=True)
    hostp.add_argument("--password", required=True)
    hostp.add_argument("--username", required=False)
    hostp.add_argument("--host", default=DEFAULT_HOST)
    hostp.add_argument("--port", type=int, default=DEFAULT_PORT)
    hostp.add_argument("--gui", action="store_true", help="Launch GUI client instead of CLI")

    joinp = sub.add_parser("join-server", help="Join an existing server/room")
    joinp.add_argument("--name", required=True)
    joinp.add_argument("--password", required=True)
    joinp.add_argument("--username", required=False)
    joinp.add_argument("--host", default=DEFAULT_HOST)
    joinp.add_argument("--port", type=int, default=DEFAULT_PORT)
    joinp.add_argument("--gui", action="store_true", help="Launch GUI client instead of CLI")

    args = parser.parse_args()

    if args.command == "host-server":
        command_host(args, use_gui=args.gui)
    elif args.command == "join-server":
        command_join(args, use_gui=args.gui)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
