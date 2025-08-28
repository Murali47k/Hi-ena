# server/main.py
import socket
import threading
import traceback

from core.utils import create_message, parse_message
from server.auth import AuthManager

HOST = "0.0.0.0"
PORT = 5555

# global structures
clients_lock = threading.Lock()
# List of dicts: {"conn": socket, "addr": (ip,port), "username": str or None, "server_name": str or None}
connected_clients = []

auth_mgr = AuthManager()

def send_json(conn, obj_str):
    """Send JSON (string) over socket; add newline delimiter for naive framing."""
    try:
        conn.sendall((obj_str + "\n").encode("utf-8"))
    except Exception:
        # let caller handle removal
        raise

def recv_full(conn):
    """
    Simple receiver for Phase 1: read available bytes and split by newline.
    We'll return the raw string without newline. This assumes each message is sendall'd
    as a single JSON string with newline appended (see send_json).
    """
    try:
        data = conn.recv(4096)
        if not data:
            return None
        return data.decode("utf-8").strip()
    except Exception:
        return None

def broadcast_to_server(server_name, sender_username, text):
    """Broadcast a 'chat' message to all connected clients that belong to server_name."""
    with clients_lock:
        to_remove = []
        for c in connected_clients:
            if c["server_name"] == server_name and c["conn"] is not None:
                try:
                    msg = create_message("chat", {"from": sender_username, "message": text})
                    send_json(c["conn"], msg)
                except Exception:
                    to_remove.append(c)
        for r in to_remove:
            try:
                connected_clients.remove(r)
            except ValueError:
                pass

def handle_client(conn, addr):
    client_entry = {"conn": conn, "addr": addr, "username": None, "server_name": None}
    with clients_lock:
        connected_clients.append(client_entry)

    print(f"[NEW CONNECTION] {addr}")
    try:
        while True:
            raw = recv_full(conn)
            if raw is None:
                break

            # Sometimes multiple messages could be batched; handle simple newline separated
            for line in raw.splitlines():
                if not line.strip():
                    continue
                packet = parse_message(line)
                ptype = packet.get("type")
                pdata = packet.get("data", {})

                if ptype == "host":
                    # register a new server
                    server_name = pdata.get("server_name")
                    password_hash = pdata.get("password_hash")
                    username = pdata.get("username", "host")
                    if not server_name or not password_hash:
                        resp = create_message("auth_result", {"ok": False, "reason": "missing_fields"})
                        send_json(conn, resp)
                        continue

                    ok, msg = auth_mgr.create_server(server_name, password_hash, conn)
                    if ok:
                        client_entry["username"] = username
                        client_entry["server_name"] = server_name
                        resp = create_message("auth_result", {"ok": True, "message": "server_created"})
                        send_json(conn, resp)
                        print(f"[SERVER CREATED] {server_name} by {addr}")
                    else:
                        resp = create_message("auth_result", {"ok": False, "message": msg})
                        send_json(conn, resp)

                elif ptype == "join":
                    # join existing server
                    server_name = pdata.get("server_name")
                    password_hash = pdata.get("password_hash")
                    username = pdata.get("username")
                    if not server_name or not password_hash or not username:
                        resp = create_message("auth_result", {"ok": False, "reason": "missing_fields"})
                        send_json(conn, resp)
                        continue

                    ok, msg = auth_mgr.verify_join(server_name, password_hash, username)
                    if ok:
                        client_entry["username"] = username
                        client_entry["server_name"] = server_name
                        resp = create_message("auth_result", {"ok": True, "message": "joined"})
                        send_json(conn, resp)
                        # inform others
                        broadcast_to_server(server_name, "SYSTEM", f"{username} has joined.")
                        print(f"[JOIN] {username} -> {server_name} from {addr}")
                    else:
                        resp = create_message("auth_result", {"ok": False, "message": msg})
                        send_json(conn, resp)

                elif ptype == "chat":
                    # broadcast to same server
                    server_name = client_entry.get("server_name")
                    username = client_entry.get("username", "unknown")
                    text = pdata.get("message", "")
                    if server_name:
                        broadcast_to_server(server_name, username, text)
                        print(f"[CHAT] ({server_name}) {username}: {text}")
                    else:
                        resp = create_message("system", {"message": "not_in_server"})
                        send_json(conn, resp)

                else:
                    # unknown
                    resp = create_message("system", {"message": "unknown_type"})
                    send_json(conn, resp)

    except Exception as e:
        print("[ERROR] Exception in client handler:", e)
        traceback.print_exc()
    finally:
        # cleanup
        print(f"[DISCONNECT] {addr}")
        try:
            server_name = client_entry.get("server_name")
            username = client_entry.get("username")
            if server_name and username:
                # naive cleanup: remove username from auth manager clients
                auth_mgr.remove_connection(server_name, username)
                broadcast_to_server(server_name, "SYSTEM", f"{username} has left.")
        except Exception:
            pass

        with clients_lock:
            try:
                connected_clients.remove(client_entry)
            except ValueError:
                pass
        try:
            conn.close()
        except Exception:
            pass

def start_server(host=HOST, port=PORT):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen()
    print(f"[SERVER STARTED] Listening on {host}:{port}")

    try:
        while True:
            conn, addr = server_sock.accept()
            thr = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thr.start()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Server shutting down.")
    finally:
        server_sock.close()

if __name__ == "__main__":
    start_server()