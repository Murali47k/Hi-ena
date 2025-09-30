import threading

class AppState:
    def __init__(self):
        self.messages = []      # list of (username, message) for chat only
        self.clients = []       # active users
        self.system_logs = []   # list of system log strings
        self.lock = threading.Lock()
        self.username = None 
        self.client = None

    def add_message(self, username, message):
        with self.lock:
            self.messages.append((username, message))

    def add_system_log(self, log):
        with self.lock:
            self.system_logs.append(log)
            if len(self.system_logs) > 100:  # keep last 100 logs
                self.system_logs.pop(0)
    
    def set_client(self, client):
        with self.lock:
            self.client = client

    def get_client(self):
        with self.lock:
            return self.client

    def set_clients(self, client_list):
        with self.lock:
            self.clients = client_list
    
    def set_username(self, username):
        with self.lock:
            self.username = username

    def get_username(self):
        with self.lock:
            return self.username

app_state = AppState()
