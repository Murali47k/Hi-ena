import threading

class AppState:
    def __init__(self):
        self.messages = []  # list of (username, message)
        self.clients = []   # active users
        self.lock = threading.Lock()

    def add_message(self, username, message):
        with self.lock:
            self.messages.append((username, message))

    def set_clients(self, client_list):
        with self.lock:
            self.clients = client_list

app_state = AppState()
