# server/main.py
import socket
import threading
import traceback

from core.utils import create_message, parse_message
from server.auth import AuthManager
from server import file_transfer

HOST = "0.0.0.0"
PORT = 5555

# global structures
clients_lock = threading.Lock()
connected_clients = []  # {"conn": socket, "addr": (ip,port), "username": str, "server_name": str}

auth_mgr = AuthManager()

def send_json(conn, obj_str):
    try:
        conn.sendall((obj_str + "\n").encode("utf-8"))
    except Exception:
        raise

def recv_full(conn):
    """Simple receiver for Phase 1 (newline-delimited messages)."""
    try:
        data = conn.recv(4096)
        if not data:
            return None
        return data.decode("utf-8").strip()
    except Exception:
        return None
    
def broadcast_to_server(server_name, sender_username, text, sender_conn=None):
    """Broadcast a 'chat' message to all clients in server_name except sender."""
    with clients_lock:
        to_remove = []
        for c in connected_clients:
            if c["server_name"] == server_name and c["conn"] is not None:
                if c["conn"] == sender_conn:
                    continue  # skip sender

                # ✅ mark host if sender is host of this server
                display_name = sender_username
                if auth_mgr.is_host(server_name, sender_username):
                    display_name = f"{sender_username} (HOST)"

                try:
                    msg = create_message("chat", {"from": display_name, "message": text})
                    send_json(c["conn"], msg)
                except Exception:
                    to_remove.append(c)
        for r in to_remove:
            try:
                connected_clients.remove(r)
            except ValueError:
                pass

def broadcast_system_message(server_name, text):
    """Broadcast a system message to all clients in server_name."""
    with clients_lock:
        to_remove = []
        for c in connected_clients:
            if c["server_name"] == server_name and c["conn"] is not None:
                try:
                    msg = create_message("system", {"message": text})
                    send_json(c["conn"], msg)
                except Exception:
                    to_remove.append(c)
        for r in to_remove:
            try:
                connected_clients.remove(r)
            except ValueError:
                pass

def broadcast_client_list(server_name):
    """Send updated client list to all clients in the server."""
    with clients_lock:
        clients = [c["username"] for c in connected_clients if c["server_name"] == server_name]
        print(f"[DEBUG] broadcast_client_list -> connected_clients = {clients}")  # <--- add this
        for c in connected_clients:
            if c["server_name"] == server_name:
                try:
                    msg = create_message("clients", {"list": clients})
                    send_json(c["conn"], msg)
                except Exception:
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
                        auth_mgr.servers[server_name]["host"] = username  # ✅ record host
                        resp = create_message("auth_result", {"ok": True, "message": "server_created"})
                        send_json(conn, resp)
                        broadcast_client_list(server_name)
                        print(f"[SERVER CREATED] {server_name} by {username}@{addr}")
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
                        broadcast_system_message(server_name, f"{username} has joined.") 
                        broadcast_client_list(server_name)
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
                        broadcast_to_server(server_name, username, text, sender_conn=conn)
                        print(f"[CHAT] ({server_name}) {username}: {text}")
                    else:
                        resp = create_message("system", {"message": "not_in_server"})
                        send_json(conn, resp)

                elif ptype in ("file_offer", "file_chunk", "file_complete"):
                    file_transfer.handle_file_message(packet, client_entry, connected_clients, clients_lock)


                else:
                    resp = create_message("system", {"message": "unknown_type"})
                    send_json(conn, resp)

    except Exception as e:
        print("[ERROR] Exception in client handler:", e)
        traceback.print_exc()
    finally:
        with clients_lock:
            # remove based on conn (or username)
            connected_clients[:] = [c for c in connected_clients if c["conn"] != conn]

        if client_entry["username"] and client_entry["server_name"]:
            broadcast_system_message(client_entry["server_name"], f"{client_entry['username']} has left.")
            broadcast_client_list(client_entry["server_name"])

        conn.close()
        print(f"[DISCONNECT] {addr}")

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