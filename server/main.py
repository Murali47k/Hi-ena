import socket
import threading

# Store connected clients
clients = []

def handle_client(conn,addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    while True:
        try:
            msg = conn.recv(1024).decode('utf-8')
            if not msg:
                break
            print(f"[{addr}] {msg}")
            broadcast(f"{addr}: {msg}", conn)
        except:
            break
    print(f"[DISCONNECTED] {addr}")
    clients.remove(conn)
    conn.close()

def broadcast(message, sender_conn):
    for client in clients:
        if client != sender_conn:
            try:
                client.send(message.encode('utf-8'))
            except:
                pass

def start_server(host='0.0.0.0', port=5000):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()
    print(f"[LISTENING] Server started on {host}:{port}")

    while True:
        conn, addr = server_socket.accept()
        clients.append(conn)
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {len(clients)}")

if __name__ == "__main__":
    print("[STARTING] Server is starting...")
    start_server()