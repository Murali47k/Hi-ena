import socket
import threading

def receive_messages(client_socket):
    while True:
        try:
            msg = client_socket.recv(1024).decode('utf-8')
            if not msg:
                break
            print(msg)
        except:
            break

def start_client(host='127.0.0.1', port=5000):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    # Start a thread to receive messages
    threading.Thread(target=receive_messages, args=(client_socket,), daemon=True).start()

    print("Connected to server. Type messages and press Enter:")
    while True:
        msg = input()
        if msg.lower() == "quit":
            break
        client_socket.send(msg.encode('utf-8'))

    client_socket.close()

if __name__ == "__main__":
    start_client()