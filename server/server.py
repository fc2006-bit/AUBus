import socket
import threading
from database import init_db, register_user, login_user, db_lock, edit_fields

HOST = '0.0.0.0'
PORT = 12345

def handle_client(conn, addr):
    print(f"New connection from {addr}")
    message = conn.recv(1024).decode()
    try:
        fields = message.split(":")
        if fields[0].lower() == "register":
            username = fields[1]
            name = fields[2] 
            email = fields[3] 
            password = fields[4]
            area = fields[5]
            is_driver = int(fields[6])
            conn.sendall(register_user(username,name,email,password,area,is_driver).encode())
        elif fields[0].lower() == "login":
            username = fields[1]
            password = fields[2]
            conn.sendall(login_user(username, password).encode())
        elif fields[0].lower() == "editprofile":
            username = fields[1]
            full_name = fields[2]
            area = fields[3]
            is_driver = int(fields[4])
            dict = {"name": full_name, "area": area, "is_driver": is_driver}
            print(dict)
            conn.sendall(edit_fields(username, dict).encode())
        else:
            conn.sendall("Invalid command.".encode())
    except:
        conn.sendall("Error processing request. Connection closing.\n".encode())
    finally:
        conn.close()

init_db()

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()
print(f"Server listening on port {PORT}...")

while True:
    conn, addr = server_socket.accept()
    client_thread = threading.Thread(target=handle_client, args=(conn, addr))
    client_thread.start()
