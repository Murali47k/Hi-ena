import json

# Message structure: { "type": "<message_type>", "data": { ... } }
# Example types used in Phase 1: "host", "join", "auth_result", "chat", "system"

def create_message(msg_type, data):
    """
    Create a JSON message string for sending over socket.
    :param msg_type: Type of the message (e.g., 'host', 'join', 'chat')
    :param data: Dictionary containing message data
    :return: JSON string
    """
    packet = {"type": msg_type, "data": data}
    return json.dumps(packet)

def parse_message(msg_str):
    """
    Parse a JSON message string received over socket.
    :param msg_str: JSON string
    :return: dict with keys 'type' and 'data' or {'type':'error', 'data':{...}}
    """
    try:
        return json.loads(msg_str)
    except Exception:
        return {"type": "error", "data": {"message": "invalid_json"}}
