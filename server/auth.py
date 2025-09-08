"""
Simple in-memory authentication manager for Phase 1.

This module stores server entries (a hosted "room") and performs simple
password verification. For Phase 1 we store only in-memory and keep
passwords as SHA256 hashes (clients should send the SHA256 of their password).
"""

import hashlib
import threading

_lock = threading.Lock()

class AuthManager:
    def __init__(self):
        # servers: server_name -> {
        #   "password_hash": str,
        #   "owner_conn": conn,
        #   "clients": set(usernames),
        #   "host": str
        # }
        self.servers = {}

    def create_server(self, server_name: str, password_hash: str, owner_conn):
        """Register a new hosted server. Returns (ok:bool, message:str)."""
        with _lock:
            if server_name in self.servers:
                return False, "server_exists"
            self.servers[server_name] = {
                "password_hash": password_hash,
                "owner_conn": owner_conn,
                "clients": set(),
                "host": None,   # ✅ will be filled in after auth
            }
            return True, "created"

    def verify_join(self, server_name: str, password_hash: str, username: str):
        """Verify join credentials. Returns (ok:bool, message:str)."""
        with _lock:
            if server_name not in self.servers:
                return False, "server_not_found"
            if self.servers[server_name]["password_hash"] != password_hash:
                return False, "wrong_password"
            # allow join
            self.servers[server_name]["clients"].add(username)
            return True, "joined"

    def remove_connection(self, server_name: str, username: str = None):
        """Remove a user from server clients. If owner disconnects, destroy the server."""
        with _lock:
            if server_name not in self.servers:
                return
            if username:
                self.servers[server_name]["clients"].discard(username)
            # cleanup logic can be expanded later

    def get_server_list(self):
        with _lock:
            return list(self.servers.keys())
        
    def is_host(self, server_name, username):
        """Return True if the given username is the host of the server."""
        if server_name not in self.servers:
            return False
        return self.servers[server_name].get("host") == username

    @staticmethod
    def hash_password_raw(password: str) -> str:
        """Helper to get SHA256 hex digest of a raw password string."""
        if isinstance(password, str):
            password = password.encode("utf-8")
        return hashlib.sha256(password).hexdigest()