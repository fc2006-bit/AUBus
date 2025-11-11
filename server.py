import socket
import threading

HOST = '0.0.0.0'   # Listen on all interfaces
PORT = 12345       # Any free port

def handle_client(conn, addr):
    print(f"New connection from {addr}")
    conn.sendall("login or register: ".encode())
    page = conn.recv(1024).decode()
    if page.lower() == "register":
        conn.sendall("Input username: ".encode())
        username = conn.recv(1024).decode()
        conn.sendall("Input password: ".encode())
        password = conn.recv(1024).decode()
        database[username] = password
        conn.sendall("User registered successfully. Connection closing.\n".encode())
    elif page.lower() == "login":
        conn.sendall("Input username: ".encode())
        username = conn.recv(1024).decode()
        if username not in database:
            conn.sendall("User not found. Connection closing.\n".encode())
        else:
            conn.sendall("Input password: ".encode())
            password = conn.recv(1024).decode()
            if database[username] == password:
                conn.sendall("Login successful.\n".encode())
            else:
                conn.sendall("Incorrect password. Connection closing.\n".encode())
    conn.sendall("exit".encode())
    conn.close()

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()
print(f"Server listening on port {PORT}...")

database = {}

while True:
    conn, addr = server_socket.accept()
    client_thread = threading.Thread(target=handle_client, args=(conn, addr))
    client_thread.start()