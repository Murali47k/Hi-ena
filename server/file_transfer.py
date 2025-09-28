from core.utils import create_message

def handle_file_message(packet, client_entry, connected_clients, clients_lock):
    """
    Relay file messages (offer/chunk/complete) to other clients
    in the same server.
    """
    ptype = packet["type"]
    pdata = packet["data"]

    server_name = client_entry["server_name"]
    sender = client_entry["username"]

    # forward to everyone in same room except sender
    with clients_lock:
        for c in connected_clients:
            if c["server_name"] == server_name and c["conn"] != client_entry["conn"]:
                try:
                    relay = create_message(ptype, {"from": sender, **pdata})
                    c["conn"].sendall((relay + "\n").encode("utf-8"))
                except Exception:
                    pass
