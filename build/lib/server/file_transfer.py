import json
from core.utils import create_message

VALID_FILE_TYPES = {"file_offer", "file_chunk", "file_complete"}

def handle_file_message(packet, client_entry, connected_clients, clients_lock):
    """
    Relay file messages (offer/chunk/complete) to other clients in the same server.
    """
    try:
        ptype = packet.get("type")
        pdata = packet.get("data", {})

        if ptype not in VALID_FILE_TYPES:
            print(f"[SERVER] Ignored unknown file packet type: {ptype}")
            return

        server_name = client_entry.get("server_name")
        sender = client_entry.get("username")

        with clients_lock:
            for c in connected_clients:
                if c.get("server_name") == server_name and c.get("conn") != client_entry.get("conn"):
                    try:
                        relay_dict = {"from": sender}
                        if isinstance(pdata, dict):
                            relay_dict.update(pdata)
                        relay_json = create_message(ptype, relay_dict)
                        if not isinstance(relay_json, str):
                            relay_json = json.dumps(relay_json)
                        c["conn"].sendall((relay_json + "\n").encode("utf-8"))
                    except Exception as e:
                        print(f"[SERVER FILE RELAY ERROR] {e}")

        if ptype == "file_offer":
            print(f"[SERVER] {sender} is sending file '{pdata.get('filename')}' ({pdata.get('filesize',0)//1024} KB)")
        elif ptype == "file_complete":
            print(f"[SERVER] File transfer completed: {pdata.get('filename')} from {sender}")

    except Exception as e:
        print(f"[SERVER ERROR] handle_file_message exception: {e}")
