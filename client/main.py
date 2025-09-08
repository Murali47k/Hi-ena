import argparse
import socket
import threading
import sys
import os
import time
import hashlib
from core.utils import create_message, parse_message

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

    def connect(self):
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
        try:
            # append newline to help server-side simple framing
            self.sock.sendall((msg_str + "\n").encode("utf-8"))
        except Exception as e:
            print("[ERROR] send failed:", e)

    def _listener_thread(self):
        while self.listening:
            try:
                data = self.sock.recv(4096)
                if not data:
                    print("[INFO] Server closed connection.")
                    self.listening = False
                    break
                text = data.decode("utf-8")
                # handle newline separated packets
                for line in text.splitlines():
                    if not line.strip():
                        continue
                    packet = parse_message(line)
                    ptype = packet.get("type")
                    pdata = packet.get("data", {})
                    if ptype == "auth_result":
                        print("[AUTH]", pdata)
                    elif ptype == "chat":
                        print(f"{pdata.get('from')}: {pdata.get('message')}")
                    elif ptype == "system":
                        print("[SYSTEM]", pdata.get("message"))
                    else:
                        print("[RECV]", packet)
            except Exception as e:
                print("[ERROR] listening:", e)
                self.listening = False
                break

    def close(self):
        self.listening = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.sock = None

def command_host(args):
    client = Client(args.host, args.port)
    if not client.connect():
        return
    password_hash = sha256_hex(args.password)
    payload = create_message("host", {
        "server_name": args.name,
        "password_hash": password_hash,
        "username": args.username or "host"
    })
    client.send(payload)
    # wait for auth_result or timeout
    time.sleep(0.5)
    print("[INFO] You are now hosting. Type chat messages to broadcast. /quit to exit.")
    try:
        while True:
            line = input()
            if line.strip().lower() == "/quit":
                break
            # send chat messages (JSON chat)
            msg = create_message("chat", {"message": line})
            client.send(msg)
            print(f"you : {line}")
    finally:
        client.close()

def command_join(args):
    client = Client(args.host, args.port)
    if not client.connect():
        return
    password_hash = sha256_hex(args.password)
    payload = create_message("join", {
        "server_name": args.name,
        "password_hash": password_hash,
        "username": args.username or "guest"
    })
    client.send(payload)
    # small wait for response
    time.sleep(0.5)
    print("[INFO] Joined (if auth succeeded). Type chat messages to send. /quit to exit.")
    try:
        while True:
            line = input()
            if line.strip().lower() == "/quit":
                break
            msg = create_message("chat", {"message": line})
            client.send(msg)
            print(f"you : {line}")
    finally:
        client.close()

def main():
    parser = argparse.ArgumentParser(prog="lanchat-client", description="LAN chat client - Phase1")
    sub = parser.add_subparsers(dest="command", required=True)

    hostp = sub.add_parser("host-server", help="Host a new server/room")
    hostp.add_argument("--name", required=True, help="Server name to create")
    hostp.add_argument("--password", required=True, help="Password for the server (will be SHA256 hashed client-side)")
    hostp.add_argument("--username", required=False, help="Display name for host")
    hostp.add_argument("--host", default=DEFAULT_HOST, help="Server host to connect to (defaults to localhost)")
    hostp.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port (defaults to 5555)")

    joinp = sub.add_parser("join-server", help="Join an existing server/room")
    joinp.add_argument("--name", required=True, help="Server name to join")
    joinp.add_argument("--password", required=True, help="Password for server (will be SHA256 hashed client-side)")
    joinp.add_argument("--username", required=False, help="Your display name")
    joinp.add_argument("--host", default=DEFAULT_HOST, help="Server host to connect to (defaults to localhost)")
    joinp.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port (defaults to 5555)")

    args = parser.parse_args()

    if args.command == "host-server":
        command_host(args)
    elif args.command == "join-server":
        command_join(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()